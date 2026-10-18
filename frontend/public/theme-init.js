// Runs before first paint (loaded synchronously from index.html; inline scripts are blocked by the CSP),
// so a reload in Graphite never flashes the light canvas.
try {
  if (localStorage.getItem("bluewatch.theme") === "graphite") {
    document.documentElement.dataset.theme = "graphite";
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", "#0F1012");
  }
} catch {
  // Storage blocked (private windows): light.
}
