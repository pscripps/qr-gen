import assert from "node:assert/strict";
import { readFile, mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import vm from "node:vm";
import { execFileSync } from "node:child_process";
import { test } from "node:test";
import { build } from "esbuild";
import { Resvg } from "@resvg/resvg-js";

const root = new URL("../../", import.meta.url);
const settings = JSON.parse(await readFile(new URL("appearances.json", root)));
const library = await readFile(
  new URL("vendor/qrcodegen-v1.8.0-es6.js", root),
  "utf8",
);
const bundled = await build({
  entryPoints: [new URL("web/render.ts", root).pathname],
  bundle: true,
  format: "iife",
  globalName: "renderer",
  write: false,
});
const context = vm.createContext({ TextEncoder });
vm.runInContext(library + bundled.outputFiles[0].text, context);
const { encode, svgText, paintCanvas } = context.renderer;

// Recording canvas proves exact integer module geometry and alpha-state restoration.
test("canvas preserves every module and the four-module border", () => {
  const matrix = encode("https://example.com");
  for (const preset of settings.presets) {
    const calls = [];
    const drawing = {
      fillRect(...rect) {
        calls.push({ rect, color: this.fillStyle, alpha: this.globalAlpha });
      },
    };
    const canvas = { getContext: () => drawing };
    paintCanvas(canvas, matrix, preset);
    assert.equal(canvas.width, (matrix.length + 8) * 10);
    assert.equal(calls[0].alpha, preset.paperAlpha / 255);
    assert.equal(calls.length - 1, matrix.flat().filter(Boolean).length);
    for (const call of calls.slice(1)) {
      assert.equal(call.alpha, 1);
      assert.ok(call.rect[0] >= 40 && call.rect[1] >= 40);
      assert.ok(
        call.rect[0] < canvas.width - 40 && call.rect[1] < canvas.width - 40,
      );
      assert.deepEqual(call.rect.slice(2), [10, 10]);
    }
  }
});

test("input boundaries and canvas failure are explicit", () => {
  assert.throws(() => encode(""), /Paste/);
  assert.throws(() => encode("a".repeat(2954)), /too long/);
  assert.equal(encode("a".repeat(2953)).length, 177);
  assert.throws(
    () =>
      paintCanvas(
        { getContext: () => null },
        encode("hello"),
        settings.presets[0],
      ),
    /could not draw/,
  );
});

test("independently decode actual SVGs after compositing, including inverted output", async () => {
  const directory = await mkdtemp(path.join(tmpdir(), "qr-web-"));
  try {
    const records = [];
    const payloads = [
      "https://example.com",
      "https://example.com/café/東京?emoji=😀&literal=%20#part",
      "https://example.com/" + "x".repeat(480),
    ];
    for (const [index, payload] of payloads.entries()) {
      for (const preset of settings.presets) {
        const text = svgText(encode(payload), preset);
        const svgPath = path.join(directory, `${index}-${preset.id}.svg`);
        await writeFile(svgPath, text);
        for (const surface of settings.surfaces) {
          const pngPath = `${svgPath}-${surface.id}.png`;
          await writeFile(
            pngPath,
            new Resvg(text, { background: surface.color }).render().asPng(),
          );
          records.push({
            path: pngPath,
            payload,
            preset: preset.id,
            surface: surface.id,
          });
        }
      }
    }
    const manifest = path.join(directory, "records.json");
    await writeFile(manifest, JSON.stringify(records));
    execFileSync(
      new URL(".venv/bin/python", root).pathname,
      [new URL("tests/decode_exports.py", root).pathname, manifest],
      { stdio: "inherit" },
    );
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test("deliverable embeds all assets and blocks online connections", async () => {
  const html = await readFile(new URL("QR-generator.html", root), "utf8");
  assert.match(html, /connect-src 'none'/);
  assert.doesNotMatch(html, /<(?:script|link)[^>]+(?:src|href)=/);
  assert.match(html, /prefers-reduced-motion/);
  assert.match(html, /Copyright \(c\) Project Nayuki/);
});

test("URL normalization supplies HTTPS while preserving complete web URLs", async () => {
  const urlModule = await build({
    entryPoints: [new URL("web/url.ts", root).pathname],
    bundle: true,
    format: "iife",
    globalName: "urls",
    write: false,
  });
  const scope = vm.createContext({ URL });
  vm.runInContext(urlModule.outputFiles[0].text, scope);
  for (const value of [
    "https://example.com/café/東京?x=%20&y=😀",
    "HTTP://example.com/#literal",
  ])
    assert.doesNotThrow(() => scope.urls.normalizeUrl(value));
  for (const [input, expected] of [
    ["google.com", "https://google.com"],
    [
      "example.com/café/東京?x=%20&y=😀#part",
      "https://example.com/café/東京?x=%20&y=😀#part",
    ],
    ["  google.com  ", "https://google.com"],
    ["//example.com/path", "https://example.com/path"],
    ["example.com:8080/path", "https://example.com:8080/path"],
    ["http://example.com/path", "http://example.com/path"],
    ["HTTPS://example.com/%2f?x=%20", "HTTPS://example.com/%2f?x=%20"],
  ])
    assert.equal(scope.urls.normalizeUrl(input), expected);
  for (const value of [
    "",
    "https://example.com/a b",
    "javascript:alert(1)",
    "file:///tmp/x",
  ])
    assert.throws(() => scope.urls.normalizeUrl(value));
});

test("Python SVG exports independently decode with the same presets", async () => {
  const directory = await mkdtemp(path.join(tmpdir(), "qr-python-svg-"));
  try {
    const records = [];
    const payload = "https://example.com/café/東京?x=%20&y=😀";
    for (const preset of settings.presets) {
      const svgPath = path.join(directory, `${preset.id}.svg`);
      execFileSync(
        new URL(".venv/bin/python", root).pathname,
        [
          new URL("qr_gen.py", root).pathname,
          payload,
          svgPath,
          "--format",
          "svg",
          "--preset",
          preset.id,
        ],
        { stdio: "pipe" },
      );
      const pngPath = `${svgPath}.png`;
      await writeFile(
        pngPath,
        new Resvg(await readFile(svgPath), { background: "#c9ced1" })
          .render()
          .asPng(),
      );
      records.push({
        path: pngPath,
        payload,
        preset: preset.id,
        surface: "silver",
      });
    }
    const manifest = path.join(directory, "records.json");
    await writeFile(manifest, JSON.stringify(records));
    execFileSync(
      new URL(".venv/bin/python", root).pathname,
      [new URL("tests/decode_exports.py", root).pathname, manifest],
      { stdio: "inherit" },
    );
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test("website offers three distinct finishes and omits removed labels", async () => {
  const output = await build({
    entryPoints: [new URL("web/config.ts", root).pathname],
    bundle: true,
    format: "iife",
    globalName: "config",
    write: false,
  });
  const scope = vm.createContext({});
  vm.runInContext(output.outputFiles[0].text, scope);
  assert.equal(
    scope.config.websitePresets.map((preset) => preset.id).join(","),
    "classic,reverse,clear",
  );
  assert.ok(settings.presets.some((preset) => preset.id === "frost"));
  const html = await readFile(new URL("web/index.html", root), "utf8");
  assert.doesNotMatch(
    html,
    /Works offline|Not included in download|surface-hint/,
  );
});

test("one fixed reminder replaces finish-specific caveats", async () => {
  const html = await readFile(new URL("web/index.html", root), "utf8");
  assert.equal(
    (html.match(/Test your code and color combination before sharing\./g) || [])
      .length,
    1,
  );
  assert.doesNotMatch(html, /id="compatibility"/);
  const app = await readFile(new URL("web/app.ts", root), "utf8");
  assert.doesNotMatch(app, /updateCompatibility|compatibilityNote/);
});
