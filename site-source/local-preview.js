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

// Do not invoke the production Server Action or send/store contact information.
// Preserve the original form until the user tries it, then clearly disclose
// the preview-only outcome instead of claiming a message was delivered.
document.addEventListener("submit", function (event) {
  if (!["/en/contact", "/en/start-project"].includes(location.pathname.replace(/\/$/, ""))) return;
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  event.preventDefault();
  event.stopImmediatePropagation();
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
  status.textContent = "Local preview only \u2014 your " + kind + " was not sent or stored. Email hello@getvout.com to reach our team.";
}, true);
