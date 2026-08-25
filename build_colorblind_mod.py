import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys

import numpy as np

import colorfilters as cf
from vpk_util import build_vpk, extract, list_vpk

GAME = os.environ.get(
    "DEADLOCK_GAME_DIR",
    r"C:\Program Files (x86)\Steam\steamapps\common\Deadlock\game\citadel",
)
GAME_PAK = os.path.join(GAME, "pak01_dir.vpk")
SHADER_PAK = os.path.join(GAME, "shaders_pc_dir.vpk")
ADDONS = os.path.join(GAME, "addons")
ADDON_NAME = "pak02_dir.vpk"

HERE = os.path.dirname(os.path.abspath(__file__))
BACKUP = os.path.join(HERE, "backup", "original_vpost")
SHADER_BACKUP = os.path.join(
    HERE, "backup", "original_shaders", "generate_outlines_pc_50_ps.vcs")
SHADER_BUILD = os.path.join(
    HERE, "build", "shaders", "vfx", "generate_outlines_pc_50_ps.vcs")
SHADER_2X = os.path.join(
    HERE, "assets", "outlines", "generate_outlines_2x_pc_50_ps.vcs")
SHADER_2X_SHA256 = "899dba24dc046eac5651d949382a9842c4b4760719612c0958734516cc378988"
OUTLINE_COLOR_BACKUP = os.path.join(
    HERE, "backup", "original_vdata", "generic_data.vdata_c")
OUTLINE_COLOR_BUILD = os.path.join(
    HERE, "build", "scripts", "generic_data.vdata_c")
HEALTH_STYLE_BACKUP = os.path.join(HERE, "backup", "original_vcss")
STATE = os.path.join(HERE, "current_settings.txt")

SHADER_INTERNAL = "shaders/vfx/generate_outlines_pc_50_ps.vcs"
OUTLINE_COLOR_INTERNAL = "scripts/generic_data.vdata_c"
HEALTH_STYLE_INTERNALS = (
    "panorama/styles/hud_health.vcss_c",
    "panorama/styles/hud_health_container.vcss_c",
    "panorama/styles/hud_health_pips.vcss_c",
    "panorama/styles/hud_health_single_bar.vcss_c",
    "panorama/styles/hud_health_stacked.vcss_c",
    "panorama/styles/unit_status.vcss_c",
    "panorama/styles/unit_status_old.vcss_c",
    "panorama/styles/unit_status_v2.vcss_c",
)
HEALTH_NAMED_COLORS = {
    "colorEnemy": (255, 65, 13),
    "colorFriendly": (0, 255, 153),
    "courageBrightColor": (236, 151, 25),
    "darkblue": (0, 0, 139),
    "darkorange": (255, 140, 0),
    "lightgreen": (144, 238, 144),
    "spiritBrightColor": (206, 144, 255),
    "vivaciousGreen": (20, 35, 4),
}
HEALTH_COLOR_LITERALS = {
    "panorama/styles/hud_health.vcss_c": (
        "#FCFF6D", "#FF410D", "#FFE3DB", "#4bdc68", "rgb(232, 127, 61)",
        "rgb(122, 165, 69)", "#00FF99", "#FFEFD7", "#cc340a", "#f6805f",
        "#00D37F", "#FF5656", "#580000", "colorEnemy", "colorFriendly",
        "courageBrightColor", "spiritBrightColor",
    ),
    "panorama/styles/hud_health_container.vcss_c": (
        "#D74949", "#DDFF56", "#FF5656", "rgb(255, 130, 130)", "#FFED79",
        "lightgreen", "vivaciousGreen",
    ),
    "panorama/styles/hud_health_pips.vcss_c": (
        "#E4D0B2", "#87FF87", "#FF410D", "#E7B659", "#5B79E6", "#8B0000",
        "#FF8787", "#7DDAB0", "#78c2ff", "#00FFFF", "#AED6F1",
        "rgba( 255, 215, 216, 1 )", "rgba( 133, 255, 133, 1 )",
        "rgba( 10, 230, 80, 0 )", "rgba( 255, 250, 219, 1 )",
        "darkblue", "darkorange",
    ),
    "panorama/styles/hud_health_single_bar.vcss_c": (
        "#FCFF6D", "#FF410D", "#FFE3DB", "rgb(119, 219, 119)",
        "rgb(232, 127, 61)", "#00FF99", "#FFEFD7", "#cc340a", "#f6805f",
        "#00D37F", "#FF5656", "#580000", "colorEnemy", "colorFriendly",
    ),
    "panorama/styles/hud_health_stacked.vcss_c": (
        "#4bdc68", "courageBrightColor", "spiritBrightColor",
    ),
    "panorama/styles/unit_status.vcss_c": (
        "#E7B659", "#5B79E6", "#5befb5", "#fd4949", "#FFEFD7", "#ffedb8",
        "#f24d4d", "#ffe55b", "#504c47", "#fcb43d", "#e29afd", "#46e2ac",
        "rgb(113, 0, 0)", "#b82323", "#5fff80", "#e9e76a", "#6a75e9",
        "#b95f5f", "#acca91", "#62FBBE", "lightgreen",
    ),
    "panorama/styles/unit_status_old.vcss_c": (
        "#E7B659", "#5B79E6", "#7DDAB0", "#62FBBE", "lightgreen",
    ),
    "panorama/styles/unit_status_v2.vcss_c": (
        "#E7B659", "#5B79E6", "#5befb5", "#fd4949", "#FFEFD7", "#ffedb8",
        "#f24d4d", "#ffe55b", "#504c47", "#fcb43d", "#e29afd", "#46e2ac",
        "rgb(67, 12, 12)", "rgb(64, 8, 8)", "rgb(80, 2, 2)", "#b82323",
        "rgb(74, 15, 15)", "#bf3333", "#c13030", "#d8d2af", "#c7c19d",
        "#5fff80", "#e9e76a", "#6a75e9", "#b95f5f", "#acca91", "#FB4949",
        "rgb(255, 194, 194)", "#62FBBE", "lightgreen",
    ),
}
DEFAULT_OUTLINE_COLOR = (162, 34, 34)
OUTLINE_WIDTH_SCALE = 2.0
SHADER_HELPER = os.path.join(
    HERE, "tools", "shader_patch", "bin", "Release", "net9.0", "ShaderPatch.exe")
SHADER_PROJECT = os.path.join(HERE, "tools", "shader_patch", "ShaderPatch.csproj")
VDATA_HELPER = os.path.join(
    HERE, "tools", "vdata_patch", "bin", "Release", "net9.0", "VDataPatch.exe")
VDATA_PUBLISHED_DLL = os.path.join(
    HERE, "tools", "vdata_patch", "publish", "VDataPatch.dll")
VDATA_BUILD_DLL = os.path.join(
    HERE, "tools", "vdata_patch", "bin", "Release", "net9.0", "VDataPatch.dll")
VDATA_PROJECT = os.path.join(HERE, "tools", "vdata_patch", "VDataPatch.csproj")

TARGET_PREFIX = "postprocessing/"
TARGET_EXCLUDE = "postprocessing/gamestate/"

SWATCHES = [
    ("Enemy health", "#E03B3B"),
    ("Ally health", "#4CC44C"),
    ("Low health", "#C22222"),
    ("Weapon item", "#C87D2D"),
    ("Vitality item", "#659F31"),
    ("Spirit item", "#A063C4"),
    ("Amber team", "#E8A33D"),
    ("Sapphire team", "#4A9EE8"),
    ("Souls", "#F0C674"),
    ("Neutral creep", "#B8A882"),
]

KEY_PAIRS = [
    ("Enemy vs ally health", "#E03B3B", "#4CC44C"),
    ("Weapon vs vitality", "#C87D2D", "#659F31"),
    ("Enemy health vs souls", "#E03B3B", "#F0C674"),
]


def hex_to_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64) / 255.0


def rgb_to_hex(c):
    v = np.clip(np.rint(np.asarray(c) * 255.0), 0, 255).astype(int)
    return "#%02X%02X%02X" % tuple(v)


def discover_targets():
    if os.path.exists(GAME_PAK):
        found = []
        for full, _, _, _ in list_vpk(GAME_PAK):
            low = full.lower()
            if low.startswith(TARGET_PREFIX) and low.endswith(".vpost_c") \
                    and not low.startswith(TARGET_EXCLUDE):
                found.append(full)
        return sorted(found)
    cached = [
        TARGET_PREFIX + name
        for name in os.listdir(BACKUP)
        if name.lower().endswith(".vpost_c")
    ] if os.path.isdir(BACKUP) else []
    if not cached:
        raise FileNotFoundError("no Deadlock post-processing resources are available")
    return sorted(cached)


def fetch_originals():
    os.makedirs(BACKUP, exist_ok=True)
    out = {}
    for internal in discover_targets():
        cached = os.path.join(BACKUP, os.path.basename(internal))
        if os.path.exists(cached):
            with open(cached, "rb") as f:
                out[internal] = f.read()
        else:
            data = extract(GAME_PAK, internal)
            with open(cached, "wb") as f:
                f.write(data)
            out[internal] = data
    return out


def fetch_outline_shader_original():
    if not os.path.exists(SHADER_BACKUP):
        os.makedirs(os.path.dirname(SHADER_BACKUP), exist_ok=True)
        data = extract(SHADER_PAK, SHADER_INTERNAL)
        with open(SHADER_BACKUP, "wb") as handle:
            handle.write(data)
    return SHADER_BACKUP


def fetch_outline_color_original():
    if not os.path.exists(OUTLINE_COLOR_BACKUP):
        os.makedirs(os.path.dirname(OUTLINE_COLOR_BACKUP), exist_ok=True)
        data = extract(GAME_PAK, OUTLINE_COLOR_INTERNAL)
        with open(OUTLINE_COLOR_BACKUP, "wb") as handle:
            handle.write(data)
    return OUTLINE_COLOR_BACKUP


def fetch_health_style_originals():
    os.makedirs(HEALTH_STYLE_BACKUP, exist_ok=True)
    result = {}
    for internal in HEALTH_STYLE_INTERNALS:
        cached = os.path.join(HEALTH_STYLE_BACKUP, os.path.basename(internal))
        if os.path.exists(cached):
            with open(cached, "rb") as handle:
                result[internal] = handle.read()
        elif os.path.exists(GAME_PAK):
            data = extract(GAME_PAK, internal)
            with open(cached, "wb") as handle:
                handle.write(data)
            result[internal] = data
        else:
            raise FileNotFoundError("missing bundled health-bar style: %s" % internal)
    return result


def _parse_css_color(value):
    if value in HEALTH_NAMED_COLORS:
        return HEALTH_NAMED_COLORS[value]
    if value.startswith("#"):
        return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))
    numbers = [int(part) for part in re.findall(r"\d+", value)]
    return tuple(numbers[:3])


def _format_css_color(value, rgb):
    alpha = ""
    if value.startswith("rgba"):
        numbers = re.findall(r"[\d.]+", value)
        opacity = float(numbers[3])
        alpha = "%02X" % int(np.clip(np.rint(opacity * 255.0), 0, 255))
    return ("#%02X%02X%02X%s" % (*rgb, alpha)).encode("ascii")


def _transform_health_rgb(rgb, mode, severity, gain, filter_config):
    source = np.array(rgb, dtype=np.float64).reshape(1, 3) / 255.0
    if filter_config is None:
        transformed = cf.apply_mode(source, mode, severity, gain)
    else:
        transformed = cf.apply_custom(source, filter_config)
    return tuple(np.clip(np.rint(transformed[0] * 255.0), 0, 255).astype(int))


def patch_health_styles(mode="deutan", severity=1.0, gain=1.0,
                        filter_config=None, log=print):
    active = (not cf.custom_filter_is_identity(filter_config)
              if filter_config is not None else mode != "off")
    if not active:
        log("  health bars: original colors")
        return {}
    result = {}
    for internal, blob in fetch_health_style_originals().items():
        patched = blob
        replacements = 0
        for literal in HEALTH_COLOR_LITERALS[internal]:
            original = literal.encode("ascii")
            rgb = _transform_health_rgb(
                _parse_css_color(literal), mode, severity, gain, filter_config)
            replacement = _format_css_color(literal, rgb)
            if len(replacement) > len(original):
                raise ValueError("health-bar color replacement exceeds its source length")
            count = patched.count(original)
            if count:
                patched = patched.replace(original, replacement.ljust(len(original), b" "))
                replacements += count
        if replacements == 0:
            raise ValueError("no health-bar colors found in %s" % internal)
        if len(patched) != len(blob):
            raise ValueError("health-bar patch changed resource size")
        result[internal] = patched
    log("  filtered health-bar colors in %d Panorama resources" % len(result))
    return result


def patch_enemy_outline_color(rgb, log=print):
    rgb = tuple(int(component) for component in rgb)
    if len(rgb) != 3 or any(component < 0 or component > 255 for component in rgb):
        raise ValueError("enemy outline RGB components must be between 0 and 255")
    if rgb == DEFAULT_OUTLINE_COLOR:
        log("  enemy outline color: original #%02X%02X%02X" % rgb)
        return None

    source = fetch_outline_color_original()
    os.makedirs(os.path.dirname(OUTLINE_COLOR_BUILD), exist_ok=True)
    arguments = [source, OUTLINE_COLOR_BUILD, *(str(component) for component in rgb)]
    if os.name == "nt" and os.path.exists(VDATA_HELPER):
        command = [VDATA_HELPER, *arguments]
    elif os.path.exists(VDATA_PUBLISHED_DLL):
        command = ["dotnet", VDATA_PUBLISHED_DLL, *arguments]
    elif os.path.exists(VDATA_BUILD_DLL):
        command = ["dotnet", VDATA_BUILD_DLL, *arguments]
    else:
        command = [
            "dotnet", "run", "--project", VDATA_PROJECT,
            "-c", "Release", "--", *arguments,
        ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "The build-time outline-color helper is unavailable. "
            "Rebuild tools/vdata_patch first."
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError("enemy outline color patch failed: %s" % detail) from exc

    with open(OUTLINE_COLOR_BUILD, "rb") as handle:
        patched = handle.read()
    if not patched:
        raise RuntimeError("outline-color helper produced an empty resource")
    log("  enemy outline color: #A22222 -> #%02X%02X%02X" % rgb)
    return patched


def patch_outline_shader(width_scale=OUTLINE_WIDTH_SCALE, log=print):
    width_scale = float(width_scale)
    if abs(width_scale - 1.0) < 1e-6:
        log("  outline width: original 1.00x (shader override omitted)")
        return None
    prebuilt = {
        2.0: (SHADER_2X, SHADER_2X_SHA256),
    }
    selected = prebuilt.get(width_scale)
    if selected is not None:
        path, expected_digest = selected
        with open(path, "rb") as handle:
            patched = handle.read()
        digest = hashlib.sha256(patched).hexdigest()
        if digest != expected_digest:
            raise RuntimeError(
                "the prebuilt %.0fx outline shader is missing or damaged"
                % width_scale)
        log("  outline halo width: 1.00x -> %.2fx" % width_scale)
        return patched
    raise ValueError(
        "outline width scale must be 1 or 2; other compiled scales are rejected by Deadlock")


def separation_scores(mode, severity, gain):
    if mode not in cf.CVD_TYPES:
        return []
    rows = []
    for label, ha, hb in KEY_PAIRS:
        a, b = hex_to_rgb(ha), hex_to_rgb(hb)
        before = np.linalg.norm(cf.simulate(a, mode, severity) - cf.simulate(b, mode, severity))
        ca = cf.daltonize(a, mode, severity, gain)
        cb = cf.daltonize(b, mode, severity, gain)
        after = np.linalg.norm(cf.simulate(ca, mode, severity) - cf.simulate(cb, mode, severity))
        pct = (after / before - 1.0) * 100.0 if before > 1e-9 else float("inf")
        rows.append((label, before, after, pct))
    return rows


def build(mode="deutan", severity=1.0, gain=1.0,
          outline_width_scale=OUTLINE_WIDTH_SCALE, log=print,
          filter_config=None, outline_color=None, filter_healthbars=True):
    originals = fetch_originals()
    payload, skipped, enabled = {}, [], []
    for internal in sorted(originals):
        blob = originals[internal]
        try:
            patched, before, after, was_on = cf.patch_vpost(
                blob, mode, severity, gain, custom_config=filter_config)
        except ValueError as exc:
            skipped.append((os.path.basename(internal), str(exc)))
            continue
        payload[internal] = patched
        filter_active = (not cf.custom_filter_is_identity(filter_config)
                         if filter_config is not None else mode != "off")
        if was_on is False and filter_active:
            enabled.append(os.path.basename(internal))
        assert len(patched) == len(blob), "patch changed file size"
    log("  patched %d resources, skipped %d" % (len(payload), len(skipped)))
    for name, why in skipped:
        log("    SKIPPED %s (%s)" % (name, why))
    if enabled:
        log("  switched color correction ON in %d resource(s) that shipped disabled:"
            % len(enabled))
        for n in enabled:
            log("    - %s" % n)
    outline_shader = patch_outline_shader(outline_width_scale, log=log)
    if outline_shader is not None:
        payload[SHADER_INTERNAL] = outline_shader
    if outline_color is not None:
        color_resource = patch_enemy_outline_color(outline_color, log=log)
        if color_resource is not None:
            payload[OUTLINE_COLOR_INTERNAL] = color_resource
    if filter_healthbars:
        payload.update(patch_health_styles(
            mode, severity, gain, filter_config=filter_config, log=log))
    else:
        log("  health bars: original colors")
    return payload


def install(payload, log=print):
    out_vpk = os.path.join(HERE, ADDON_NAME)
    size = build_vpk(out_vpk, payload)
    os.makedirs(ADDONS, exist_ok=True)
    target = os.path.join(ADDONS, ADDON_NAME)
    try:
        shutil.copy2(out_vpk, target)
    except PermissionError as exc:
        raise RuntimeError(
            "Deadlock has locked the installed VPK. Fully exit the game, "
            "then apply the filter again."
        ) from exc
    except OSError as exc:
        if getattr(exc, "winerror", None) in (32, 33):
            raise RuntimeError(
                "Deadlock has locked the installed VPK. Fully exit the game, "
                "then apply the filter again."
            ) from exc
        raise
    log("  built and installed %s (%d bytes, %d files)" % (ADDON_NAME, size, len(payload)))
    return out_vpk


def uninstall(log=print):
    target = os.path.join(ADDONS, ADDON_NAME)
    if os.path.exists(target):
        try:
            os.remove(target)
        except PermissionError as exc:
            raise RuntimeError(
                "Deadlock has locked the installed VPK. Fully exit the game, "
                "then remove the filter again."
            ) from exc
        except OSError as exc:
            if getattr(exc, "winerror", None) in (32, 33):
                raise RuntimeError(
                    "Deadlock has locked the installed VPK. Fully exit the game, "
                    "then remove the filter again."
                ) from exc
            raise
        log("  removed %s" % target)
    else:
        log("  not installed; nothing to remove")
    if os.path.exists(STATE):
        os.remove(STATE)


def save_state(mode, severity, gain, last_mode=None):
    if last_mode is None:
        previous = load_state()
        if mode != "off":
            last_mode = mode
        else:
            last_mode = previous.get("last_mode", previous.get("mode", "deutan"))
    if last_mode not in cf.MODES or last_mode == "off":
        last_mode = "deutan"
    with open(STATE, "w") as f:
        f.write("mode=%s\nlast_mode=%s\nseverity=%.3f\ngain=%.3f\n"
                % (mode, last_mode, severity, gain))


def load_state():
    state = {"mode": "deutan", "last_mode": "deutan", "severity": 1.0, "gain": 1.0}
    if os.path.exists(STATE):
        for line in open(STATE):
            if "=" in line:
                k, v = line.strip().split("=", 1)
                if k in ("severity", "gain"):
                    state[k] = float(v)
                elif k in ("mode", "last_mode"):
                    state[k] = v
    if state["last_mode"] not in cf.MODES or state["last_mode"] == "off":
        state["last_mode"] = state["mode"] if state["mode"] != "off" else "deutan"
    return state


def write_preview(path, mode, severity, gain):
    from PIL import Image, ImageDraw

    sim_type = mode if mode in cf.CVD_TYPES else "deutan"
    cols = ["Original", "You see", "Filtered", "You see"]
    sw, sh, pad, top, label_w = 132, 58, 8, 34, 132
    w = label_w + len(cols) * (sw + pad) + pad
    h = top + len(SWATCHES) * (sh + pad) + pad
    img = Image.new("RGB", (w, h), (22, 22, 26))
    d = ImageDraw.Draw(img)
    for i, c in enumerate(cols):
        d.text((label_w + i * (sw + pad) + 6, 12), c, fill=(225, 225, 230))
    for row, (name, hexv) in enumerate(SWATCHES):
        y = top + row * (sh + pad)
        base = hex_to_rgb(hexv)
        filtered = cf.apply_mode(base, mode, severity, gain)
        cells = [base,
                 cf.simulate(base, sim_type, severity),
                 filtered,
                 cf.simulate(filtered, sim_type, severity)]
        d.text((6, y + sh // 2 - 6), name, fill=(200, 200, 208))
        for i, c in enumerate(cells):
            x = label_w + i * (sw + pad)
            v = np.clip(np.rint(np.asarray(c) * 255.0), 0, 255).astype(int)
            d.rectangle([x, y, x + sw, y + sh], fill=tuple(v))
    img.save(path)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=cf.MODES, default="deutan")
    ap.add_argument("--severity", type=float, default=1.0,
                    help="how strong the color deficiency is (0-1, CVD modes only)")
    ap.add_argument("--gain", type=float, default=1.0,
                    help="filter intensity (0-1)")
    ap.add_argument("--outline-width-scale", type=float, choices=(1.0, 2.0),
                    default=OUTLINE_WIDTH_SCALE,
                    help="outline halo thickness multiplier (1 or 2; default: 2)")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--preview", action="store_true", help="also write preview.png")
    args = ap.parse_args()

    if args.uninstall:
        uninstall()
        return 0
    if not os.path.exists(GAME_PAK) or not os.path.exists(SHADER_PAK):
        print("ERROR: game VPKs not found under %s" % GAME, file=sys.stderr)
        return 1

    print("Deadlock color filter: mode=%s severity=%.2f gain=%.2f"
          % (args.mode, args.severity, args.gain))
    payload = build(args.mode, args.severity, args.gain, args.outline_width_scale)

    rows = separation_scores(args.mode, args.severity, args.gain)
    if rows:
        print("\n  Perceived separation (higher = easier to tell apart):")
        print("    %-24s %9s %9s %9s" % ("pair", "before", "after", "change"))
        for label, before, after, pct in rows:
            print("    %-24s %9.3f %9.3f %+8.1f%%" % (label, before, after, pct))

    if args.preview:
        print("\n  preview -> %s" % write_preview(
            os.path.join(HERE, "preview.png"), args.mode, args.severity, args.gain))

    if args.install:
        old_state = load_state()
        last_mode = args.mode if args.mode != "off" else old_state["last_mode"]
        install(payload)
        save_state(args.mode, args.severity, args.gain, last_mode=last_mode)
        print("\nFully restart Deadlock for it to take effect.")
    else:
        build_vpk(os.path.join(HERE, ADDON_NAME), payload)
        print("\nBuilt but not installed. Add --install to copy into citadel/addons.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
