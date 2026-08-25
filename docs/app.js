"use strict";

const DEFAULTS = Object.freeze({
  mode: "deutan",
  algorithm: "nvidia",
  severity: 100,
  luminance: 100,
  healthbars: false,
  thickness: 1,
  outlineColor: "#a22222",
});

const state = { ...DEFAULTS };
const controls = new Map();
let split = 0.5;
let renderer = null;
let previewImages = [];
let previewImageIndex = 0;

const CONTROL_DEFINITIONS = [
  ["severity", "Severity", 0, 100, 1, value => `${value}%`],
  ["luminance", "Luminance preservation", 0, 100, 1, value => `${value}%`],
];

function makeRange(definition, destination) {
  const [key, title, min, max, step, format] = definition;
  const label = document.createElement("label");
  label.className = "range-control";
  const heading = document.createElement("span");
  const name = document.createElement("span");
  const output = document.createElement("output");
  name.textContent = title;
  heading.append(name, output);

  const input = document.createElement("input");
  input.type = "range";
  input.min = String(min);
  input.max = String(max);
  input.step = String(step);
  input.value = String(state[key]);
  input.id = key;
  input.setAttribute("aria-label", title);
  label.append(heading, input);
  destination.appendChild(label);

  const record = { input, output, label, min, max, format };
  controls.set(key, record);
  input.addEventListener("input", () => {
    state[key] = Number(input.value);
    updateRange(record, state[key]);
    renderer?.render();
  });
  updateRange(record, state[key]);
}

function updateRange(record, value) {
  const text = record.format(value);
  record.output.value = text;
  record.output.textContent = text;
  const percentage = 100 * (value - record.min) / (record.max - record.min);
  record.input.style.setProperty("--fill", `${percentage}%`);
}

function setControlEnabled(key, enabled) {
  const record = controls.get(key);
  record.input.disabled = !enabled;
  record.label.classList.toggle("disabled", !enabled);
}

function setControlVisible(key, visible) {
  controls.get(key).label.classList.toggle("hidden", !visible);
}

function updateAvailability() {
  const enabled = state.mode !== "off";
  const nvidiaOption = document.querySelector('#algorithm option[value="nvidia"]');
  nvidiaOption.disabled = state.mode === "tritan";
  if (state.mode === "tritan" && state.algorithm === "nvidia") {
    state.algorithm = "classic";
    document.getElementById("algorithm").value = state.algorithm;
  }
  const classic = state.algorithm === "classic";
  document.getElementById("algorithm").disabled = !enabled;
  setControlEnabled("severity", enabled);
  setControlVisible("luminance", classic);
  setControlEnabled("luminance", enabled && classic);
}

function updatePresetButtons() {
  document.querySelectorAll("[data-mode]").forEach(button => {
    button.classList.toggle("active", button.dataset.mode === state.mode);
  });
}

function updateOutlineButtons() {
  document.querySelectorAll("[data-thickness]").forEach(button => {
    const active = Number(button.dataset.thickness) === state.thickness;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function updateHealthbarToggle() {
  const button = document.getElementById("healthbarToggle");
  button.classList.toggle("active", state.healthbars);
  button.setAttribute("aria-pressed", String(state.healthbars));
}

function applyState(values = {}) {
  Object.assign(state, DEFAULTS, values);
  document.getElementById("algorithm").value = state.algorithm;
  document.getElementById("outlineColor").value = state.outlineColor;
  document.getElementById("outlineColorValue").textContent = state.outlineColor.toUpperCase();
  for (const [key, record] of controls) {
    record.input.value = String(state[key]);
    updateRange(record, state[key]);
  }
  updateAvailability();
  updatePresetButtons();
  updateHealthbarToggle();
  updateOutlineButtons();
  renderer?.render();
}

function setupControls() {
  const filterContainer = document.getElementById("filterControls");
  for (const definition of CONTROL_DEFINITIONS) makeRange(definition, filterContainer);

  document.getElementById("algorithm").addEventListener("change", event => {
    state.algorithm = event.target.value;
    updateAvailability();
    renderer?.render();
  });
  document.querySelectorAll("[data-mode]").forEach(button => {
    button.addEventListener("click", () => {
      state.mode = button.dataset.mode;
      updateAvailability();
      updatePresetButtons();
      renderer?.render();
    });
  });
  document.querySelectorAll("[data-thickness]").forEach(button => {
    button.addEventListener("click", () => {
      state.thickness = Number(button.dataset.thickness);
      updateOutlineButtons();
    });
  });
  document.getElementById("healthbarToggle").addEventListener("click", () => {
    state.healthbars = !state.healthbars;
    updateHealthbarToggle();
  });
  document.getElementById("outlineColor").addEventListener("input", event => {
    state.outlineColor = event.target.value;
    document.getElementById("outlineColorValue").textContent = state.outlineColor.toUpperCase();
  });
  document.getElementById("resetButton").addEventListener("click", () => applyState());
  document.getElementById("downloadButton").addEventListener("click", downloadVpk);
}

function setupDivider() {
  const preview = document.getElementById("preview");
  const divider = document.getElementById("divider");

  function setFromClientX(clientX) {
    const bounds = preview.getBoundingClientRect();
    split = Math.max(0, Math.min(1, (clientX - bounds.left) / bounds.width));
    divider.style.left = `${split * 100}%`;
    divider.setAttribute("aria-valuenow", String(Math.round(split * 100)));
    renderer?.render();
  }

  preview.addEventListener("pointerdown", event => {
    if (event.target.closest(".preview-arrow")) return;
    preview.setPointerCapture(event.pointerId);
    setFromClientX(event.clientX);
  });
  preview.addEventListener("pointermove", event => {
    if (preview.hasPointerCapture(event.pointerId)) setFromClientX(event.clientX);
  });
  preview.addEventListener("pointerup", event => {
    if (preview.hasPointerCapture(event.pointerId)) preview.releasePointerCapture(event.pointerId);
  });
  preview.addEventListener("pointercancel", event => {
    if (preview.hasPointerCapture(event.pointerId)) preview.releasePointerCapture(event.pointerId);
  });
  divider.addEventListener("keydown", event => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    split = Math.max(0, Math.min(1, split + (event.key === "ArrowRight" ? 0.02 : -0.02)));
    divider.style.left = `${split * 100}%`;
    renderer?.render();
  });
}

function compileShader(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    throw new Error(gl.getShaderInfoLog(shader) || "Preview shader compilation failed.");
  }
  return shader;
}

function createRenderer() {
  const canvas = document.getElementById("previewCanvas");
  const gl = canvas.getContext("webgl", { alpha: false, antialias: false });
  if (!gl) throw new Error("WebGL is required for the preview.");

  const vertexSource = `
    attribute vec2 a_position;
    varying vec2 v_uv;
    void main() {
      v_uv = (a_position + 1.0) * 0.5;
      gl_Position = vec4(a_position, 0.0, 1.0);
    }
  `;
  const fragmentSource = `
    precision highp float;
    varying vec2 v_uv;
    uniform sampler2D u_image;
    uniform sampler2D u_nvidia;
    uniform float u_split;
    uniform int u_mode;
    uniform int u_algorithm;
    uniform float u_severity;
    uniform float u_luminance;

    float linearChannel(float value) {
      return value <= 0.04045 ? value / 12.92 : pow((value + 0.055) / 1.055, 2.4);
    }
    vec3 toLinear(vec3 value) {
      return vec3(linearChannel(value.r), linearChannel(value.g), linearChannel(value.b));
    }
    float srgbChannel(float value) {
      value = clamp(value, 0.0, 1.0);
      return value <= 0.0031308 ? value * 12.92 : 1.055 * pow(value, 1.0 / 2.4) - 0.055;
    }
    vec3 toSrgb(vec3 value) {
      return vec3(srgbChannel(value.r), srgbChannel(value.g), srgbChannel(value.b));
    }
    vec3 simulateCvd(vec3 linear) {
      vec3 full;
      if (u_mode == 1) {
        full = vec3(
          dot(linear, vec3(0.152286, 1.052583, -0.204868)),
          dot(linear, vec3(0.114503, 0.786281, 0.099216)),
          dot(linear, vec3(-0.003882, -0.048116, 1.051998))
        );
      } else if (u_mode == 2) {
        full = vec3(
          dot(linear, vec3(0.367322, 0.860646, -0.227968)),
          dot(linear, vec3(0.280085, 0.672501, 0.047413)),
          dot(linear, vec3(-0.011820, 0.042940, 0.968881))
        );
      } else {
        full = vec3(
          dot(linear, vec3(1.255528, -0.076749, -0.178779)),
          dot(linear, vec3(-0.078411, 0.930809, 0.147602)),
          dot(linear, vec3(0.004733, 0.691367, 0.303900))
        );
      }
      return mix(linear, full, u_severity);
    }
    float channelLimit(float neutral, float chroma) {
      if (chroma > 0.000000000001) return (1.0 - neutral) / chroma;
      if (chroma < -0.000000000001) return neutral / -chroma;
      return 1000000000000.0;
    }
    vec3 fitGamut(vec3 corrected, float desiredLuma) {
      vec3 balanced = corrected + vec3(desiredLuma - dot(corrected, vec3(0.2126, 0.7152, 0.0722)));
      vec3 chroma = balanced - vec3(desiredLuma);
      float limit = min(channelLimit(desiredLuma, chroma.r), min(channelLimit(desiredLuma, chroma.g), channelLimit(desiredLuma, chroma.b)));
      float scale = 1.0;
      if (limit <= 0.000000000001) {
        scale = 0.0;
      } else {
        float q = 1.0 / limit;
        if (q > 1.0) {
          float excess = q - 1.0;
          float compressedQ = 1.0 - 0.01 * (1.0 - exp(-pow(excess / 0.015, 2.0)));
          scale = compressedQ / q;
        }
      }
      return clamp(vec3(desiredLuma) + chroma * scale, 0.0, 1.0);
    }
    vec3 nvidiaTarget(vec3 source) {
      vec3 rgb8 = floor(clamp(source, 0.0, 1.0) * 255.0 + 0.5);
      float x = mod(rgb8.r, 16.0) * 256.0 + rgb8.b;
      float y = floor(rgb8.r / 16.0) * 256.0 + rgb8.g;
      return texture2D(u_nvidia, vec2((x + 0.5) / 4096.0, (y + 0.5) / 4096.0)).rgb;
    }
    vec3 filterColor(vec3 source) {
      if (u_mode == 0) return source;
      vec3 reference = toLinear(source);
      if (u_algorithm == 0) {
        vec3 target = toLinear(nvidiaTarget(source));
        return toSrgb(mix(reference, target, u_severity));
      }
      vec3 error = reference - simulateCvd(reference);
      vec3 shifted;
      if (u_mode == 3) {
        shifted = vec3(error.r + 0.7 * error.b, error.g + 0.7 * error.b, 0.0);
      } else {
        shifted = vec3(0.0, 0.7 * error.r + error.g, 0.7 * error.r + error.b);
      }
      vec3 corrected = reference + shifted;
      float sourceLuma = dot(reference, vec3(0.2126, 0.7152, 0.0722));
      float correctedLuma = dot(corrected, vec3(0.2126, 0.7152, 0.0722));
      float desiredLuma = mix(correctedLuma, sourceLuma, u_luminance);
      return toSrgb(fitGamut(corrected, desiredLuma));
    }
    void main() {
      vec4 original = texture2D(u_image, v_uv);
      vec3 color = v_uv.x < u_split ? original.rgb : filterColor(original.rgb);
      gl_FragColor = vec4(color, 1.0);
    }
  `;

  const program = gl.createProgram();
  gl.attachShader(program, compileShader(gl, gl.VERTEX_SHADER, vertexSource));
  gl.attachShader(program, compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource));
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    throw new Error(gl.getProgramInfoLog(program) || "Preview shader linking failed.");
  }
  gl.useProgram(program);

  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
  const position = gl.getAttribLocation(program, "a_position");
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

  const texture = gl.createTexture();
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);

  const nvidiaTexture = gl.createTexture();
  gl.activeTexture(gl.TEXTURE1);
  gl.bindTexture(gl.TEXTURE_2D, nvidiaTexture);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([0, 0, 0, 255]));
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, texture);

  const location = name => gl.getUniformLocation(program, name);
  const uniforms = {
    split: location("u_split"), mode: location("u_mode"), algorithm: location("u_algorithm"),
    severity: location("u_severity"), luminance: location("u_luminance"),
  };
  gl.uniform1i(location("u_image"), 0);
  gl.uniform1i(location("u_nvidia"), 1);
  const modeNumber = { off: 0, protan: 1, deutan: 2, tritan: 3 };
  const algorithmNumber = { nvidia: 0, classic: 1 };
  let imageReady = false;
  let imageGeneration = 0;
  let nvidiaMode = null;
  const nvidiaImages = new Map();
  const nvidiaPromises = new Map();
  const nvidiaUploadPending = new Set();

  function uploadNvidiaTexture(mode, image) {
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, nvidiaTexture);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, image);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, texture);
    nvidiaMode = mode;
  }

  function loadNvidiaImage(mode) {
    if (nvidiaImages.has(mode)) return Promise.resolve(nvidiaImages.get(mode));
    if (nvidiaPromises.has(mode)) return nvidiaPromises.get(mode);
    const promise = new Promise((resolve, reject) => {
      const transform = new Image();
      transform.fetchPriority = "high";
      transform.addEventListener("load", () => {
        nvidiaImages.set(mode, transform);
        nvidiaPromises.delete(mode);
        resolve(transform);
      }, { once: true });
      transform.addEventListener("error", () => {
        nvidiaPromises.delete(mode);
        reject(new Error("Could not load the NVIDIA reference transform."));
      }, { once: true });
      transform.src = mode === "protan" ? "assets/protanopia.png" : "assets/deuteranopia.png";
    });
    nvidiaPromises.set(mode, promise);
    return promise;
  }

  function ensureNvidiaTexture(mode) {
    if (mode !== "protan" && mode !== "deutan") return false;
    if (nvidiaMode === mode) return true;
    if (nvidiaImages.has(mode)) {
      uploadNvidiaTexture(mode, nvidiaImages.get(mode));
      return true;
    }
    if (!nvidiaUploadPending.has(mode)) {
      nvidiaUploadPending.add(mode);
      loadNvidiaImage(mode).then(image => {
        if (state.algorithm === "nvidia" && state.mode === mode) {
          uploadNvidiaTexture(mode, image);
          api.render();
        }
      }).catch(error => showStatus(error.message, "error")).finally(() => nvidiaUploadPending.delete(mode));
    }
    return false;
  }

  const api = {
    render() {
      if (!imageReady) return;
      const needsNvidia = state.algorithm === "nvidia" && state.mode !== "off";
      const nvidiaReady = !needsNvidia || ensureNvidiaTexture(state.mode);
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform1f(uniforms.split, split);
      gl.uniform1i(uniforms.mode, nvidiaReady ? modeNumber[state.mode] : 0);
      gl.uniform1i(uniforms.algorithm, algorithmNumber[state.algorithm]);
      gl.uniform1f(uniforms.severity, state.severity / 100);
      gl.uniform1f(uniforms.luminance, state.luminance / 100);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    },
    loadImage(url) {
      const generation = ++imageGeneration;
      imageReady = false;
      const image = new Image();
      image.addEventListener("load", () => {
        if (generation !== imageGeneration) return;
        canvas.width = image.naturalWidth;
        canvas.height = image.naturalHeight;
        document.getElementById("preview").style.aspectRatio = `${image.naturalWidth} / ${image.naturalHeight}`;
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
        imageReady = true;
        api.render();
      });
      image.addEventListener("error", () => {
        if (generation === imageGeneration) {
          showStatus("Could not load the selected preview image.", "error");
        }
      });
      image.fetchPriority = "high";
      image.src = url;
    },
    prefetchNvidia(mode) {
      if (mode !== "protan" && mode !== "deutan") return Promise.resolve();
      return loadNvidiaImage(mode).catch(error => showStatus(error.message, "error"));
    },
  };
  return api;
}

function buildPayload() {
  return {
    filter: {
      mode: state.mode,
      algorithm: state.algorithm,
      severity: state.severity / 100,
      luminance: state.luminance / 100,
      healthbars: state.healthbars,
    },
    outline: { thickness: state.thickness, color: state.outlineColor },
  };
}

function showStatus(message, type = "") {
  const status = document.getElementById("buildStatus");
  status.textContent = message;
  status.className = `status ${type}`.trim();
}

async function downloadVpk() {
  const button = document.getElementById("downloadButton");
  button.disabled = true;
  showStatus("Building VPK…");
  try {
    const payload = buildPayload();
    const packageBytes = await DeadlockBrowserBuilder.buildVpk({
      ...payload.filter,
      ...payload.outline,
      outlineColor: payload.outline.color,
    }, message => showStatus(message));
    const blob = new Blob([packageBytes], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "pak##_dir.vpk";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    showStatus(`Downloaded ${(blob.size / 1024 / 1024).toFixed(2)} MB VPK.`, "success");
  } catch (error) {
    showStatus(error.message || "VPK build failed.", "error");
  } finally {
    button.disabled = false;
  }
}

function selectPreviewImage(index) {
  if (previewImages.length === 0) return;
  previewImageIndex = (index + previewImages.length) % previewImages.length;
  document.querySelectorAll(".preview-thumbnail").forEach((thumbnail, thumbnailIndex) => {
    const active = thumbnailIndex === previewImageIndex;
    thumbnail.classList.toggle("active", active);
    thumbnail.setAttribute("aria-current", active ? "true" : "false");
  });
  const entry = previewImages[previewImageIndex];
  renderer?.loadImage(`demo/${encodeURIComponent(entry.id)}`);
}

async function initializeImages(priorityAssets) {
  const thumbnails = document.getElementById("previewThumbnails");
  const previous = document.getElementById("previousImage");
  const next = document.getElementById("nextImage");
  for (const button of [previous, next]) {
    button.addEventListener("pointerdown", event => event.stopPropagation());
  }
  previous.addEventListener("click", () => selectPreviewImage(previewImageIndex - 1));
  next.addEventListener("click", () => selectPreviewImage(previewImageIndex + 1));
  try {
    previewImages = [
      "demo_image.png",
      "demo_image6.png",
      "demo_image3.png",
      "demo_image4.png",
      "demo_image5.png",
      "demo_image2.png",
      "demo_image7.png",
    ].map((id, index) => ({ id, label: `Scene ${index + 1}` }));
    const thumbnailImages = [];
    thumbnails.replaceChildren(...previewImages.map((entry, index) => {
      const button = document.createElement("button");
      button.className = "preview-thumbnail";
      button.type = "button";
      button.setAttribute("aria-label", `Show ${entry.label}`);
      const image = document.createElement("img");
      image.dataset.src = `demo/${encodeURIComponent(entry.id)}`;
      if (index === 0) image.src = image.dataset.src;
      image.alt = "";
      image.draggable = false;
      image.fetchPriority = "low";
      thumbnailImages.push(image);
      button.appendChild(image);
      button.addEventListener("click", () => selectPreviewImage(index));
      return button;
    }));
    previous.disabled = previewImages.length < 2;
    next.disabled = previewImages.length < 2;
    selectPreviewImage(0);
    Promise.resolve(priorityAssets).finally(() => {
      for (const image of thumbnailImages) {
        if (!image.src) image.src = image.dataset.src;
      }
    });
  } catch (error) {
    previous.disabled = true;
    next.disabled = true;
    showStatus(`Preview images failed to load: ${error.message}`, "error");
  }
}

function initialize() {
  setupControls();
  setupDivider();
  applyState();
  let priorityAssets = Promise.resolve();
  try {
    renderer = createRenderer();
    if (state.algorithm === "nvidia") priorityAssets = renderer.prefetchNvidia(state.mode);
  } catch (error) {
    showStatus(error.message, "error");
  }
  initializeImages(priorityAssets);
}

initialize();
