(() => {
  // Keep the error page in sync with the visitor's existing theme preference.
  addEventListener("storage", event => {
    if (event.key !== "getvout-theme") return;
    if (event.newValue === "dark") document.documentElement.dataset.theme = "dark";
    else delete document.documentElement.dataset.theme;
  });
})();
