import os
import unittest
from unittest import mock

import numpy as np

import build_colorblind_mod as builder
import colorfilters as cf
from web_app import demo_image_entries, validate_request


def request_payload(**outline_overrides):
    outline = {"thickness": 2.0, "color": "#A22222"}
    outline.update(outline_overrides)
    return {
        "filter": dict(cf.CUSTOM_DEFAULTS),
        "outline": outline,
    }


def website_request_payload(**outline_overrides):
    payload = request_payload(**outline_overrides)
    payload["filter"].pop("correction")
    return payload


class FilterStudioValidationTests(unittest.TestCase):
    def test_bundled_scene_order(self):
        self.assertEqual(
            [
                "demo_image.png",
                "demo_image6.png",
                "demo_image3.png",
                "demo_image4.png",
                "demo_image5.png",
                "demo_image2.png",
                "demo_image7.png",
            ],
            [entry["id"] for entry in demo_image_entries()],
        )

    def test_hosted_build_uses_bundled_resources(self):
        with mock.patch.object(builder, "GAME_PAK", "missing-game-pak.vpk"):
            targets = builder.discover_targets()
        self.assertIn("postprocessing/basepostprocess_deadlock.vpost_c", targets)
        self.assertGreaterEqual(len(targets), 17)

    def test_website_does_not_require_redundant_strength(self):
        config, _, _ = validate_request(website_request_payload())
        self.assertEqual(1.0, config["correction"])

    def test_accepts_website_outline_endpoints(self):
        for thickness in (1.0, 2.0):
            _, parsed, rgb = validate_request(request_payload(
                thickness=thickness, color="#00D6FF"))
            self.assertEqual(thickness, parsed)
            self.assertEqual((0, 214, 255), rgb)

    def test_rejects_non_option_outline_values(self):
        for thickness in (0.5, 1.5, 3.0, 4.0):
            with self.assertRaises(ValueError):
                validate_request(request_payload(thickness=thickness))

    def test_rejects_malformed_outline_color(self):
        with self.assertRaises(ValueError):
            validate_request(request_payload(color="cyan"))

    def test_rejects_unknown_algorithm(self):
        payload = request_payload()
        payload["filter"]["algorithm"] = "made_up"
        with self.assertRaises(ValueError):
            validate_request(payload)

    def test_rejects_nvidia_for_tritan(self):
        payload = request_payload()
        payload["filter"].update(mode="tritan", algorithm="nvidia")
        with self.assertRaises(ValueError):
            validate_request(payload)

    def test_outline_choices_use_size_preserving_artifacts(self):
        self.assertIsNone(builder.patch_outline_shader(1.0, log=lambda _: None))
        original_size = os.path.getsize(builder.SHADER_BACKUP)
        shader = builder.patch_outline_shader(2.0, log=lambda _: None)
        self.assertEqual(original_size, len(shader))
        with self.assertRaises(ValueError):
            builder.patch_outline_shader(3.0, log=lambda _: None)


class CustomFilterTests(unittest.TestCase):
    def test_off_with_neutral_tuning_is_byte_eligible_identity(self):
        source = np.linspace(0.0, 1.0, 96).reshape(32, 3)
        config = dict(cf.CUSTOM_DEFAULTS, mode="off")
        np.testing.assert_array_equal(source, cf.apply_custom(source, config))

    def test_all_modes_stay_finite_and_in_gamut(self):
        generator = np.random.default_rng(42)
        source = generator.random((1024, 3))
        for mode in cf.MODES:
            config = dict(
                cf.CUSTOM_DEFAULTS,
                mode=mode,
                algorithm="classic" if mode == "tritan" else "nvidia",
                correction=1.0,
                hue=37.0,
                saturation=1.4,
                contrast=1.2,
            )
            result = cf.apply_custom(source, config)
            self.assertTrue(np.isfinite(result).all(), mode)
            self.assertGreaterEqual(float(result.min()), 0.0, mode)
            self.assertLessEqual(float(result.max()), 1.0, mode)

    def test_all_correction_algorithms_stay_finite_and_in_gamut(self):
        generator = np.random.default_rng(7)
        source = generator.random((1024, 3))
        for algorithm in ("nvidia", "classic"):
            config = dict(
                cf.CUSTOM_DEFAULTS,
                algorithm=algorithm,
                correction=1.0,
            )
            result = cf.apply_custom(source, config)
            self.assertTrue(np.isfinite(result).all(), algorithm)
            self.assertGreaterEqual(float(result.min()), 0.0, algorithm)
            self.assertLessEqual(float(result.max()), 1.0, algorithm)

    def test_classic_supports_tritan(self):
        source = np.linspace(0.0, 1.0, 96).reshape(32, 3)
        config = dict(cf.CUSTOM_DEFAULTS, mode="tritan", algorithm="classic")
        result = cf.apply_custom(source, config)
        self.assertFalse(np.array_equal(source, result))

    def test_nvidia_full_severity_matches_published_reference(self):
        rgb8 = np.array([
            [0, 0, 0], [255, 255, 255], [162, 34, 34],
            [0, 214, 255], [18, 129, 73],
        ], dtype=np.uint16)
        for mode in ("protan", "deutan"):
            red, green, blue = rgb8[:, 0], rgb8[:, 1], rgb8[:, 2]
            x = (red % 16) * 256 + blue
            y = (red // 16) * 256 + green
            expected = cf._nvidia_transform_image(mode)[y, x]
            actual = np.rint(cf.nvidia_daltonize(
                rgb8 / 255.0, mode, 1.0) * 255.0).astype(np.uint8)
            np.testing.assert_array_equal(expected, actual)


if __name__ == "__main__":
    unittest.main()
