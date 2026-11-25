// Evaluated by the existing CDP harness on the local preview, without Google.
(async () => {
  const source = await (await fetch("/analytics-consent.js")).text();
  const originalFetch = window.fetch;
  window.fetch = async (url, ...args) => url === "/api/analytics-policy" ?
    {ok: true, json: async () => ({active: true, consentRequired: true})} : originalFetch(url, ...args);
  const originalAppend = document.head.appendChild.bind(document.head);
  const googleScripts = [];
  document.head.appendChild = node => {
    if (node.src?.includes("googletagmanager.com")) { googleScripts.push(node.src); return node; }
    return originalAppend(node);
  };
  localStorage.removeItem("getvout-analytics-v1");
  // Only bypass the production host guard in this test; real loader stays strict.
  (0, eval)(source.replace('location.protocol !== "https:"', 'false')
    .replace('!["getvout.com", "www.getvout.com"].includes(location.hostname)', 'false'));
  await new Promise(resolve => setTimeout(resolve, 200));
  const panel = document.querySelector("#gv-consent");
  if (!panel || panel.hidden || googleScripts.length) throw Error("Consent gate failed");
  const box = panel.getBoundingClientRect();
  if (box.left < 0 || box.right > innerWidth || box.bottom > innerHeight) throw Error("Consent overflow");
  panel.querySelector('[data-choice="declined"]').click();
  if (!panel.hidden || googleScripts.length) throw Error("Decline loaded Google");
  document.querySelector("#gv-analytics-settings").click();
  panel.querySelector('[data-choice="accepted"]').click();
  if (googleScripts.length !== 1) throw Error("Accept did not load exactly once");
  // Leave panel visible for screenshot review.
  document.querySelector("#gv-analytics-settings").click();
  return {viewport: innerWidth, consentGate: true, decline: true, accept: true,
    googleLoaderCount: googleScripts.length, pageviews: window.dataLayer.filter(x => x[0] === "event").length,
    preferencesInFooter: !!document.querySelector("footer #gv-analytics-settings"),
    overflow: document.documentElement.scrollWidth > innerWidth};
})()
