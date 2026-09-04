"use strict";

const fs = require("fs");
const path = require("path");
const { fileURLToPath, pathToFileURL } = require("url");

const root = path.resolve(__dirname, "..");
global.document = { baseURI: pathToFileURL(`${root}${path.sep}docs${path.sep}`).href };
global.fetch = async url => {
  try {
    const bytes = fs.readFileSync(fileURLToPath(url));
    return {
      ok: true,
      status: 200,
      arrayBuffer: async () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    };
  } catch {
    return { ok: false, status: 404 };
  }
};

require(path.join(root, "docs", "browser_builder.js"));

function hex(bytes) {
  return Buffer.from(bytes).toString("hex");
}

async function main() {
  const builder = global.DeadlockBrowserBuilder;
  if (hex(builder.md5(new TextEncoder().encode(""))) !== "d41d8cd98f00b204e9800998ecf8427e") {
    throw new Error("MD5 empty-vector mismatch");
  }
  if (hex(builder.md5(new TextEncoder().encode("abc"))) !== "900150983cd24fb0d6963f7d28e17f72") {
    throw new Error("MD5 abc-vector mismatch");
  }
  if (builder.crc32(new TextEncoder().encode("123456789")) !== 0xcbf43926) {
    throw new Error("CRC-32 vector mismatch");
  }
  const settings = process.argv[3] ? JSON.parse(process.argv[3]) : {
    mode: "deutan",
    algorithm: "classic",
    severity: 0.65,
    luminance: 0.7,
    healthbars: true,
    outlineColor: "#ffffb0",
  };
  if (process.argv[4]) {
    builder.loadNvidiaPixels(settings.mode, fs.readFileSync(process.argv[4]));
  }
  const output = await builder.buildVpk(settings);
  fs.writeFileSync(process.argv[2], output);
  process.stdout.write(`${output.length}\n`);
}

main().catch(error => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
