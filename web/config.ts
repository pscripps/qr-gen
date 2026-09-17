import settings from "../appearances.json";

export type Preset = (typeof settings.presets)[number];
export type Surface = (typeof settings.surfaces)[number];
export const OPAQUE = 255;
export const settingsValidated = (() => {
  const ids = new Set<string>();
  for (const preset of settings.presets) {
    if (
      ids.has(preset.id) ||
      !/^#[0-9a-f]{6}$/i.test(preset.ink) ||
      !/^#[0-9a-f]{6}$/i.test(preset.paper) ||
      preset.paperAlpha < 0 ||
      preset.paperAlpha > OPAQUE
    )
      throw new Error("Invalid appearance settings.");
    ids.add(preset.id);
  }
  if (
    !ids.has(settings.defaultPreset) ||
    settings.quietZone < 4 ||
    settings.scale < 1
  )
    throw new Error("Invalid default QR settings.");
  return settings;
})();

// Frost remains available to existing CLI users, but duplicates Classic visually.
export const websitePresets = settingsValidated.presets.filter(
  (preset) => preset.id !== "frost",
);
