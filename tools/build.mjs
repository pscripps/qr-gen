import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { build } from "esbuild";

export const root = new URL("../", import.meta.url);
const ENCODER_PATH = "vendor/qrcodegen-v1.8.0-es6.js";
const ENCODER_SHA =
  "6a1116192ed1dd67fa1bf31e77f5817103d71c23bbac24c382e698b7668bdd01"; // pragma: allowlist secret -- public release SHA-256
const CSS_FILES = ["base", "controls", "result", "responsive"];

export async function buildHtml() {
  const read = (path) => readFile(new URL(path, root), "utf8");
  const encoder = await read(ENCODER_PATH);
  if (createHash("sha256").update(encoder).digest("hex") !== ENCODER_SHA)
    throw new Error(
      "Bundled encoder does not match the pinned official release.",
    );
  const app = await build({
    entryPoints: [new URL("web/app.ts", root).pathname],
    bundle: true,
    format: "iife",
    target: "es2022",
    write: false,
    minify: false,
  });
  const css = (
    await Promise.all(CSS_FILES.map((name) => read(`web/${name}.css`)))
  ).join("\n");
  const template = await read("web/index.html");
  return template
    .replace("/* STYLES */", () => css)
    .replace("/* ENCODER */", () => encoder)
    .replace("/* APP */", () => app.outputFiles[0].text);
}

if (process.argv[1] === new URL(import.meta.url).pathname)
  await writeFile(new URL("QR-generator.html", root), await buildHtml());
