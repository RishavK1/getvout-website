// Built-in Node VM only; never loads or executes Google's hosted code.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("site-source/analytics-consent.js", "utf8");
async function run({countryConsent = true, choice = null, host = "getvout.com", active = true, fail = false} = {}) {
  const nodes = [], events = {}, appended = [];
  const el = () => ({hidden: false, dataset: {}, setAttribute() {}, addEventListener(n, fn) { this[n] = fn; },
    appendChild(n) { appended.push(n); n.isConnected = true; }, querySelector() {return {focus() {}};}, focus() {}});
  const doc = {readyState: "complete", cookie: "", head: el(), body: el(),
    createElement() {const n = el(); nodes.push(n); return n;}, addEventListener() {}, querySelector() {return this.body;}};
  const location = {protocol: "https:", hostname: host, origin: "https://" + host,
    pathname: "/en/contact", reload() {this.reloaded = true;}};
  const store = new Map(choice ? [["getvout-analytics-v1", JSON.stringify({choice, at: Date.now()})]] : []);
  const window = {addEventListener(n, fn) {events[n] = fn;}};
  const context = {window, document: doc, location, history: {pushState() {}, replaceState() {}},
    localStorage: {getItem: k => store.get(k), setItem: (k, v) => store.set(k, v)},
    MutationObserver: class {observe() {}}, fetch: async () => {
      if (fail) throw Error("offline");
      return {ok: true, json: async () => ({active, consentRequired: countryConsent})};
    }, console};
  vm.runInNewContext(source, context);
  await new Promise(resolve => setImmediate(resolve));
  return {window, location, nodes, appended, context,
    panel: nodes.find(n => n.id === "gv-consent"),
    scripts: () => appended.filter(n => n.src)};
}
(async () => {
  let r = await run();
  assert.equal(r.panel.hidden, false);
  assert.equal(r.scripts().length, 0);
  r.panel.click({target: {closest: () => ({dataset: {choice: "declined"}})}});
  assert.equal(r.scripts().length, 0);
  assert.equal(r.panel.hidden, true);
  r = await run();
  r.panel.click({target: {closest: () => ({dataset: {choice: "accepted"}})}});
  assert.equal(r.scripts().length, 1);
  assert.equal(r.window.dataLayer.filter(x => x[0] === "event").length, 1);
  r.context.history.replaceState();
  assert.equal(r.window.dataLayer.filter(x => x[0] === "event").length, 1);
  r.location.pathname = "/en/work";
  r.context.history.pushState();
  assert.equal(r.window.dataLayer.filter(x => x[0] === "event").length, 2);
  r.panel.click({target: {closest: () => ({dataset: {choice: "declined"}})}});
  assert.equal(r.window["ga-disable-G-PZ5DTH5MCX"], true);
  assert.equal(r.location.reloaded, true);
  r = await run({countryConsent: false});
  assert.equal(r.scripts().length, 1);
  assert.equal(r.panel.hidden, true);
  r = await run({countryConsent: false, choice: "declined"});
  assert.equal(r.scripts().length, 0);
  r = await run({choice: "accepted"});
  assert.equal(r.scripts().length, 1);
  r = await run({active: false});
  assert.equal(r.scripts().length, 0);
  assert.equal(r.panel, undefined);
  r = await run({host: "preview.vercel.app"});
  assert.equal(r.scripts().length, 0);
  r = await run({fail: true});
  assert.equal(r.panel.hidden, false);
  assert.equal(r.scripts().length, 0);
  console.log("PASS: consent, decline, accept, withdrawal, persistence, SPA deduplication, preview and fail-closed policy");
})().catch(error => {console.error(error); process.exitCode = 1;});
