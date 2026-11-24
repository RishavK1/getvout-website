"""Audit local site content, links, assets and paired server payloads."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs
from lxml import html
from site_data import records

ROOT = Path(__file__).resolve().parent


def audit(forbidden):
    issues = []
    scanned = 0
    suffixes = {".html", ".rsc", ".js", ".css", ".svg", ".json", ".py", ".md", ".txt", ".webmanifest"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes or "__pycache__" in path.parts:
            continue
        scanned += 1
        text = path.read_text(errors="replace")
        for term in forbidden:
            if term.casefold() in text.casefold():
                issues.append({"file":str(path.relative_to(ROOT)), "problem":"Forbidden legacy content"})
    page_results = []
    for path in sorted((ROOT / "faithful/en").glob("**/index.html")):
        doc = html.fromstring(path.read_text())
        route = "/" + str(path.parent.relative_to(ROOT / "faithful"))
        page_issues = []
        def target_exists(url):
            parsed = urlparse(url)
            if parsed.scheme or parsed.netloc or not parsed.path:
                return True
            local = unquote(parsed.path)
            if local == "/_next/image":
                local = parse_qs(parsed.query).get("url", [""])[0]
            if local in {"/", "/contact", "/start-project"}:
                return True
            target = ROOT / "faithful" / local.lstrip("/")
            return target.is_file() or (target / "index.html").is_file()
        for node in doc.xpath('//*[@href or @src or @poster]'):
            for attr in ("href", "src", "poster"):
                value = node.get(attr)
                if value and value.startswith("/") and not target_exists(value):
                    page_issues.append({"problem":"Missing local target", "target":value})
                if value and value.startswith("tel:"):
                    page_issues.append({"problem":"Unexpected telephone link"})
        if not doc.xpath('//meta[@name="robots" and contains(@content,"noindex")]'):
            page_issues.append({"problem":"Preview noindex missing"})
        flight = path.with_suffix(".rsc")
        try:
            list(records(flight.read_text()))
            for script in doc.xpath("//script"):
                match = re.fullmatch(r"self\.__next_f\.push\((.*)\)", script.text or "", re.S)
                if match:
                    payload = json.loads(match[1])
                    if payload[0] == 1:
                        list(records(payload[1]))
        except (ValueError, UnicodeError, OSError) as error:
            page_issues.append({"problem":"Invalid server payload", "detail":str(error)})
        cards = doc.xpath('//*[@data-card]//h3/text()')
        if route == "/en" and cards != ["JAC Creation", "Hira Dhan Builders", "Rudra Infocom", "Bloom"]:
            page_issues.append({"problem":"Homepage selection changed"})
        if route == "/en/work" and len(doc.xpath("//main//ol/li")) != 8:
            page_issues.append({"problem":"Work project count changed"})
        page_results.append({"route":route, "issues":page_issues})
        issues.extend({"route":route, **issue} for issue in page_issues)
    result = {"filesScanned":scanned,"pagesChecked":len(page_results),"issues":issues,"pages":page_results}
    (ROOT / "shots").mkdir(exist_ok=True)
    (ROOT / "shots/site-static-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"Scanned {scanned} text/code files and {len(page_results)} pages: {len(issues)} issues.")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--forbid", action="append", default=[], help="Case-insensitive legacy text to reject")
    args = parser.parse_args()
    raise SystemExit(bool(audit(args.forbid)["issues"]))
