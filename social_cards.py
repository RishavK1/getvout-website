"""Design reproducible getvout sharing cards using the site's own typeface.

Run with the local preview server available. No remote images, client photos,
AI API, browser login or credentials are needed.
"""
import argparse
import html
import json
import os
import shutil
import subprocess
from pathlib import Path
from seo_content import PAGES, SOURCE, ROOT

HEADLINES = {
    "/en": ("Thoughtful work.<br>Made real.", "Design, development and AI.<br>One team. Built around your business."),
    "/en/work": ("Digital work.<br>Real possibilities.", "Selected websites, web apps<br>and digital experiences."),
    "/en/studio": ("Good work.<br>Better together.", "Meet the team behind getvout."),
    "/en/services": ("From first idea<br>to what’s next.", "Websites, software, branding<br>and connected systems."),
    "/en/contact": ("Let’s make<br>something useful.", "Start a conversation with our team.<br>Email or WhatsApp."),
    "/en/start-project": ("Your next idea.<br>Our next project.", "Tell us what you have in mind."),
    "/en/privacy": ("Your privacy.<br>Clearly explained.", "How the getvout website handles information."),
    "/en/imprint": ("The details<br>behind getvout.", "Studio information and contact details."),
    "/en/services/websites": ("Websites made<br>to mean more.", "Custom design. Considered development."),
    "/en/services/custom-software-apps": ("Software shaped<br>around your work.", "Custom software and web applications."),
    "/en/services/brand-logo": ("A clear identity.<br>A lasting impression.", "Brand identity and logo design."),
    "/en/services/ai-assistants": ("AI with<br>a useful purpose.", "Thoughtful assistants and integrations."),
    "/en/services/online-shops": ("Your products.<br>A better experience.", "E-commerce websites and online shops."),
    "/en/services/workflow-automation": ("Less repetition.<br>More possibility.", "Connected tools. Clearer workflows."),
    "/en/services/hosting-domains-email": ("A strong home<br>for your website.", "Hosting, domains and business email."),
}


def artwork(route, dark):
    ink = "#f4f4f2" if dark else "#121214"
    faint = "#39393b" if dark else "#d8d8d5"
    # One visual motif: precision, the red focal point and a measured aperture.
    # Individual service treatments echo what that page offers.
    body = ""
    if route.endswith("/websites") or route == "/en/work":
        body = f'<rect x="35" y="82" width="260" height="186" rx="14" fill="none" stroke="{ink}" stroke-width="3"/><path d="M35 120H295M60 145H173M60 165H135M60 235H165" stroke="{ink}" stroke-width="3"/><circle cx="60" cy="101" r="4" fill="#ff3e3e"/><rect x="194" y="144" width="74" height="92" rx="5" fill="#ff3e3e"/>'
    elif route.endswith("/workflow-automation") or route.endswith("/custom-software-apps"):
        body = f'<path d="M70 110H165V215H265M165 110V45" fill="none" stroke="{ink}" stroke-width="3"/><rect x="30" y="75" width="80" height="70" rx="16" fill="{ink}"/><rect x="125" y="175" width="80" height="80" rx="16" fill="#ff3e3e"/><circle cx="265" cy="215" r="28" fill="{ink}"/><circle cx="165" cy="45" r="12" fill="#ff3e3e"/>'
    elif route.endswith("/hosting-domains-email"):
        body = f'<rect x="35" y="105" width="260" height="155" rx="14" fill="none" stroke="{ink}" stroke-width="3"/><path d="M40 110L165 198L290 110" stroke="#ff3e3e" stroke-width="4" fill="none"/><circle cx="165" cy="52" r="18" fill="#ff3e3e"/><path d="M165 72V91" stroke="{ink}" stroke-width="3"/>'
    elif route.endswith("/online-shops"):
        body = f'<path d="M67 112H263L278 284H52Z" fill="none" stroke="{ink}" stroke-width="3"/><path d="M118 133V94A47 47 0 0 1 212 94V133" fill="none" stroke="{ink}" stroke-width="3"/><circle cx="165" cy="205" r="29" fill="#ff3e3e"/>'
    else:
        body = f'<circle cx="165" cy="165" r="120" fill="none" stroke="{ink}" stroke-width="2"/><circle cx="165" cy="165" r="94" fill="none" stroke="{faint}" stroke-width="2"/><circle cx="165" cy="165" r="23" fill="#ff3e3e"/><path d="M165 17V36M165 294V313M17 165H36M294 165H313" stroke="#ff3e3e" stroke-width="3"/><path d="M264 264L313 313" stroke="{ink}" stroke-width="10" stroke-linecap="round"/>'
    return f'<svg viewBox="0 0 330 330" xmlns="http://www.w3.org/2000/svg">{body}</svg>'


def template(route, info):
    is_article = "article" in info
    dark = route == "/en" or is_article
    section = "Journal" if is_article else "Services" if route.startswith("/en/services/") else "Digital studio"
    title, subtitle = HEADLINES.get(route, (html.escape(info["label"]), "Practical ideas. Useful details.<br>From the getvout journal."))
    if is_article:
        title = html.escape(info["article"]["title"])
    small_label = info["label"] if route.startswith("/en/services/") else section
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex"><style>
    @font-face{{font-family:Studio;src:url("/_next/static/media/0c89a48fa5027cee-s.p.2cyn07wtgehh0.woff2") format("woff2");font-weight:100 900;font-display:block}}
    *{{box-sizing:border-box}}html,body{{margin:0;width:1200px;height:630px;overflow:hidden}}
    body{{font-family:Studio,Arial,sans-serif;background:{"#121214" if dark else "#f4f4f2"};color:{"#f4f4f2" if dark else "#121214"};-webkit-font-smoothing:antialiased}}
    .frame{{position:relative;width:1200px;height:630px;padding:58px 70px}}
    .brand{{font-size:{"88px" if route=="/en" else "48px"};font-weight:600;letter-spacing:-.055em;line-height:1}}
    .brand span{{color:#ff3e3e}}.category{{position:absolute;right:72px;top:72px;font-size:19px;color:{"#b5b5b2" if dark else "#626260"}}}
    .copy{{position:absolute;left:72px;top:{"211px" if route=="/en" else "187px"};width:{"745px" if is_article else "750px"}}}
    h1{{font-size:{"65px" if is_article else "74px"};font-weight:500;letter-spacing:-.047em;line-height:1.075;margin:0;max-width:{"720px" if is_article else "750px"};text-wrap:balance}}
    p{{font-size:23px;line-height:1.45;margin:25px 0 0;color:{"#b5b5b2" if dark else "#626260"}}}
    .art{{position:absolute;width:{"260px" if is_article else "285px"};height:285px;right:{"54px" if is_article else "62px"};top:{"225px" if is_article else "204px"};{"opacity:.65" if is_article else ""}}}
    .art:before{{content:"";position:absolute;inset:-36px;background-image:linear-gradient({"#f4f4f20b" if dark else "#12121408"} 1px,transparent 1px),linear-gradient(90deg,{"#f4f4f20b" if dark else "#12121408"} 1px,transparent 1px);background-size:28px 28px;mask-image:radial-gradient(ellipse,black,transparent 70%)}}
    svg{{position:relative;width:100%;height:100%}}
    .footer{{position:absolute;bottom:42px;left:72px;right:72px;border-top:1px solid {"#39393b" if dark else "#d6d6d2"};padding-top:22px;display:flex;justify-content:space-between;align-items:center;font-size:17px}}
    .location{{color:{"#b5b5b2" if dark else "#626260"}}}.site{{display:flex;align-items:center;gap:12px}}.site:before{{content:"";width:8px;height:8px;background:#ff3e3e;border-radius:50%}}
    .edge{{position:absolute;width:26px;height:26px;right:43px;bottom:27px;border-right:2px solid #ff3e3e;border-bottom:2px solid #ff3e3e}}
    </style></head><body><div class="frame"><div class="brand">getvout<span>.</span></div>
    <div class="category">{html.escape(small_label)}</div>
    <div class="copy"><h1>{title}</h1><p>{subtitle}</p></div>
    <div class="art">{artwork(route,dark)}</div>
    <div class="footer"><span class="location">Karnal, India · Working together</span><span class="site">getvout.com</span></div><span class="edge"></span>
    </div></body></html>'''


def generate(base):
    preview = ROOT / "faithful/_social-preview"
    preview.mkdir(exist_ok=True)
    output = SOURCE / "img/getvout/social-v2"
    output.mkdir(parents=True, exist_ok=True)
    tasks = []
    for route, info in PAGES.items():
        name = "home" if route == "/en" else route.removeprefix("/en/").replace("/", "-")
        page = preview / (name + ".html")
        page.write_text(template(route, info))
        tasks.append({
            "url": base.rstrip("/") + "/_social-preview/" + page.name,
            "path": str(output / (name + ".jpg")),
            "route": route,
        })
    manifest = ROOT / "shots/social-render-tasks.json"
    manifest.parent.mkdir(exist_ok=True)
    manifest.write_text(json.dumps(tasks, indent=2))
    env = {**os.environ, "SOCIAL_CARDS": str(manifest)}
    subprocess.run(["node", "shots/cdp.js", base, "1200", "630"], cwd=ROOT, env=env, check=True)
    # Existing social URLs must not continue serving a client project image.
    shutil.copyfile(output / "home.jpg", SOURCE / "img/getvout/social-site.jpg")
    for index, (_, info) in enumerate((item for item in PAGES.items() if "article" in item[1])):
        name = "journal-" + info["article"]["slug"]
        shutil.copyfile(output / (name + ".jpg"), SOURCE / f"img/getvout/social-journal-{index}.jpg")
    # Only remove the temporary HTML files this invocation created.
    for task in tasks:
        (preview / (Path(task["path"]).stem + ".html")).unlink()
    if not any(preview.iterdir()):
        preview.rmdir()
    print(f"Generated {len(tasks)} branded 1200 × 630 JPEG sharing cards.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:4173")
    generate(parser.parse_args().base)
