import { readFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { buildHtml, root } from "./build.mjs";

const manifest = JSON.parse(await readFile(new URL("package.json", root)));
const run = (command, args) =>
  execFileSync(command, args, { cwd: root, stdio: "inherit" });
if (process.versions.node !== manifest.engines.node)
  throw new Error(`Use Node ${manifest.engines.node}.`);
const npmVersion = execFileSync("npm", ["--version"], {
  encoding: "utf8",
}).trim();
if (npmVersion !== manifest.engines.npm)
  throw new Error(`Use npm ${manifest.engines.npm}.`);
for (const [name, version] of Object.entries(manifest.devDependencies)) {
  const installed = JSON.parse(
    await readFile(new URL(`node_modules/${name}/package.json`, root)),
  );
  if (installed.version !== version)
    throw new Error(`Install pinned ${name}@${version}.`);
}
run("node_modules/.bin/tsc", ["--noEmit"]);
run("node_modules/.bin/eslint", ["web", "tools/*.mjs", "tests/web"]);
run("node_modules/.bin/prettier", [
  "--check",
  "web",
  "tools/*.mjs",
  "tests/web",
  "*.json",
  "eslint.config.mjs",
]);
if (
  (await readFile(new URL("QR-generator.html", root), "utf8")) !==
  (await buildHtml())
)
  throw new Error("QR-generator.html is stale. Run npm run build.");
run("node", ["--test", "tests/web/*.test.mjs"]);
