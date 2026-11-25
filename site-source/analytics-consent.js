/* Basic consent mode: no Google requests before consent where required. */
(() => {
  "use strict";
  if (window.__getvoutGA4 || location.protocol !== "https:" ||
      !["getvout.com", "www.getvout.com"].includes(location.hostname)) return;
  window.__getvoutGA4 = true;
  const ID = "G-PZ5DTH5MCX", KEY = "getvout-analytics-v1", MAX_AGE = 180 * 86400000;
  let started = false, allowed = false, lastPath = "", panel, settings;
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window["ga-disable-" + ID] = true;
  gtag("consent", "default", {analytics_storage: "denied", ad_storage: "denied",
    ad_user_data: "denied", ad_personalization: "denied"});
  function saved() {
    try {
      const value = JSON.parse(localStorage.getItem(KEY));
      return value && ["accepted", "declined"].includes(value.choice) &&
        Date.now() >= value.at && Date.now() - value.at < MAX_AGE ? value.choice : null;
    } catch (_) { return null; }
  }
  function pageview() {
    if (!allowed || lastPath === location.pathname) return;
    // Only known public routes, never form data, URL queries or fragment values.
    const path = location.pathname.replace(/\/$/, "") || "/en";
    if (!/^\/en(?:\/(?:work|services|studio|journal|contact|start-project|privacy|imprint)(?:\/[a-z-]+)?)?$/.test(path)) return;
    lastPath = location.pathname;
    gtag("event", "page_view", {page_location: location.origin + path,
      page_referrer: "", page_title: "getvout"});
  }
  function enable() {
    allowed = true;
    window["ga-disable-" + ID] = false;
    gtag("consent", "update", {analytics_storage: "granted"});
    if (!started) {
      started = true;
      gtag("js", new Date());
      gtag("config", ID, {send_page_view: false, allow_google_signals: false,
        allow_ad_personalization_signals: false, page_location: location.origin + location.pathname,
        page_referrer: "", cookie_expires: 15552000});
      const script = document.createElement("script");
      script.async = true;
      script.src = "https://www.googletagmanager.com/gtag/js?id=" + ID;
      document.head.appendChild(script);
    }
    pageview();
  }
  function disable() {
    allowed = false;
    window["ga-disable-" + ID] = true;
    // Do not send a consent ping on withdrawal. Reload removes Google's listeners.
    for (const cookie of document.cookie.split(";")) {
      const name = cookie.split("=")[0].trim();
      if (!/^_ga(?:_|$)|^_gid$|^_gat/.test(name)) continue;
      for (const domain of ["", "; Domain=getvout.com", "; Domain=.getvout.com", "; Domain=" + location.hostname]) {
        document.cookie = name + "=; Max-Age=0; Path=/" + domain + "; SameSite=Lax; Secure";
      }
    }
  }
  function choose(choice) {
    try { localStorage.setItem(KEY, JSON.stringify({choice, at: Date.now()})); } catch (_) {}
    panel.hidden = true;
    settings.focus();
    if (choice === "accepted") enable();
    else {
      disable();
      if (started) location.reload();
    }
  }
  function ui(required) {
    const style = document.createElement("style");
    style.textContent = `
      #gv-consent{position:fixed;bottom:24px;left:var(--shell,20px);z-index:10000;width:min(440px,calc(100vw - 40px));box-sizing:border-box;padding:22px;background:var(--paper,#f4f4f2);color:var(--ink,#121214);border:1px solid var(--line,#ccc);box-shadow:0 8px 36px #0002;font-family:var(--nf-text),sans-serif}
      #gv-consent[hidden]{display:none}
      #gv-consent h2{font-size:19px;line-height:1.3;margin:0 0 10px;font-weight:600}
      #gv-consent p{font-size:14px;line-height:1.6;margin:0 0 16px}
      #gv-consent a{color:inherit;text-decoration:underline}
      #gv-consent .gv-actions{display:flex;gap:10px}
      #gv-consent button{flex:1;background:var(--paper,#f4f4f2);color:var(--ink,#121214);border:1px solid var(--ink,#121214);padding:11px 12px;font:inherit;font-size:14px;cursor:pointer}
      #gv-consent button:focus-visible,#gv-analytics-settings:focus-visible{outline:3px solid var(--accent,#ff3e3e);outline-offset:3px}
      #gv-analytics-settings{display:block;margin:16px 0;background:transparent;color:inherit;border:0;text-decoration:underline;font:inherit;font-size:12px;cursor:pointer}
      @media(max-width:480px){#gv-consent{bottom:14px;left:20px;padding:18px}}
    `;
    document.head.appendChild(style);
    panel = document.createElement("section");
    panel.id = "gv-consent";
    panel.setAttribute("role", "region");
    panel.setAttribute("aria-labelledby", "gv-consent-title");
    panel.innerHTML = '<h2 id="gv-consent-title">Your analytics choice</h2><p>We use Google Analytics cookies to understand visits and improve our website. You can decline and still use everything. <a href="/en/privacy">Privacy policy</a></p><div class="gv-actions"><button type="button" data-choice="declined">Decline analytics</button><button type="button" data-choice="accepted">Accept analytics</button></div>';
    panel.hidden = !required;
    panel.addEventListener("click", event => {
      const choice = event.target.closest("[data-choice]")?.dataset.choice;
      if (choice) choose(choice);
    });
    document.body.appendChild(panel);
    settings = document.createElement("button");
    settings.id = "gv-analytics-settings";
    settings.type = "button";
    settings.textContent = "Analytics preferences";
    settings.onclick = () => {
      panel.hidden = false;
      panel.querySelector("button").focus();
    };
    // Footer can be replaced by client navigation; preserve access to preferences.
    function attachSettings() {
      const footer = document.querySelector("footer");
      if (footer && !settings.isConnected) footer.appendChild(settings);
    }
    attachSettings();
    new MutationObserver(attachSettings).observe(document.body, {childList: true, subtree: true});
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && !panel.hidden && saved()) {
        panel.hidden = true;
        settings.focus();
      }
    });
  }
  async function init() {
    // Next creates its route announcer in a post-hydration React effect.
    // Appending UI before that can invalidate the server-rendered document.
    if (!document.querySelector("next-route-announcer")) {
      await new Promise(resolve => {
        const observer = new MutationObserver(() => {
          if (document.querySelector("next-route-announcer")) {
            observer.disconnect();
            resolve();
          }
        });
        observer.observe(document.body, {childList: true, subtree: true});
      });
    }
    let policy;
    try {
      const response = await fetch("/api/analytics-policy", {cache: "no-store", credentials: "same-origin"});
      if (!response.ok) throw new Error("policy");
      policy = await response.json();
    } catch (_) { policy = {active: true, consentRequired: true}; }
    if (policy.active !== true) return;
    const choice = saved();
    ui(policy.consentRequired !== false && !choice);
    if (choice === "accepted" || (!choice && policy.consentRequired === false)) enable();
    // Google enhanced history tracking must be disabled in the stream settings.
    for (const name of ["pushState", "replaceState"]) {
      const original = history[name];
      history[name] = function (...args) {
        const result = original.apply(this, args);
        pageview();
        return result;
      };
    }
    window.addEventListener("popstate", pageview);
    window.addEventListener("storage", event => {
      if (event.key === KEY) location.reload();
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, {once: true});
  else init();
})();
