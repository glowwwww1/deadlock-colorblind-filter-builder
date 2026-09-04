import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import build_colorblind_mod as builder
from vpk_util import build_vpk


ROOT = Path(__file__).resolve().parent.parent
NODE_BUILDER = ROOT / "tests" / "browser_builder_test.js"


class StaticPagesBuilderTests(unittest.TestCase):
    def test_browser_builder_matches_server_for_classic_filters(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is unavailable")
        cases = (
            {
                "mode": "deutan",
                "algorithm": "classic",
                "severity": 0.65,
                "luminance": 0.7,
                "healthbars": True,
                "outlineColor": "#ffffb0",
            },
            {
                "mode": "tritan",
                "algorithm": "classic",
                "severity": 1.0,
                "luminance": 0.25,
                "healthbars": False,
                "outlineColor": "#a22222",
            },
            {
                "mode": "protan",
                "algorithm": "classic",
                "severity": 0.35,
                "luminance": 1.0,
                "healthbars": True,
                "outlineColor": "#123456",
            },
        )
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            for index, settings in enumerate(cases):
                browser_path = temporary_path / f"browser_{index}.vpk"
                server_path = temporary_path / f"server_{index}.vpk"
                subprocess.run(
                    [node, str(NODE_BUILDER), str(browser_path), json.dumps(settings)],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                config = {
                    "mode": settings["mode"],
                    "algorithm": settings["algorithm"],
                    "severity": settings["severity"],
                    "correction": 1.0,
                    "luminance": settings["luminance"],
                }
                outline = tuple(
                    int(settings["outlineColor"][offset:offset + 2], 16)
                    for offset in (1, 3, 5)
                )
                payload = builder.build(
                    mode=settings["mode"],
                    severity=settings["severity"],
                    gain=1.0,
                    outline_width_scale=1.0,
                    filter_config=config,
                    outline_color=outline,
                    filter_healthbars=settings["healthbars"],
                    log=lambda _: None,
                )
                build_vpk(server_path, payload)
                self.assertEqual(server_path.read_bytes(), browser_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
