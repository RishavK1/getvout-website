// Publish static assets at the edge; the Python adapter handles page/RSC routes.
const fs = require("node:fs");
const path = require("node:path");
const source = path.join(__dirname, "site-source");
const output = path.join(__dirname, "public");
fs.mkdirSync(output, { recursive: true });
for (const name of fs.readdirSync(source)) {
  if (name === "en" || name === "index.html" || name === "api") continue;
  fs.cpSync(path.join(source, name), path.join(output, name), { recursive: true });
}
fs.cpSync(path.join(source, "api"), path.join(output, "api"), { recursive: true });
console.log("Local static assets prepared for Vercel.");
