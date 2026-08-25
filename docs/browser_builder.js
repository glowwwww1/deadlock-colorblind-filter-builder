"use strict";

const VPOST_FILES = [
  "basepostprocess.vpost_c",
  "basepostprocess_deadlock.vpost_c",
  "caldera.vpost_c",
  "caldera_base_north.vpost_c",
  "caldera_base_south.vpost_c",
  "caldera_lane_blue.vpost_c",
  "caldera_lane_orange.vpost_c",
  "caldera_lane_purple.vpost_c",
  "caldera_lane_yellow.vpost_c",
  "character_picker_glyph_bg.vpost_c",
  "hero_select.vpost_c",
  "leylines_north.vpost_c",
  "leylines_south.vpost_c",
  "main_menu.vpost_c",
  "test_neutral.vpost_c",
  "toolscene.vpost_c",
  "toolscene_deadlock.vpost_c",
];

const HEALTH_FILES = {
  "panorama/styles/hud_health.vcss_c": "hud_health.vcss_c",
  "panorama/styles/hud_health_container.vcss_c": "hud_health_container.vcss_c",
  "panorama/styles/hud_health_pips.vcss_c": "hud_health_pips.vcss_c",
  "panorama/styles/hud_health_single_bar.vcss_c": "hud_health_single_bar.vcss_c",
  "panorama/styles/hud_health_stacked.vcss_c": "hud_health_stacked.vcss_c",
  "panorama/styles/unit_status.vcss_c": "unit_status.vcss_c",
  "panorama/styles/unit_status_old.vcss_c": "unit_status_old.vcss_c",
  "panorama/styles/unit_status_v2.vcss_c": "unit_status_v2.vcss_c",
};

const HEALTH_NAMED_COLORS = {
  colorEnemy: [255, 65, 13],
  colorFriendly: [0, 255, 153],
  courageBrightColor: [236, 151, 25],
  darkblue: [0, 0, 139],
  darkorange: [255, 140, 0],
  lightgreen: [144, 238, 144],
  spiritBrightColor: [206, 144, 255],
  vivaciousGreen: [20, 35, 4],
};

const HEALTH_COLORS = {
  "panorama/styles/hud_health.vcss_c": [
    "#FCFF6D", "#FF410D", "#FFE3DB", "#4bdc68", "rgb(232, 127, 61)",
    "rgb(122, 165, 69)", "#00FF99", "#FFEFD7", "#cc340a", "#f6805f",
    "#00D37F", "#FF5656", "#580000", "colorEnemy", "colorFriendly",
    "courageBrightColor", "spiritBrightColor",
  ],
  "panorama/styles/hud_health_container.vcss_c": [
    "#D74949", "#DDFF56", "#FF5656", "rgb(255, 130, 130)", "#FFED79",
    "lightgreen", "vivaciousGreen",
  ],
  "panorama/styles/hud_health_pips.vcss_c": [
    "#E4D0B2", "#87FF87", "#FF410D", "#E7B659", "#5B79E6", "#8B0000",
    "#FF8787", "#7DDAB0", "#78c2ff", "#00FFFF", "#AED6F1",
    "rgba( 255, 215, 216, 1 )", "rgba( 133, 255, 133, 1 )",
    "rgba( 10, 230, 80, 0 )", "rgba( 255, 250, 219, 1 )",
    "darkblue", "darkorange",
  ],
  "panorama/styles/hud_health_single_bar.vcss_c": [
    "#FCFF6D", "#FF410D", "#FFE3DB", "rgb(119, 219, 119)",
    "rgb(232, 127, 61)", "#00FF99", "#FFEFD7", "#cc340a", "#f6805f",
    "#00D37F", "#FF5656", "#580000", "colorEnemy", "colorFriendly",
  ],
  "panorama/styles/hud_health_stacked.vcss_c": [
    "#4bdc68", "courageBrightColor", "spiritBrightColor",
  ],
  "panorama/styles/unit_status.vcss_c": [
    "#E7B659", "#5B79E6", "#5befb5", "#fd4949", "#FFEFD7", "#ffedb8",
    "#f24d4d", "#ffe55b", "#504c47", "#fcb43d", "#e29afd", "#46e2ac",
    "rgb(113, 0, 0)", "#b82323", "#5fff80", "#e9e76a", "#6a75e9",
    "#b95f5f", "#acca91", "#62FBBE", "lightgreen",
  ],
  "panorama/styles/unit_status_old.vcss_c": [
    "#E7B659", "#5B79E6", "#7DDAB0", "#62FBBE", "lightgreen",
  ],
  "panorama/styles/unit_status_v2.vcss_c": [
    "#E7B659", "#5B79E6", "#5befb5", "#fd4949", "#FFEFD7", "#ffedb8",
    "#f24d4d", "#ffe55b", "#504c47", "#fcb43d", "#e29afd", "#46e2ac",
    "rgb(67, 12, 12)", "rgb(64, 8, 8)", "rgb(80, 2, 2)", "#b82323",
    "rgb(74, 15, 15)", "#bf3333", "#c13030", "#d8d2af", "#c7c19d",
    "#5fff80", "#e9e76a", "#6a75e9", "#b95f5f", "#acca91", "#FB4949",
    "rgb(255, 194, 194)", "#62FBBE", "lightgreen",
  ],
};

const CVD_MATRICES = {
  protan: [
    0.152286, 1.052583, -0.204868,
    0.114503, 0.786281, 0.099216,
    -0.003882, -0.048116, 1.051998,
  ],
  deutan: [
    0.367322, 0.860646, -0.227968,
    0.280085, 0.672501, 0.047413,
    -0.011820, 0.042940, 0.968881,
  ],
  tritan: [
    1.255528, -0.076749, -0.178779,
    -0.078411, 0.930809, 0.147602,
    0.004733, 0.691367, 0.303900,
  ],
};

const LINEAR_LUMA = [0.2126, 0.7152, 0.0722];
const DEFAULT_OUTLINE = [162, 34, 34];
const OUTLINE_TEMPLATE_VALUES = [127, 128, 255];
const OUTLINE_TEMPLATE_OFFSETS = [8592, 8600, 8608];
const RESOURCE_CACHE = new Map();
const NVIDIA_CACHE = new Map();
const TEXT_ENCODER = new TextEncoder();

function relativeUrl(path) {
  return new URL(path, document.baseURI).href;
}

async function fetchBytes(path) {
  const url = relativeUrl(path);
  if (!RESOURCE_CACHE.has(url)) {
    RESOURCE_CACHE.set(url, fetch(url).then(response => {
      if (!response.ok) throw new Error(`Could not load ${path} (${response.status}).`);
      return response.arrayBuffer();
    }).then(buffer => new Uint8Array(buffer)));
  }
  return new Uint8Array(await RESOURCE_CACHE.get(url));
}

function clamp(value, low = 0, high = 1) {
  return Math.min(high, Math.max(low, value));
}

function roundEven(value) {
  const lower = Math.floor(value);
  const fraction = value - lower;
  if (fraction < 0.5) return lower;
  if (fraction > 0.5) return lower + 1;
  return lower % 2 === 0 ? lower : lower + 1;
}

function srgbChannelToLinear(value) {
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

function linearChannelToSrgb(value) {
  const bounded = clamp(value);
  return bounded <= 0.0031308 ? bounded * 12.92 : 1.055 * bounded ** (1 / 2.4) - 0.055;
}

function toLinear(rgb) {
  return rgb.map(srgbChannelToLinear);
}

function toSrgb(rgb) {
  return rgb.map(linearChannelToSrgb);
}

function dot(left, right) {
  return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
}

function fitGamut(corrected, desiredLuma) {
  const correctedLuma = dot(corrected, LINEAR_LUMA);
  const balanced = corrected.map(value => value + desiredLuma - correctedLuma);
  const chroma = balanced.map(value => value - desiredLuma);
  const limits = chroma.map(value => {
    if (value > 1e-12) return (1 - desiredLuma) / value;
    if (value < -1e-12) return desiredLuma / -value;
    return Infinity;
  });
  const minimum = Math.min(...limits);
  let q = 0;
  if (Number.isFinite(minimum) && minimum > 1e-12) q = 1 / minimum;
  if (minimum <= 1e-12) q = Infinity;
  let scale = 1;
  if (q > 1) {
    const excess = q - 1;
    const compressed = 1 - 0.01 * (1 - Math.exp(-((excess / 0.015) ** 2)));
    scale = compressed / q;
  }
  return chroma.map(value => clamp(desiredLuma + value * scale));
}

function classicFilter(source, settings) {
  const reference = toLinear(source);
  const full = CVD_MATRICES[settings.mode];
  const severity = clamp(settings.severity);
  const simulated = [0, 1, 2].map(row => {
    const base = row * 3;
    const transformed = reference[0] * full[base]
      + reference[1] * full[base + 1]
      + reference[2] * full[base + 2];
    return reference[row] * (1 - severity) + transformed * severity;
  });
  const error = reference.map((value, index) => value - simulated[index]);
  const shifted = settings.mode === "tritan"
    ? [error[0] + 0.7 * error[2], error[1] + 0.7 * error[2], 0]
    : [0, 0.7 * error[0] + error[1], 0.7 * error[0] + error[2]];
  const corrected = reference.map((value, index) => value + shifted[index]);
  const sourceLuma = dot(reference, LINEAR_LUMA);
  const correctedLuma = dot(corrected, LINEAR_LUMA);
  const desiredLuma = correctedLuma
    + clamp(settings.luminance) * (sourceLuma - correctedLuma);
  return toSrgb(fitGamut(corrected, desiredLuma));
}

async function imageElement(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener("load", () => resolve(image), { once: true });
    image.addEventListener("error", () => reject(new Error(`Could not decode ${url}.`)), { once: true });
    image.src = url;
  });
}

async function loadNvidiaTransform(mode) {
  if (NVIDIA_CACHE.has(mode)) return NVIDIA_CACHE.get(mode);
  const promise = (async () => {
    const path = mode === "protan" ? "assets/protanopia.png" : "assets/deuteranopia.png";
    const image = await imageElement(relativeUrl(path));
    if (image.naturalWidth !== 4096 || image.naturalHeight !== 4096) {
      throw new Error("The NVIDIA reference transform has an unexpected size.");
    }
    const canvas = document.createElement("canvas");
    canvas.width = 4096;
    canvas.height = 4096;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(image, 0, 0);
    return context.getImageData(0, 0, 4096, 4096).data;
  })();
  NVIDIA_CACHE.set(mode, promise);
  return promise;
}

function nvidiaTargetBytes(sourceBytes, pixels) {
  const [red, green, blue] = sourceBytes;
  const x = (red % 16) * 256 + blue;
  const y = Math.floor(red / 16) * 256 + green;
  const offset = (y * 4096 + x) * 4;
  return [pixels[offset], pixels[offset + 1], pixels[offset + 2]];
}

function nvidiaFilter(sourceBytes, settings, pixels) {
  const source = sourceBytes.map(value => value / 255);
  const target = nvidiaTargetBytes(sourceBytes, pixels).map(value => value / 255);
  const sourceLinear = toLinear(source);
  const targetLinear = toLinear(target);
  const severity = clamp(settings.severity);
  return toSrgb(sourceLinear.map((value, index) =>
    value + severity * (targetLinear[index] - value)));
}

function filterBytes(rgb, settings, nvidiaPixels) {
  if (settings.mode === "off") return rgb.slice();
  const filtered = settings.algorithm === "nvidia"
    ? nvidiaFilter(rgb, settings, nvidiaPixels)
    : classicFilter(rgb.map(value => value / 255), settings);
  if (settings.algorithm === "nvidia") {
    return filtered.map(value => clamp(Math.round(value * 255), 0, 255));
  }
  return filtered.map(value => clamp(roundEven(value * 255), 0, 255));
}

function readAscii(bytes, offset, length) {
  let text = "";
  for (let index = 0; index < length; index += 1) text += String.fromCharCode(bytes[offset + index]);
  return text;
}

function findLut(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const blockOffset = view.getUint32(8, true);
  const blockCount = view.getUint32(12, true);
  let position = 8 + blockOffset;
  let dataOffset = -1;
  let dataSize = 0;
  for (let index = 0; index < blockCount; index += 1) {
    const tag = readAscii(bytes, position, 4);
    const relative = view.getUint32(position + 4, true);
    const size = view.getUint32(position + 8, true);
    if (tag === "DATA") {
      dataOffset = position + 4 + relative;
      dataSize = size;
    }
    position += 12;
  }
  if (dataOffset < 0) throw new Error("A post-processing resource has no DATA block.");
  if (bytes[dataOffset + 20] !== 0) throw new Error("A post-processing DATA block is compressed.");
  const end = dataOffset + dataSize - 4;
  const start = end - 32 ** 3 * 4;
  if (start < dataOffset) throw new Error("A post-processing resource has no 32³ LUT.");
  if (bytes[end] !== 0 || bytes[end + 1] !== 0xdd
      || bytes[end + 2] !== 0xee || bytes[end + 3] !== 0xff) {
    throw new Error("A post-processing resource has an unexpected KV3 terminator.");
  }
  return [start, end];
}

function patchVpost(bytes, settings, nvidiaPixels) {
  const [start, end] = findLut(bytes);
  const output = new Uint8Array(bytes);
  for (let offset = start; offset < end; offset += 4) {
    const filtered = filterBytes(
      [bytes[offset], bytes[offset + 1], bytes[offset + 2]], settings, nvidiaPixels);
    output[offset] = filtered[0];
    output[offset + 1] = filtered[1];
    output[offset + 2] = filtered[2];
  }
  let flag = -1;
  for (let offset = start - 2; offset >= Math.max(0, start - 64); offset -= 1) {
    if (bytes[offset] === 0x0b && bytes[offset + 1] === 0x07) {
      flag = offset + 2;
      break;
    }
  }
  if (flag >= 0 && (bytes[flag] === 0x0d || bytes[flag] === 0x0e)
      && settings.mode !== "off") output[flag] = 0x0d;
  return output;
}

function parseCssColor(value) {
  if (HEALTH_NAMED_COLORS[value]) return HEALTH_NAMED_COLORS[value].slice();
  if (value.startsWith("#")) {
    return [1, 3, 5].map(index => Number.parseInt(value.slice(index, index + 2), 16));
  }
  return [...value.matchAll(/\d+/g)].slice(0, 3).map(match => Number(match[0]));
}

function formatCssColor(value, rgb) {
  let alpha = "";
  if (value.startsWith("rgba")) {
    const numbers = [...value.matchAll(/[\d.]+/g)].map(match => Number(match[0]));
    alpha = roundEven(clamp(numbers[3]) * 255).toString(16).padStart(2, "0").toUpperCase();
  }
  return `#${rgb.map(component => component.toString(16).padStart(2, "0").toUpperCase()).join("")}${alpha}`;
}

function replaceFixed(bytes, sourceText, replacementText) {
  const source = TEXT_ENCODER.encode(sourceText);
  const replacement = TEXT_ENCODER.encode(replacementText);
  if (replacement.length > source.length) throw new Error("A healthbar color replacement is too long.");
  let count = 0;
  for (let offset = 0; offset <= bytes.length - source.length; offset += 1) {
    let matches = true;
    for (let index = 0; index < source.length; index += 1) {
      if (bytes[offset + index] !== source[index]) {
        matches = false;
        break;
      }
    }
    if (!matches) continue;
    bytes.set(replacement, offset);
    bytes.fill(0x20, offset + replacement.length, offset + source.length);
    count += 1;
    offset += source.length - 1;
  }
  return count;
}

function patchHealthStyle(bytes, internal, settings, nvidiaPixels) {
  const output = new Uint8Array(bytes);
  let replacements = 0;
  for (const literal of HEALTH_COLORS[internal]) {
    const rgb = filterBytes(parseCssColor(literal), settings, nvidiaPixels);
    replacements += replaceFixed(output, literal, formatCssColor(literal, rgb));
  }
  if (replacements === 0) throw new Error(`No healthbar colors were found in ${internal}.`);
  return output;
}

function parseHexColor(value) {
  if (!/^#[0-9a-f]{6}$/i.test(value)) throw new Error("The outline color must use #RRGGBB format.");
  return [1, 3, 5].map(index => Number.parseInt(value.slice(index, index + 2), 16));
}

async function patchOutlineColor(rgb) {
  const template = await fetchBytes("resources/outline_color_template.vdata_c");
  if (template.length !== 21291) throw new Error("The outline-color template has an unexpected size.");
  const view = new DataView(template.buffer, template.byteOffset, template.byteLength);
  for (let index = 0; index < 3; index += 1) {
    if (view.getUint32(OUTLINE_TEMPLATE_OFFSETS[index], true) !== OUTLINE_TEMPLATE_VALUES[index]
        || view.getUint32(OUTLINE_TEMPLATE_OFFSETS[index] + 4, true) !== 0) {
      throw new Error("The outline-color template failed validation.");
    }
    view.setUint32(OUTLINE_TEMPLATE_OFFSETS[index], rgb[index], true);
    view.setUint32(OUTLINE_TEMPLATE_OFFSETS[index] + 4, 0, true);
  }
  return template;
}

function crc32(bytes) {
  let value = 0xffffffff;
  for (const byte of bytes) {
    value ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value >>> 1) ^ (0xedb88320 & -(value & 1));
    }
  }
  return (value ^ 0xffffffff) >>> 0;
}

function rotateLeft(value, amount) {
  return ((value << amount) | (value >>> (32 - amount))) >>> 0;
}

function md5(bytes) {
  const paddedLength = Math.ceil((bytes.length + 9) / 64) * 64;
  const padded = new Uint8Array(paddedLength);
  padded.set(bytes);
  padded[bytes.length] = 0x80;
  const paddedView = new DataView(padded.buffer);
  paddedView.setUint32(paddedLength - 8, (bytes.length * 8) >>> 0, true);
  paddedView.setUint32(paddedLength - 4, Math.floor(bytes.length / 0x20000000), true);
  const shifts = [
    7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
    5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20,
    4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
    6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21,
  ];
  const constants = Array.from({ length: 64 }, (_, index) =>
    Math.floor(Math.abs(Math.sin(index + 1)) * 0x100000000) >>> 0);
  let a0 = 0x67452301;
  let b0 = 0xefcdab89;
  let c0 = 0x98badcfe;
  let d0 = 0x10325476;
  for (let offset = 0; offset < padded.length; offset += 64) {
    const words = Array.from({ length: 16 }, (_, index) =>
      paddedView.getUint32(offset + index * 4, true));
    let a = a0;
    let b = b0;
    let c = c0;
    let d = d0;
    for (let index = 0; index < 64; index += 1) {
      let f;
      let g;
      if (index < 16) {
        f = (b & c) | (~b & d);
        g = index;
      } else if (index < 32) {
        f = (d & b) | (~d & c);
        g = (5 * index + 1) % 16;
      } else if (index < 48) {
        f = b ^ c ^ d;
        g = (3 * index + 5) % 16;
      } else {
        f = c ^ (b | ~d);
        g = (7 * index) % 16;
      }
      const previousD = d;
      d = c;
      c = b;
      const sum = (a + f + constants[index] + words[g]) >>> 0;
      b = (b + rotateLeft(sum, shifts[index])) >>> 0;
      a = previousD;
    }
    a0 = (a0 + a) >>> 0;
    b0 = (b0 + b) >>> 0;
    c0 = (c0 + c) >>> 0;
    d0 = (d0 + d) >>> 0;
  }
  const digest = new Uint8Array(16);
  const view = new DataView(digest.buffer);
  view.setUint32(0, a0, true);
  view.setUint32(4, b0, true);
  view.setUint32(8, c0, true);
  view.setUint32(12, d0, true);
  return digest;
}

function concatenate(parts) {
  const length = parts.reduce((total, part) => total + part.length, 0);
  const output = new Uint8Array(length);
  let offset = 0;
  for (const part of parts) {
    output.set(part, offset);
    offset += part.length;
  }
  return output;
}

function uint16(value) {
  const bytes = new Uint8Array(2);
  new DataView(bytes.buffer).setUint16(0, value, true);
  return bytes;
}

function uint32(value) {
  const bytes = new Uint8Array(4);
  new DataView(bytes.buffer).setUint32(0, value >>> 0, true);
  return bytes;
}

function cstring(value) {
  return concatenate([TEXT_ENCODER.encode(value), new Uint8Array(1)]);
}

function buildVpkArchive(files) {
  const internals = [...files.keys()].sort();
  const metadata = new Map();
  const dataParts = [];
  let dataOffset = 0;
  const tree = new Map();
  for (const internal of internals) {
    const data = files.get(internal);
    const slash = internal.lastIndexOf("/");
    const folder = slash >= 0 ? internal.slice(0, slash) : " ";
    const filename = slash >= 0 ? internal.slice(slash + 1) : internal;
    const dot = filename.lastIndexOf(".");
    const name = filename.slice(0, dot);
    const extension = filename.slice(dot + 1);
    if (!tree.has(extension)) tree.set(extension, new Map());
    if (!tree.get(extension).has(folder)) tree.get(extension).set(folder, []);
    tree.get(extension).get(folder).push(name);
    metadata.set(internal, { offset: dataOffset, length: data.length, crc: crc32(data) });
    dataParts.push(data);
    dataOffset += data.length;
  }
  const treeParts = [];
  for (const extension of [...tree.keys()].sort()) {
    treeParts.push(cstring(extension));
    const folders = tree.get(extension);
    for (const folder of [...folders.keys()].sort()) {
      treeParts.push(cstring(folder));
      for (const name of folders.get(folder).sort()) {
        const internal = folder === " "
          ? `${name}.${extension}`
          : `${folder}/${name}.${extension}`;
        const entry = metadata.get(internal);
        treeParts.push(
          cstring(name),
          uint32(entry.crc),
          uint16(0),
          uint16(0x7fff),
          uint32(entry.offset),
          uint32(entry.length),
          uint16(0xffff),
        );
      }
      treeParts.push(new Uint8Array(1));
    }
    treeParts.push(new Uint8Array(1));
  }
  treeParts.push(new Uint8Array(1));
  const treeBytes = concatenate(treeParts);
  const dataBytes = concatenate(dataParts);
  const header = concatenate([
    uint32(0x55aa1234), uint32(2), uint32(treeBytes.length),
    uint32(dataBytes.length), uint32(0), uint32(48), uint32(0),
  ]);
  const body = concatenate([header, treeBytes, dataBytes]);
  const treeDigest = md5(treeBytes);
  const archiveDigest = md5(new Uint8Array());
  const wholeDigest = md5(concatenate([body, treeDigest, archiveDigest]));
  return concatenate([body, treeDigest, archiveDigest, wholeDigest]);
}

function validateSettings(settings) {
  if (!["off", "protan", "deutan", "tritan"].includes(settings.mode)) {
    throw new Error("Unknown vision profile.");
  }
  if (!["nvidia", "classic"].includes(settings.algorithm)) {
    throw new Error("Unknown correction algorithm.");
  }
  if (settings.algorithm === "nvidia" && settings.mode === "tritan") {
    throw new Error("NVIDIA's transform does not support Tritan.");
  }
  if (!Number.isFinite(settings.severity) || settings.severity < 0 || settings.severity > 1) {
    throw new Error("Severity must be between 0 and 1.");
  }
  if (!Number.isFinite(settings.luminance) || settings.luminance < 0 || settings.luminance > 1) {
    throw new Error("Luminance preservation must be between 0 and 1.");
  }
  if (![1, 2].includes(settings.thickness)) throw new Error("Outline thickness must be 1 or 2.");
  if (typeof settings.healthbars !== "boolean") throw new Error("Healthbar filtering must be on or off.");
  parseHexColor(settings.outlineColor);
}

async function buildVpk(settings, onProgress = () => {}) {
  validateSettings(settings);
  const nvidiaPixels = settings.algorithm === "nvidia" && settings.mode !== "off"
    ? await loadNvidiaTransform(settings.mode)
    : null;
  const files = new Map();
  for (let index = 0; index < VPOST_FILES.length; index += 1) {
    const filename = VPOST_FILES[index];
    onProgress(`Building scene filter ${index + 1} of ${VPOST_FILES.length}…`);
    const original = await fetchBytes(`resources/vpost/${filename}`);
    files.set(`postprocessing/${filename}`, patchVpost(original, settings, nvidiaPixels));
    await new Promise(resolve => setTimeout(resolve, 0));
  }
  if (settings.thickness === 2) {
    files.set("shaders/vfx/generate_outlines_pc_50_ps.vcs", await fetchBytes("resources/outline_2x.vcs"));
  }
  const outline = parseHexColor(settings.outlineColor);
  if (outline.some((value, index) => value !== DEFAULT_OUTLINE[index])) {
    files.set("scripts/generic_data.vdata_c", await patchOutlineColor(outline));
  }
  if (settings.healthbars && settings.mode !== "off") {
    let index = 0;
    for (const [internal, filename] of Object.entries(HEALTH_FILES)) {
      index += 1;
      onProgress(`Building healthbars ${index} of ${Object.keys(HEALTH_FILES).length}…`);
      const original = await fetchBytes(`resources/vcss/${filename}`);
      files.set(internal, patchHealthStyle(original, internal, settings, nvidiaPixels));
      await new Promise(resolve => setTimeout(resolve, 0));
    }
  }
  onProgress("Packaging VPK…");
  return buildVpkArchive(files);
}

globalThis.DeadlockBrowserBuilder = {
  buildVpk,
  buildVpkArchive,
  crc32,
  filterBytes,
  loadNvidiaPixels(mode, pixels) {
    NVIDIA_CACHE.set(mode, Promise.resolve(pixels));
  },
  md5,
  patchOutlineColor,
  patchVpost,
};
