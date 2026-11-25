// Mirrored routes retain the original client-side transition/navigation.
// Other routes still open the live site until they are added locally.
document.addEventListener("click", function (event) {
  const link = event.target.closest("a[href]");
  if (!link || event.defaultPrevented || event.button !== 0 ||
      event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const url = new URL(link.href, location.href);
  // The snapshot router can reuse a previously prefetched empty brief.
  // Load module-specific briefs directly to preserve the chosen add-ons.
  if (url.origin === location.origin && url.pathname === "/en/start-project" &&
      url.searchParams.has("modules")) {
    event.preventDefault();
    event.stopImmediatePropagation();
    location.assign(url.href);
    return;
  }
  const articles = [
    "dropdown-defaults-accessible-forms", "safer-confirmation-ux", "accessible-cta-button-design",
    "website-walkthrough-video", "template-vs-custom-website",
    "inp-animation-responsive-websites", "technical-seo-aeo-useful-content",
    "dropdown-defaults-accessible-forms", "safer-confirmation-ux", "accessible-cta-button-design",
    "website-walkthrough-video", "template-vs-custom-website", "inp-animation-responsive-websites", "technical-seo-aeo-useful-content",
  ];
  const services = [
    "websites", "custom-software-apps", "brand-logo", "ai-assistants",
    "workflow-automation", "hosting-domains-email", "online-shops",
    "workflow-automation",
  ];
  if (services.some(slug => url.pathname.replace(/\/$/, "") === "/en/services/" + slug)) return;
  if (articles.some(slug => url.pathname.replace(/\/$/, "") === "/en/journal/" + slug)) return;
  if (["/en", "/en/work", "/en/services", "/en/studio", "/en/journal", "/en/contact", "/en/start-project", "/en/privacy", "/en/imprint"].includes(url.pathname.replace(/\/$/, ""))) return;
  if (url.origin === location.origin && /^\/(?:en\/.+|(?:services|work|journal|contact|studio|start-project)(?:\/|$))/.test(url.pathname)) {
    event.preventDefault();
    event.stopImmediatePropagation();
    location.href = "https://getvout.com/" + url.pathname + url.search + url.hash;
  }
}, true);

// The compiled Server Actions belong to the original build, not this backend.
// Intercept before React and submit only to our same-origin production endpoint.
const enquiryProduction = location.protocol === "https:" &&
  ["getvout.com", "www.getvout.com"].includes(location.hostname);
const enquiryStates = new WeakMap();
let enquiryToken;
let enquiryTokenTime = 0;
function enquiryRequestTimeout(ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, clear: () => clearTimeout(timer) };
}
function enquiryReference() {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, "0")).join("");
  return hex.slice(0, 8) + "-" + hex.slice(8, 12) + "-" + hex.slice(12, 16) + "-" + hex.slice(16, 20) + "-" + hex.slice(20);
}
async function loadEnquiryToken() {
  if (!enquiryToken || Date.now() - enquiryTokenTime > 7000000) {
    const request = enquiryRequestTimeout(15000);
    enquiryToken = fetch("/api/enquiry", { credentials: "same-origin", cache: "no-store", signal: request.signal })
      .then(async response => {
        let result = {};
        try { result = await response.json(); } catch (error) { result = {}; }
        if (!response.ok || !result.token) throw new Error(result.message || "Email delivery is temporarily unavailable. Please email hello@getvout.com directly.");
        enquiryTokenTime = Date.now();
        return result.token;
      }).finally(request.clear)
      .catch(error => { enquiryToken = undefined; throw error; });
  }
  return enquiryToken;
}
// Only fetch the bootstrap token when a visitor interacts with a form.
document.addEventListener("focusin", event => {
  if (enquiryProduction && event.target.closest("form") &&
      ["/en/contact", "/en/start-project"].includes(location.pathname.replace(/\/$/, ""))) {
    loadEnquiryToken().catch(() => {});
  }
});
document.addEventListener("input", event => {
  const form = event.target.closest("form");
  if (!form || !form.dataset.enquirySent) return;
  delete form.dataset.enquirySent;
  enquiryStates.delete(form);
  const button = form.querySelector('button[type="submit"]');
  if (button) {
    button.disabled = false;
    button.textContent = form.dataset.enquiryButtonLabel || "Send enquiry";
  }
});
document.addEventListener("submit", async function (event) {
  if (!["/en/contact", "/en/start-project"].includes(location.pathname.replace(/\/$/, ""))) return;
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  if (form.dataset.enquirySending || form.dataset.enquirySent) return;
  if (!form.reportValidity()) return;
  let status = form.querySelector("[data-local-contact-status]");
  if (!status) {
    status = document.createElement("p");
    status.dataset.localContactStatus = "";
    status.className = "text-sm text-steel";
    status.setAttribute("role", "status");
    form.appendChild(status);
  }
  const kind = location.pathname.includes("start-project") ? "brief" : "message";
  if (!enquiryProduction) {
    status.textContent = "Local preview only \u2014 your " + kind + " was not sent or stored. Email hello@getvout.com to reach our team.";
    return;
  }
  const fields = new FormData(form);
  const value = name => String(fields.get(name) || "");
  const payload = {
    kind: kind === "brief" ? "project" : "contact",
    name: value("name"), email: value("email"), phone: value("phone"),
    company: value("company"), existingSite: value("existingSite"),
    message: value("message"), website: value("website"),
    projectType: fields.getAll("projectType").map(String),
    budget: value("budget"), timeline: value("timeline"),
    modules: kind === "brief" ? (new URLSearchParams(location.search).get("modules") || "").split(",").filter(Boolean) : [],
  };
  const snapshot = JSON.stringify(payload);
  let state = enquiryStates.get(form);
  if (!state || state.snapshot !== snapshot) {
    state = { snapshot, submissionId: enquiryReference(), submittedAt: new Date().toISOString() };
    enquiryStates.set(form, state);
  }
  payload.submissionId = state.submissionId;
  payload.submittedAt = state.submittedAt;
  const button = form.querySelector('button[type="submit"]');
  if (button) {
    form.dataset.enquiryButtonLabel ||= button.textContent;
    button.disabled = true;
    button.textContent = "Submitting\u2026";
  }
  form.dataset.enquirySending = "true";
  form.setAttribute("aria-busy", "true");
  status.textContent = "Submitting your " + kind + "\u2026";
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25000);
  try {
    payload.token = await loadEnquiryToken();
    // Token age is checked server-side; allow ordinary autofill to work too.
    const wait = Math.max(0, 1300 - (Date.now() - enquiryTokenTime));
    if (wait) await new Promise(resolve => setTimeout(resolve, wait));
    const response = await fetch("/api/enquiry", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload), signal: controller.signal,
    });
    let result = {};
    try { result = await response.json(); } catch (error) { result = {}; }
    if (!response.ok || result.ok !== true) {
      if (response.status === 400) enquiryToken = undefined;
      throw new Error(result.message || "We could not confirm your enquiry. Please try again or email hello@getvout.com. Your details have not been cleared.");
    }
    form.dataset.enquirySent = "true";
    status.textContent = result.message;
    if (button) button.textContent = "Enquiry submitted";
  } catch (error) {
    status.textContent = ["AbortError", "TimeoutError"].includes(error.name) ?
      "We could not confirm your enquiry in time. Please retry once or email hello@getvout.com. Your details have not been cleared." :
      (error.name === "Error" && error.message ? error.message :
        "We could not reach the server. Please retry once or email hello@getvout.com. Your details have not been cleared.");
  } finally {
    clearTimeout(timeout);
    delete form.dataset.enquirySending;
    form.removeAttribute("aria-busy");
    if (button && !form.dataset.enquirySent) {
      button.disabled = false;
      button.textContent = form.dataset.enquiryButtonLabel;
    }
  }
}, true);
