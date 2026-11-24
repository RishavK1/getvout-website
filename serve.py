"""Serve the local getvout website; no remote proxy or asset downloads."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote, urlencode
import argparse
import json
import re
from html import escape

ROOT = Path(__file__).resolve().parent / "faithful"
JOURNAL = json.loads((ROOT.parent / "journal-content/articles.json").read_text())


def brief_content(content, query, html=False):
    """Preserve service enquiry presets without production Server Components."""
    params = parse_qs(query)
    preset = params.get("type", [""])[0]
    if preset == "photo":
        preset = "automation"
    if preset not in {"website", "shop", "software", "branding", "automation", "ai", "unsure"}:
        return content
    modules = {
        "booking": "Online booking", "cms": "Content management",
        "automation": "Automations", "payment": "Online payment",
        "languages": "Multilingual", "reviews": "Google reviews",
        "newsletter": "Newsletter", "analytics": "Cookie-free analytics", "chat": "AI chat",
    }
    selected = [modules[key] for key in params.get("modules", [""])[0].split(",") if key in modules]
    message = "I am interested in a website with these modules: " + ", ".join(selected) + "." if selected else "$undefined"
    old = '"preset":"$undefined","message":"$undefined"'
    new = '"preset":' + json.dumps(preset) + ',"message":' + json.dumps(message)
    text = content.decode()
    if html:
        text = text.replace(json.dumps(old)[1:-1], json.dumps(new)[1:-1])
        text = re.sub(
            rf'(<input\b[^>]*name="projectType"[^>]*value="{re.escape(preset)}")(\s*/?>)',
            lambda m: m[1] + ' checked=""' + m[2], text,
        )
        if selected:
            text = re.sub(r'(<textarea\b[^>]*id="f-message"[^>]*>)(</textarea>)',
                          lambda m: m[1] + escape(message) + m[2], text)
    else:
        text = text.replace(old, new)
        search = "?" + urlencode({key: params[key][0] for key in ("type", "modules") if key in params})
        text = text.replace('"q":""', '"q":' + json.dumps(search))
    return text.encode()


class PreviewServer(ThreadingHTTPServer):
    request_queue_size = 128


class PreviewHandler(SimpleHTTPRequestHandler):
    def send_error(self, code, message=None, explain=None):
        page = ROOT / "404.html"
        if code != 404 or not page.is_file():
            return super().send_error(code, message, explain)
        # Missing assets/RSC requests remain errors too; never redirect or return
        # a successful response for an address which does not exist.
        content = page.read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Robots-Tag", "noindex, follow")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(content)

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        if route in {"/contact", "/start-project"}:
            self.send_response(302)
            self.send_header("Location", "/en" + route + ("?" + parsed.query if parsed.query else ""))
            self.end_headers()
            return
        routes = {"/en", "/en/work", "/en/services", "/en/studio", "/en/journal", "/en/contact", "/en/start-project", "/en/privacy", "/en/imprint"}
        routes.update(
            "/en/services/" + slug for slug in [
                "websites", "custom-software-apps", "brand-logo", "ai-assistants",
                "hosting-domains-email", "online-shops",
                "workflow-automation",
            ]
        )
        routes.update("/en/journal/" + article["slug"] for article in JOURNAL)
        if "_rsc" in parse_qs(parsed.query, keep_blank_values=True) or self.headers.get("RSC") == "1":
            flight = ROOT / route.lstrip("/") / "index.rsc"
            if route in routes and flight.is_file():
                content = flight.read_bytes()
                if route == "/en/start-project":
                    content = brief_content(content, parsed.query)
                self.send_response(200)
                self.send_header("Content-Type", "text/x-component")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Vary", "RSC, Next-Router-State-Tree, Next-Router-Prefetch")
                self.end_headers()
                self.wfile.write(content)
                return
            self.send_error(404, "Page not found")
            return
        if parsed.path == "/":
            self.send_response(302)
            self.send_header("Location", "/en")
            self.end_headers()
            return
        if route in routes:
            if route == "/en/start-project" and "type" in parse_qs(parsed.query):
                content = brief_content((ROOT / "en/start-project/index.html").read_bytes(), parsed.query, html=True)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            self.path = route + "/index.html"
        elif parsed.path == "/_next/image":
            original = parse_qs(parsed.query).get("url", [""])[0]
            if not original.startswith(("/api/media/file/", "/img/")) or ".." in unquote(original):
                self.send_error(400, "Invalid image")
                return
            self.path = original
        elif parsed.path.startswith("/en/") and not (ROOT / parsed.path.lstrip("/")).exists():
            self.send_error(404, "Page not found")
            return
        if parsed.path.endswith(".mp4") and self.headers.get("Range"):
            self.serve_video_range()
            return
        super().do_GET()

    def serve_video_range(self):
        file = Path(self.translate_path(self.path))
        if not file.is_file():
            self.send_error(404)
            return
        size = file.stat().st_size
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if not match or not any(match.groups()):
            self.send_error(416)
            return
        if match[1]:
            start = int(match[1])
            end = min(int(match[2]) if match[2] else size - 1, size - 1)
        else:
            start = max(0, size - int(match[2]))
            end = size - 1
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return
        self.send_response(206)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with file.open("rb") as stream:
            stream.seek(start)
            remaining = end - start + 1
            try:
                while remaining:
                    chunk = stream.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    handler = partial(PreviewHandler, directory=str(ROOT))
    print(f"getvout preview: http://localhost:{args.port}/en", flush=True)
    PreviewServer(("127.0.0.1", args.port), handler).serve_forever()
