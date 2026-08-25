import argparse
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
from urllib.parse import unquote
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import build_colorblind_mod as builder
import colorfilters as cf
from vpk_util import build_vpk


HERE = Path(__file__).resolve().parent
WEB_ROOT = HERE / "web"
BUNDLED_DEMO_IMAGE_DIR = HERE / "demo_images"
DEMO_IMAGE_DIR = Path(os.environ.get(
    "DEMO_IMAGE_DIR",
    BUNDLED_DEMO_IMAGE_DIR if BUNDLED_DEMO_IMAGE_DIR.is_dir() else HERE.parent,
))
NVIDIA_ASSETS = HERE / "assets" / "nvidia_daltonization"
MAX_REQUEST_BYTES = 64 * 1024
BUILD_LOCK = threading.Lock()
BUILD_SLOTS = threading.BoundedSemaphore(2)
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

FILTER_LIMITS = {
    "severity": (0.0, 1.0),
    "luminance": (0.0, 1.0),
}


def demo_images():
    images = [
        path for path in DEMO_IMAGE_DIR.glob("demo_image*.png")
        if path.is_file()
    ]

    def sort_key(path):
        match = re.fullmatch(r"demo_image(\d*)\.png", path.name, re.IGNORECASE)
        if not match:
            return (1, path.name.lower())
        suffix = match.group(1)
        return (0, 1 if not suffix else int(suffix))

    images = sorted(images, key=sort_key)
    if len(images) >= 6:
        images[1], images[5] = images[5], images[1]
    return images


def demo_image_entries():
    return [
        {"id": path.name, "label": f"Scene {index}"}
        for index, path in enumerate(demo_images(), start=1)
    ]


def _number(value, name, low, high):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f"{name} must be between {low:g} and {high:g}")
    return result


def validate_request(data):
    if not isinstance(data, dict):
        raise ValueError("request body must be an object")
    raw_filter = data.get("filter")
    if not isinstance(raw_filter, dict):
        raise ValueError("filter settings are missing")
    mode = raw_filter.get("mode")
    if mode not in cf.MODES:
        raise ValueError("unknown vision profile")
    algorithm = raw_filter.get("algorithm")
    if algorithm not in ("nvidia", "classic"):
        raise ValueError("unknown correction algorithm")
    if algorithm == "nvidia" and mode not in ("protan", "deutan", "off"):
        raise ValueError("NVIDIA's published transform supports protan and deutan only")
    filter_config = {"mode": mode, "algorithm": algorithm}
    for name, (low, high) in FILTER_LIMITS.items():
        filter_config[name] = _number(raw_filter.get(name), name, low, high)
    filter_config["correction"] = 1.0
    healthbars = raw_filter.get("healthbars", False)
    if not isinstance(healthbars, bool):
        raise ValueError("health-bar option must be true or false")

    outline = data.get("outline")
    if not isinstance(outline, dict):
        raise ValueError("outline settings are missing")
    thickness = _number(outline.get("thickness"), "outline thickness", 1.0, 2.0)
    if thickness not in (1.0, 2.0):
        raise ValueError("outline thickness must be either 1 or 2")
    color = outline.get("color")
    if not isinstance(color, str) or not HEX_COLOR.fullmatch(color):
        raise ValueError("outline color must use #RRGGBB format")
    rgb = tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
    return filter_config, thickness, rgb, healthbars


def generate_vpk(data):
    filter_config, thickness, outline_rgb, filter_healthbars = validate_request(data)
    messages = []
    with BUILD_LOCK:
        payload = builder.build(
            mode=filter_config["mode"],
            severity=filter_config["severity"],
            gain=filter_config["correction"],
            outline_width_scale=thickness,
            filter_config=filter_config,
            outline_color=outline_rgb,
            filter_healthbars=filter_healthbars,
            log=messages.append,
        )
        with tempfile.TemporaryDirectory(prefix="deadlock_filter_") as temporary:
            output = os.path.join(temporary, "pak##_dir.vpk")
            build_vpk(output, payload)
            with open(output, "rb") as handle:
                package = handle.read()
    return package, messages


class AppServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.build_token = secrets.token_urlsafe(32)


class Handler(BaseHTTPRequestHandler):
    server_version = "DeadlockFilterStudio/0.1"

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            return self.send_json({"status": "ok"})
        if path == "/api/session":
            return self.send_json({"token": self.server.build_token})
        if path == "/api/images":
            return self.send_json(demo_image_entries())
        if path.startswith("/demo/"):
            requested = unquote(path.removeprefix("/demo/"))
            available = {image.name: image for image in demo_images()}
            image = available.get(requested)
            if image is None:
                return self.send_error(404)
            return self.send_file(image)
        if path == "/demo_image.png":
            available = demo_images()
            if not available:
                return self.send_error(404)
            return self.send_file(available[0])
        if path == "/nvidia_protanopia.png":
            return self.send_file(NVIDIA_ASSETS / "protanopia.png", "image/png")
        if path == "/nvidia_deuteranopia.png":
            return self.send_file(NVIDIA_ASSETS / "deuteranopia.png", "image/png")
        static = {
            "/": WEB_ROOT / "index.html",
            "/index.html": WEB_ROOT / "index.html",
            "/styles.css": WEB_ROOT / "styles.css",
            "/app.js": WEB_ROOT / "app.js",
        }.get(path)
        if static is None:
            return self.send_error(404)
        return self.send_file(static)

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/build":
            return self.send_error(404)
        if self.headers.get("X-Build-Token") != self.server.build_token:
            return self.send_json({"error": "invalid local build session"}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.send_json({"error": "invalid content length"}, 400)
        if length <= 0 or length > MAX_REQUEST_BYTES:
            return self.send_json({"error": "request is empty or too large"}, 400)
        if not BUILD_SLOTS.acquire(blocking=False):
            return self.send_json({"error": "the builder is busy; try again shortly"}, 503)
        try:
            try:
                data = json.loads(self.rfile.read(length))
                package, _ = generate_vpk(data)
            except (ValueError, json.JSONDecodeError) as exc:
                return self.send_json({"error": str(exc)}, 400)
            except Exception as exc:
                return self.send_json({"error": f"VPK build failed: {exc}"}, 500)

            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header(
                "Content-Disposition",
                'attachment; filename="pak##_dir.vpk"',
            )
            self.send_header("Content-Length", str(len(package)))
            self.send_header("Cache-Control", "no-store")
            self.send_security_headers()
            self.end_headers()
            self.wfile.write(package)
        finally:
            BUILD_SLOTS.release()

    def send_file(self, path, content_type=None):
        path = Path(path)
        if not path.is_file():
            return self.send_error(404)
        data = path.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type",
            content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        )
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_security_headers()
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, value, status=200):
        data = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_security_headers()
        self.end_headers()
        self.wfile.write(data)

    def send_security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )

    def log_message(self, pattern, *args):
        print("[web] " + pattern % args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if not demo_images():
        print(f"ERROR: no demo_image*.png files found in {DEMO_IMAGE_DIR}")
        return 1
    server = AppServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Deadlock Filter Studio is running at {url}")
    print("Press Ctrl+C to stop the local server.")
    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
