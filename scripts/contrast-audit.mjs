// Contrast audit for the rendered-answer token palette. Run with:
//   node scripts/contrast-audit.mjs
// The browser-side equivalent should use getComputedStyle; this fixture keeps
// the audit deterministic in CI and covers every answer element type.
const themes = {
  light: { body: '#44403B', primary: '#0D0C0A', secondary: '#6B665F', accent: '#8A6500', surface: '#FFFFFF', alt: '#F0EFEB' },
  dark: { body: '#D8D1C7', primary: '#F3EFE8', secondary: '#B5ADA3', accent: '#F2C94C', surface: '#211F1C', alt: '#292622' },
};
const sample = [
  ['paragraph', 'body', 'surface'], ['heading', 'primary', 'surface'], ['strong', 'primary', 'surface'],
  ['italic', 'secondary', 'surface'], ['link', 'accent', 'surface'], ['blockquote', 'secondary', 'surface'],
  ['list', 'body', 'surface'], ['table', 'body', 'alt'], ['code', 'primary', 'alt'],
  ['confidence', 'primary', 'alt'], ['source list', 'accent', 'surface'],
];
function rgb(hex) { const n = Number.parseInt(hex.slice(1), 16); return [n >> 16 & 255, n >> 8 & 255, n & 255].map(v => v / 255); }
function lum(hex) { return rgb(hex).map(v => v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4).reduce((a, v, i) => a + v * [0.2126, 0.7152, 0.0722][i], 0); }
function ratio(fg, bg) { const a = lum(fg), b = lum(bg); return (Math.max(a, b) + .05) / (Math.min(a, b) + .05); }
let failed = false;
for (const [theme, t] of Object.entries(themes)) for (const [name, fg, bg] of sample) {
  const value = ratio(t[fg], t[bg]); const pass = value >= 4.5;
  console.log(`${theme}\t${name}\t${value.toFixed(2)}\t${pass ? 'PASS' : 'FAIL'}`);
  failed ||= !pass;
}
if (failed) process.exitCode = 1;
