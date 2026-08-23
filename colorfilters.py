import struct
from functools import lru_cache
from pathlib import Path

import numpy as np

LUT_DIM = 32
LUT_BYTES = LUT_DIM ** 3 * 4
KV3_TERMINATOR = bytes([0x00, 0xDD, 0xEE, 0xFF])

KV3_BOOL_TRUE = 0x0D
KV3_BOOL_FALSE = 0x0E
CC_TYPE_PREFIX = bytes([0x0B, 0x07])

CVD_MATRICES = {
    'protan': (0.152286, 1.052583, -0.204868,
               0.114503, 0.786281, 0.099216,
               -0.003882, -0.048116, 1.051998),
    'deutan': (0.367322, 0.860646, -0.227968,
               0.280085, 0.672501, 0.047413,
               -0.011820, 0.042940, 0.968881),
    'tritan': (1.255528, -0.076749, -0.178779,
               -0.078411, 0.930809, 0.147602,
               0.004733, 0.691367, 0.303900),
}

ERROR_SHIFT = {
    'protan': np.array([[0.0, 0.0, 0.0], [0.7, 1.0, 0.0], [0.7, 0.0, 1.0]]),
    'deutan': np.array([[0.0, 0.0, 0.0], [0.7, 1.0, 0.0], [0.7, 0.0, 1.0]]),
    'tritan': np.array([[1.0, 0.0, 0.7], [0.0, 1.0, 0.7], [0.0, 0.0, 0.0]]),
}

LINEAR_LUMA = np.array([0.2126, 0.7152, 0.0722])
GAMUT_EDGE_INSET = 0.01
GAMUT_SOFTNESS = 0.015

CVD_TYPES = ('protan', 'deutan', 'tritan')
MODES = ('off', 'protan', 'deutan', 'tritan', 'gray', 'invert')

MODE_LABELS = {
    'off': 'Off (original colors)',
    'protan': 'Protan (red-weak)',
    'deutan': 'Deutan (green-weak)',
    'tritan': 'Tritan (blue-weak)',
    'gray': 'Black and white',
    'invert': 'Inverted colors',
}

CUSTOM_DEFAULTS = {
    'mode': 'deutan',
    'algorithm': 'nvidia',
    'severity': 1.0,
    'correction': 1.0,
    'luminance': 1.0,
    'exposure': 0.0,
    'contrast': 1.0,
    'saturation': 1.0,
    'gamma': 1.0,
    'hue': 0.0,
    'temperature': 0.0,
    'tint': 0.0,
    'red': 1.0,
    'green': 1.0,
    'blue': 1.0,
}

NVIDIA_TRANSFORM_PATHS = {
    'protan': Path(__file__).resolve().parent / 'assets' / 'nvidia_daltonization' / 'protanopia.png',
    'deutan': Path(__file__).resolve().parent / 'assets' / 'nvidia_daltonization' / 'deuteranopia.png',
}


def cvd_matrix(cvd_type, severity):
    full = np.array(CVD_MATRICES[cvd_type]).reshape(3, 3)
    t = float(np.clip(severity, 0.0, 1.0))
    return np.eye(3) * (1.0 - t) + full * t


def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float64), 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1.0 / 2.4) - 0.055)


def simulate(srgb, cvd_type='deutan', severity=1.0):
    lin = srgb_to_linear(srgb)
    return linear_to_srgb(lin @ cvd_matrix(cvd_type, severity).T)


def gamut_compress_preserve_luminance(linear_rgb, reference_rgb):
    corrected = np.asarray(linear_rgb, dtype=np.float64)
    reference = np.asarray(reference_rgb, dtype=np.float64)

    target_luma = np.sum(reference * LINEAR_LUMA, axis=-1, keepdims=True)
    corrected_luma = np.sum(corrected * LINEAR_LUMA, axis=-1, keepdims=True)
    balanced = corrected + (target_luma - corrected_luma)

    neutral = np.broadcast_to(target_luma, balanced.shape)
    chroma = balanced - neutral
    limits = np.full_like(chroma, np.inf)
    eps = 1e-12
    np.divide(1.0 - neutral, chroma, out=limits, where=chroma > eps)
    np.divide(neutral, -chroma, out=limits, where=chroma < -eps)

    min_limit = np.min(limits, axis=-1, keepdims=True)
    q = np.zeros_like(min_limit)
    np.divide(1.0, min_limit, out=q, where=np.isfinite(min_limit) & (min_limit > eps))
    q = np.where(min_limit <= eps, np.inf, q)
    excess = np.maximum(q - 1.0, 0.0)
    compressed_q = 1.0 - GAMUT_EDGE_INSET * (
        1.0 - np.exp(-np.square(excess / GAMUT_SOFTNESS))
    )
    scale = np.ones_like(q)
    np.divide(compressed_q, q, out=scale, where=q > 1.0)

    mapped = neutral + chroma * scale
    return np.clip(mapped, 0.0, 1.0)


def daltonize(srgb, cvd_type='deutan', severity=1.0, gain=1.0):
    lin = srgb_to_linear(srgb)
    err = lin - lin @ cvd_matrix(cvd_type, severity).T
    corrected = lin + gain * (err @ ERROR_SHIFT[cvd_type].T)
    corrected = gamut_compress_preserve_luminance(corrected, lin)
    return linear_to_srgb(corrected)


def invert_lut(rgb, gain=1.0):
    return rgb + gain * ((1.0 - rgb) - rgb)


def grayscale_lut(rgb, gain=1.0):
    lin = srgb_to_linear(rgb)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722])
    gray = linear_to_srgb(np.stack([lum] * 3, axis=-1))
    return rgb + gain * (gray - rgb)


def apply_mode(rgb, mode, severity=1.0, gain=1.0):
    if mode == 'off':
        return np.array(rgb, dtype=np.float64, copy=True)
    if mode in CVD_TYPES:
        return daltonize(rgb, mode, severity, gain)
    if mode == 'invert':
        return invert_lut(rgb, gain)
    if mode == 'gray':
        return grayscale_lut(rgb, gain)
    raise ValueError('unknown mode %r' % mode)


def normalize_custom_config(config=None):
    out = dict(CUSTOM_DEFAULTS)
    if config:
        out.update(config)
    if out['mode'] not in MODES:
        raise ValueError('unknown mode %r' % out['mode'])
    if out['algorithm'] not in ('nvidia', 'classic'):
        raise ValueError('unknown correction algorithm %r' % out['algorithm'])
    for key in CUSTOM_DEFAULTS:
        if key not in ('mode', 'algorithm'):
            out[key] = float(out[key])
    return out


@lru_cache(maxsize=2)
def _nvidia_transform_image(mode):
    if mode not in NVIDIA_TRANSFORM_PATHS:
        raise ValueError(
            "NVIDIA's published transform supports protan and deutan only")
    from PIL import Image

    path = NVIDIA_TRANSFORM_PATHS[mode]
    if not path.is_file():
        raise ValueError('NVIDIA reference transform is missing: %s' % path)
    image = np.asarray(Image.open(path).convert('RGB'), dtype=np.uint8)
    if image.shape != (4096, 4096, 3):
        raise ValueError('NVIDIA reference transform has an unexpected size')
    return image


def nvidia_daltonize(rgb, mode, severity=1.0):
    source = np.asarray(rgb, dtype=np.float64)
    rgb8 = np.clip(np.rint(source * 255.0), 0, 255).astype(np.uint16)
    red, green, blue = rgb8[..., 0], rgb8[..., 1], rgb8[..., 2]
    x = (red % 16) * 256 + blue
    y = (red // 16) * 256 + green
    target = _nvidia_transform_image(mode)[y, x].astype(np.float64) / 255.0
    amount = float(np.clip(severity, 0.0, 1.0))
    source_linear = srgb_to_linear(source)
    target_linear = srgb_to_linear(target)
    return linear_to_srgb(source_linear + amount * (target_linear - source_linear))


def custom_filter_is_identity(config):
    cfg = normalize_custom_config(config)
    return (cfg['mode'] == 'off'
            and abs(cfg['exposure']) < 1e-9
            and abs(cfg['contrast'] - 1.0) < 1e-9
            and abs(cfg['saturation'] - 1.0) < 1e-9
            and abs(cfg['gamma'] - 1.0) < 1e-9
            and abs(cfg['hue']) < 1e-9
            and abs(cfg['temperature']) < 1e-9
            and abs(cfg['tint']) < 1e-9
            and abs(cfg['red'] - 1.0) < 1e-9
            and abs(cfg['green'] - 1.0) < 1e-9
            and abs(cfg['blue'] - 1.0) < 1e-9)


def apply_custom(rgb, config):
    cfg = normalize_custom_config(config)
    source = np.asarray(rgb, dtype=np.float64)
    if custom_filter_is_identity(cfg):
        return np.array(source, copy=True)
    result = np.array(source, copy=True)
    mode = cfg['mode']

    if mode in CVD_TYPES:
        if cfg['algorithm'] == 'nvidia':
            result = nvidia_daltonize(source, mode, cfg['severity'])
        else:
            reference_linear = srgb_to_linear(source)
            matrix = cvd_matrix(mode, np.clip(cfg['severity'], 0.0, 1.0))
            error = reference_linear - reference_linear @ matrix.T
            corrected = reference_linear + cfg['correction'] * (
                error @ ERROR_SHIFT[mode].T)
            target_luma = np.sum(reference_linear * LINEAR_LUMA, axis=-1, keepdims=True)
            corrected_luma = np.sum(corrected * LINEAR_LUMA, axis=-1, keepdims=True)
            desired_luma = corrected_luma + np.clip(
                cfg['luminance'], 0.0, 1.0) * (target_luma - corrected_luma)
            corrected += desired_luma - corrected_luma

            gamut_reference = np.broadcast_to(desired_luma, corrected.shape)
            corrected = gamut_compress_preserve_luminance(corrected, gamut_reference)
            result = linear_to_srgb(corrected)
    elif mode == 'gray':
        result = grayscale_lut(source, 1.0)
    elif mode == 'invert':
        result = 1.0 - source

    if abs(cfg['hue']) > 1e-9:
        angle = np.deg2rad(cfg['hue'])
        cosine, sine = np.cos(angle), np.sin(angle)
        y = result @ np.array([0.299, 0.587, 0.114])
        i = result @ np.array([0.596, -0.274, -0.322])
        q = result @ np.array([0.211, -0.523, 0.312])
        rotated_i = i * cosine - q * sine
        rotated_q = i * sine + q * cosine
        result = np.stack([
            y + 0.956 * rotated_i + 0.621 * rotated_q,
            y - 0.272 * rotated_i - 0.647 * rotated_q,
            y - 1.106 * rotated_i + 1.703 * rotated_q,
        ], axis=-1)

    luma = np.sum(result * LINEAR_LUMA, axis=-1, keepdims=True)
    result = luma + (result - luma) * cfg['saturation']
    result *= 2.0 ** cfg['exposure']
    result += np.array([0.12, 0.02, -0.12]) * cfg['temperature']
    result += np.array([0.08, -0.10, 0.08]) * cfg['tint']
    result *= np.array([cfg['red'], cfg['green'], cfg['blue']])
    result = (result - 0.5) * cfg['contrast'] + 0.5
    result = np.power(np.clip(result, 0.0, 1.0), 1.0 / max(cfg['gamma'], 1e-6))
    return np.clip(result, 0.0, 1.0)


def find_lut(blob):
    _, _, _, blk_off, blk_cnt = struct.unpack_from('<IHHII', blob, 0)
    pos = 8 + blk_off
    data_off = data_size = None
    for _ in range(blk_cnt):
        tag = blob[pos:pos + 4]
        rel, size = struct.unpack_from('<II', blob, pos + 4)
        if tag == b'DATA':
            data_off, data_size = pos + 4 + rel, size
        pos += 12
    if data_off is None:
        raise ValueError('no DATA block')
    if blob[data_off + 20] != 0:
        raise ValueError('DATA block is compressed; in-place LUT patching unsafe')
    end = data_off + data_size - len(KV3_TERMINATOR)
    start = end - LUT_BYTES
    if start < data_off:
        raise ValueError('file too small to contain a %d^3 LUT' % LUT_DIM)
    if blob[end:end + len(KV3_TERMINATOR)] != KV3_TERMINATOR:
        raise ValueError('KV3 terminator not where expected; format changed')
    return start, end


def find_color_correction_flag(blob):
    start, _ = find_lut(blob)
    window_start = max(0, start - 64)
    window = blob[window_start:start]
    idx = window.rfind(CC_TYPE_PREFIX)
    if idx < 0:
        return None
    pos = window_start + idx + len(CC_TYPE_PREFIX)
    if blob[pos] not in (KV3_BOOL_TRUE, KV3_BOOL_FALSE):
        return None
    return pos


def read_lut(blob):
    start, end = find_lut(blob)
    arr = np.frombuffer(blob[start:end], dtype=np.uint8).reshape(-1, 4)
    return arr[:, :3].astype(np.float64) / 255.0, arr[:, 3]


def patch_vpost(blob, mode='deutan', severity=1.0, gain=1.0,
                custom_config=None):
    start, end = find_lut(blob)
    rgb, alpha = read_lut(blob)
    corrected = (apply_custom(rgb, custom_config)
                 if custom_config is not None
                 else apply_mode(rgb, mode, severity, gain))

    out = np.empty((corrected.shape[0], 4), dtype=np.uint8)
    out[:, :3] = np.clip(np.rint(corrected * 255.0), 0, 255).astype(np.uint8)
    out[:, 3] = alpha
    patched = bytearray(blob)
    patched[start:end] = out.tobytes()

    enabled = None
    flag = find_color_correction_flag(blob)
    if flag is not None:
        enabled = patched[flag] == KV3_BOOL_TRUE
        identity = (custom_filter_is_identity(custom_config)
                    if custom_config is not None else mode == 'off')
        patched[flag] = blob[flag] if identity else KV3_BOOL_TRUE

    assert len(patched) == len(blob), 'patch changed file size'
    return bytes(patched), rgb, corrected, enabled
