import { OPAQUE, settingsValidated as settings, type Preset } from "./config";

export type Matrix = boolean[][];
const MIN_VERSION = 1;
const MAX_VERSION = 40;
const AUTO_MASK = -1;

export function encode(text: string): Matrix {
  const bytes = new TextEncoder().encode(text);
  if (!bytes.length) throw new Error("Paste a URL first.");
  if (bytes.length > settings.maxBytes)
    throw new Error(
      "This link is too long for one QR code. Try a shorter URL.",
    );
  // Explicit byte mode preserves UTF-8 bytes, including spaces and Unicode.
  const qr = qrcodegen.QrCode.encodeSegments(
    [qrcodegen.QrSegment.makeBytes(Array.from(bytes))],
    qrcodegen.QrCode.Ecc.LOW,
    MIN_VERSION,
    MAX_VERSION,
    AUTO_MASK,
    false,
  );
  return Array.from({ length: qr.size }, (_, row) =>
    Array.from({ length: qr.size }, (_, col) => qr.getModule(col, row)),
  );
}

export function svgText(matrix: Matrix, preset: Preset): string {
  const dimension = matrix.length + settings.quietZone * 2;
  const pixels = dimension * settings.scale;
  const path = matrix
    .flatMap((row, y) =>
      row.flatMap((dark, x) =>
        dark
          ? [`M${x + settings.quietZone},${y + settings.quietZone}h1v1h-1z`]
          : [],
      ),
    )
    .join(" ");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${pixels}" height="${pixels}" viewBox="0 0 ${dimension} ${dimension}" shape-rendering="crispEdges"><rect width="100%" height="100%" fill="${preset.paper}" fill-opacity="${preset.paperAlpha / OPAQUE}"/><path fill="${preset.ink}" d="${path}"/></svg>`;
}

export function paintCanvas(
  canvas: HTMLCanvasElement,
  matrix: Matrix,
  preset: Preset,
): void {
  const dimension = (matrix.length + settings.quietZone * 2) * settings.scale;
  canvas.width = canvas.height = dimension;
  const context = canvas.getContext("2d");
  if (!context)
    throw new Error(
      "Your browser could not draw the image. Try another browser.",
    );
  context.fillStyle = preset.paper;
  context.globalAlpha = preset.paperAlpha / OPAQUE;
  context.fillRect(0, 0, dimension, dimension);
  context.globalAlpha = 1;
  context.fillStyle = preset.ink;
  matrix.forEach((row, y) =>
    row.forEach((dark, x) => {
      if (dark)
        context.fillRect(
          (x + settings.quietZone) * settings.scale,
          (y + settings.quietZone) * settings.scale,
          settings.scale,
          settings.scale,
        );
    }),
  );
}
