# Verification

Run `python tools/check.py` in the development environment described in the README.
The same command runs before commits. It includes the following repeatable checks:

- Python QR matrices compared with a reference encoder and saved PNGs independently
  decoded at both ends of all 40 version ranges, plus Unicode and CLI error cases.
- Shared appearance presets, alpha channels, four-module margins, explicit PNG/SVG
  formats, output filenames, and overwrite protection.
- Browser SVGs rasterized with resvg and independently decoded with ZXing-C++ 2.3.0
  for ordinary, Unicode, and long URLs on the supported preview backgrounds.
- Python PNG/SVG exports independently decoded, and browser canvas geometry checked
  for integer module placement, opaque ink, transparency, and the complete margin.
- URL validation, capacity boundaries, readable rendering failures, and embedded
  assets. The build verifies the vendored library digest and generated-file freshness.
- Exact development versions, formatting, lint, types, ignored secret files, and
  secret scanning. The public vendor checksum is the only secret-scan allowlist.

## Initial browser checks — September 17, 2026

The generated HTML was tested in a Chromium-based browser through a local server,
at widths of 1280, 390, and 320 pixels. Checks covered:

- Empty, generated, edited-input, and invalid-URL states; no horizontal overflow.
- Keyboard form submission, disclosure toggling, radio selection, and visible focus.
- Four finishes and preview backgrounds. Clear on Charcoal shows a contrast warning.
- Editing the URL disables downloads until the image is updated.
- PNG and SVG download buttons saved files, which independently decoded to the
  exact expected URL. Browser-generated download contents for all four presets
  also preserved Unicode, percent escapes, query parameters, and fragments.
- Alpha values: Classic/Reverse fully opaque; Clear 0–255; Frost 224–255.
- A rebuilt HTML file reloaded with the default Classic appearance and empty input.

## Current HTML revision — September 17, 2026

The final interface has three visible finishes (Classic, Reverse, Clear), no
appearance disclosure, and one fixed reminder to test before sharing. Frost
remains a CLI option. Finish changes no longer display separate contrast warnings.
Desktop layout measurements place the bottom of Clear within 0.01 CSS pixels of
the SVG button bottom at 680px and 882px. The stacked 390px layout and keyboard
selection were inspected. The rebuilt file passes the complete project check.

## Limits

Direct local-file navigation was blocked by the browser testing tool, so double-click
launch was not browser-verified. The delivered file embeds scripts, styles, and
images and needs no runtime imports or external requests; local server use is only
for this test, not an end-user requirement.

The rendered stylesheet includes `prefers-reduced-motion: reduce` rules disabling
transitions and animations. The test browser offered no media-emulation control;
alternative browser controls timed out, so reduced-motion playback was not verified.
Normal transitions affect only color/shadow and are not required to use the page.

The software decoder successfully read inverted Reverse images. This does not prove
universal phone compatibility. No physical phone, print, glare, reflective metal,
or engraving tests were performed. Scan the final saved design on its real surface.
Clear on a dark surface is not accepted as a supported use, even if a permissive
software decoder can sometimes recover it.
