import { normalizeUrl } from "./url";
import {
  settingsValidated as settings,
  type Preset,
  websitePresets,
} from "./config";
import { encode, paintCanvas, svgText, type Matrix } from "./render";

const SAMPLE_URL = "https://example.com";

function element<T extends HTMLElement>(id: string): T {
  const found = document.getElementById(id);
  if (!found) throw new Error(`Missing page element: ${id}`);
  return found as T;
}

const input = element<HTMLInputElement>("url");
const canvas = element<HTMLCanvasElement>("preview");
const error = element("error");
const status = element("status");
const payload = element("payload");
const stage = element("stage");
const png = element<HTMLAnchorElement>("png");
const svg = element<HTMLAnchorElement>("svg");
let preset: Preset = websitePresets.find(
  (item) => item.id === settings.defaultPreset,
)!;
let matrix: Matrix | null = null;
let encodedPayload = "";

function disableDownloads(): void {
  for (const link of [png, svg]) {
    link.removeAttribute("href");
    link.removeAttribute("download");
    link.setAttribute("aria-disabled", "true");
  }
}

function showError(message: string): void {
  error.textContent = message;
  error.hidden = false;
  disableDownloads();
}

function renderResult(): void {
  if (!matrix) return;
  try {
    paintCanvas(canvas, matrix, preset);
    canvas.hidden = false;
    element("empty").hidden = true;
    payload.hidden = false;
    payload.textContent = encodedPayload;
    element("image-size").textContent = `${canvas.width} × ${canvas.height} px`;
    // Static data URLs avoid network access and object-URL lifetime races.
    png.href = canvas.toDataURL("image/png");
    svg.href = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgText(matrix, preset))}`;
    for (const [link, extension] of [
      [png, "png"],
      [svg, "svg"],
    ] as const) {
      link.download = `qrcode-${preset.id}.${extension}`;
      link.removeAttribute("aria-disabled");
    }
    if (input.value !== encodedPayload) {
      disableDownloads();
      status.textContent = "Address changed. Transform to update.";
    } else {
      status.textContent = "";
    }
    refreshMiniatures(matrix);
  } catch (caught) {
    showError(
      caught instanceof Error
        ? caught.message
        : "Could not prepare your image.",
    );
    status.textContent = "Image not ready. Try Transform again.";
  }
}

function refreshMiniatures(pattern: Matrix): void {
  for (const item of websitePresets) {
    const image = element<HTMLImageElement>(`sample-${item.id}`);
    image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgText(pattern, item))}`;
  }
}

function setUpAppearance(): void {
  const choices = element("presets");
  for (const item of websitePresets) {
    const label = document.createElement("label");
    label.className = "preset";
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "finish";
    radio.value = item.id;
    radio.checked = item.id === preset.id;
    const image = document.createElement("img");
    image.id = `sample-${item.id}`;
    image.alt = "";
    const words = document.createElement("span");
    const name = document.createElement("strong");
    name.textContent = item.name;
    words.append(name);
    label.append(radio, image, words);
    choices.append(label);
    radio.addEventListener("change", () => {
      preset = item;
      renderResult();
    });
  }
  const select = element<HTMLSelectElement>("surface");
  for (const surface of settings.surfaces)
    select.add(new Option(surface.name, surface.id));
  select.value = settings.defaultSurface;
  const updateSurface = () => {
    const surface = settings.surfaces.find((item) => item.id === select.value)!;
    stage.style.background = surface.background;
  };
  select.addEventListener("change", updateSurface);
  updateSurface();
  refreshMiniatures(encode(SAMPLE_URL));
}

element<HTMLFormElement>("form").addEventListener("submit", (event) => {
  event.preventDefault();
  error.hidden = true;
  input.removeAttribute("aria-invalid");
  try {
    const completeUrl = normalizeUrl(input.value);
    matrix = encode(completeUrl);
    input.value = completeUrl;
    encodedPayload = completeUrl;
    renderResult();
  } catch (caught) {
    input.setAttribute("aria-invalid", "true");
    showError(
      caught instanceof Error
        ? caught.message
        : "Could not make this QR image.",
    );
    status.textContent = "Check your URL and try again.";
    input.focus();
  }
});
input.addEventListener("input", () => {
  error.hidden = true;
  input.removeAttribute("aria-invalid");
  disableDownloads();
  status.textContent = matrix ? "Address changed. Transform to update." : "";
});
setUpAppearance();
