const fs = require("fs");
const { spawn } = require("child_process");
const os = require("os");
const path = require("path");

const args = process.argv.slice(2);
const url = args[0];
const width = Number(args[1] || 1440);
const height = Number(args[2] || 900);
const out = args[3] || "shot.png";
const script = args[4] || "";
const delay = Number(args[5] || 700);
const afterNavigationScript = args[6] || "";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "getvout-preview-test-"));
  const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
    "--headless=new", "--hide-scrollbars", "--remote-debugging-port=0",
    "--user-data-dir=" + profile, "--no-first-run", "about:blank"
  ]);
  const port = await new Promise((resolve, reject) => {
    let text = "";
    chrome.stderr.on("data", chunk => {
      text += chunk;
      const found = text.match(/DevTools listening on ws:\/\/[^:]+:(\d+)\//);
      if (found) resolve(Number(found[1]));
    });
    chrome.on("error", reject);
    chrome.on("exit", code => reject(new Error("Chrome exited: " + code)));
  });
  process.on("exit", () => chrome.kill());
  const list = await (await fetch("http://127.0.0.1:" + port + "/json/list")).json();
  const page = list.find((t) => t.type === "page");
  if (!page) throw new Error("no page target");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const events = [];
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message));
      else resolve(msg.result);
    } else if (msg.method) {
      events.push(msg);
    }
  });
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, { once: true });
    ws.addEventListener("error", reject, { once: true });
  });
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const callId = ++id;
      pending.set(callId, { resolve, reject });
      ws.send(JSON.stringify({ id: callId, method, params }));
    });

  await send("Page.enable");
  await send("Runtime.enable");
  await send("Network.enable");
  // Scroll scenes are disabled for HeadlessChrome by default.
  // Use a standard Chrome UA to exercise its normal interactive path.
  if (process.env.INTERACTIVE) {
    await send("Network.setUserAgentOverride", {
      userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    });
  }
  await send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: width < 700,
  });
  if (process.env.SITE_AUDIT) {
    const siteRoot = path.resolve(__dirname, "../faithful");
    const routes = fs.readdirSync(path.join(siteRoot, "en"), {recursive:true})
      .filter(name => name === "index.html" || name.endsWith("/index.html"))
      .map(name => "/en/" + name.replace(/index\.html$/, "").replace(/\/$/, ""))
      .map(route => route.replace(/\/$/, ""));
    const results = [];
    for (const size of [{width:1440,height:900},{width:390,height:844}]) {
      await send("Emulation.setDeviceMetricsOverride", {...size,deviceScaleFactor:1,mobile:size.width<700});
      for (const route of routes) {
        const start = events.length;
        await send("Page.navigate", {url:new URL(route,url).href});
        for(let i=0;i<100;i++) {
          const state=await send("Runtime.evaluate",{
            expression:`document.readyState==="complete"&&location.pathname===${JSON.stringify(route)}`,
            returnByValue:true
          });
          if(state.result?.value) break;
          await sleep(40);
        }
        await sleep(900);
        const dom = await send("Runtime.evaluate", {
          expression:`(() => ({
            title:document.title,
            description:document.querySelector('meta[name="description"]')?.content,
            canonical:document.querySelector('link[rel="canonical"]')?.href,
            robots:document.querySelector('meta[name="robots"]')?.content,
            schemaCount:document.querySelectorAll('script[type="application/ld+json"]').length,
            schemaTypes:[...document.querySelectorAll('script[type="application/ld+json"]')].flatMap(s=>{try{return (JSON.parse(s.textContent)['@graph']||[]).map(n=>n['@type'])}catch{return ['INVALID_JSON']}}),
            heading:document.querySelector("h1")?.textContent,
            overflow:document.documentElement.scrollWidth>innerWidth,
            projects:document.querySelectorAll("[data-card]").length,
            work:document.querySelectorAll("main ol>li").length,
            links:[...new Set([...document.querySelectorAll("a")].map(a=>a.href))],
            brokenImages:[...document.images].filter(i=>i.complete&&!i.naturalWidth).map(i=>i.currentSrc||i.src)
          }))()`,
          returnByValue:true
        });
        const seen=events.slice(start);
        results.push({
          route,width:size.width,...dom.result?.value,
          errors:seen.filter(e=>e.method==="Runtime.exceptionThrown"||(e.method==="Runtime.consoleAPICalled"&&e.params.type==="error")).map(e=>e.params),
          failedResponses:seen.filter(e=>e.method==="Network.responseReceived"&&e.params.response.status>=400).map(e=>({url:e.params.response.url,status:e.params.response.status})),
          externalRequests:seen.filter(e=>e.method==="Network.requestWillBeSent"&&!e.params.request.url.startsWith(new URL(url).origin)&&/^https?:/.test(e.params.request.url)).map(e=>e.params.request.url)
        });
        console.log("AUDIT",route,size.width,"errors",results.at(-1).errors.length);
      }
    }
    fs.writeFileSync(process.env.SITE_AUDIT,JSON.stringify(results,null,2));
    ws.close();
    chrome.kill();
    return;
  }
  await send("Page.navigate", { url });
  for (let i = 0; i < 120; i++) {
    const state = await send("Runtime.evaluate", {
      expression: "document.readyState",
      returnByValue: true,
    });
    if (state.result && state.result.value === "complete") break;
    await sleep(50);
  }
  await sleep(450);
  // Optional real-browser project recording: capture rendered frames while
  // scrolling the live project. Normal screenshot/audit runs are unchanged.
  if (process.env.PROJECT_FRAMES) {
    fs.mkdirSync(process.env.PROJECT_FRAMES, { recursive: true });
    await send("Runtime.evaluate", {
      expression: "document.fonts.ready", awaitPromise: true,
    });
    await sleep(1500);
    for (let frame = 0; frame < 64; frame++) {
      const progress = frame < 8 ? 0 : frame > 55 ? 1 : (frame - 8) / 47;
      await send("Runtime.evaluate", {
        expression: `scrollTo({top:Math.min(document.documentElement.scrollHeight-innerHeight,2400)*${progress},behavior:'instant'})`,
      });
      await sleep(100);
      const capture = await send("Page.captureScreenshot", {format:"jpeg",quality:85,fromSurface:true});
      fs.writeFileSync(path.join(process.env.PROJECT_FRAMES, String(frame).padStart(3,"0")+".jpg"), Buffer.from(capture.data,"base64"));
    }
  }
  if (script) {
    const result = await send("Runtime.evaluate", {
      expression: script,
      returnByValue: true,
      awaitPromise: true,
    });
    if (result.exceptionDetails) {
      console.error("EVAL ERROR", JSON.stringify(result.exceptionDetails));
    } else if (result.result && result.result.value !== undefined) {
      console.log("EVAL", JSON.stringify(result.result.value));
    }
  }
  await sleep(delay);
  if (afterNavigationScript) {
    const result = await send("Runtime.evaluate", {
      expression: afterNavigationScript, returnByValue: true, awaitPromise: true,
    });
    console.log("AFTER NAV", JSON.stringify(result.exceptionDetails || result.result?.value));
  }
  if (process.env.HOVER_VIDEOS) {
    const playback = [];
    for (let index = 0; index < 5; index++) {
      const point = await send("Runtime.evaluate", {
        expression: `(() => { const el = document.querySelectorAll('.work-reel')[${index}]; el.scrollIntoView({block:'center',behavior:'instant'}); const r = el.getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2}; })()`,
        returnByValue: true,
      });
      await sleep(700);
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", ...point.result.value });
      await sleep(1600);
      const state = await send("Runtime.evaluate", {
        expression: `(() => { const v=document.querySelectorAll('.wr-video')[${index}]; return {src:v.getAttribute('src'),ready:v.readyState,playing:!v.paused,time:v.currentTime,error:v.error?.message??null}; })()`,
        returnByValue: true,
      });
      playback.push(state.result.value);
      await send("Input.dispatchMouseEvent", {type:"mouseMoved",x:5,y:5});
    }
    console.log("VIDEO PLAYBACK", JSON.stringify(playback));
  }
  const shot = await send("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: false,
  });
  fs.writeFileSync(out, Buffer.from(shot.data, "base64"));
  const errors = events.filter(
    (e) => e.method === "Runtime.exceptionThrown" || (e.method === "Runtime.consoleAPICalled" && e.params.type === "error")
  );
  console.log("SAVED", out, "errors", errors.length);
  if (process.env.AUDIT_FORMS) {
    console.log("FORM POST REQUESTS", JSON.stringify(events.filter(e =>
      e.method === "Network.requestWillBeSent" && e.params.request.method === "POST"
    ).map(e => e.params.request.url)));
  }
  if (errors.length) console.log(JSON.stringify(errors.slice(0, 4)));
  const failures = events.filter(e =>
    (e.method === "Network.responseReceived" && e.params.response.status >= 400) ||
    e.method === "Network.loadingFailed"
  );
  if (failures.length) console.log("NETWORK FAILURES", JSON.stringify(failures.map(e => e.params)));
  ws.close();
  chrome.kill();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
