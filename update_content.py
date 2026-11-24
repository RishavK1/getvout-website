"""Replace a literal text/URL consistently in canonical HTML and Flight data."""
import argparse
import json
import re
from pathlib import Path
from lxml import html
from site_data import records, encode

ROOT = Path(__file__).resolve().parent


def replace(old, new):
    def text(value):
        return value.replace(old, new)
    def data(value):
        if isinstance(value, str):
            return text(value)
        if isinstance(value, list):
            return [data(v) for v in value]
        if isinstance(value, dict):
            return {k:data(v) for k,v in value.items()}
        return value
    def flight(value):
        return encode((k,t,data(v) if t=="J" else text(v)) for k,t,v in records(value))
    source = ROOT / "site-source"
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".rsc":
            path.write_text(flight(path.read_text()))
        elif path.suffix == ".html":
            doc = html.document_fromstring(path.read_text())
            for node in doc.iter():
                for key,value in node.attrib.items():
                    node.set(key,text(value))
                if node.tag == "script":
                    match = re.fullmatch(r"self\.__next_f\.push\((.*)\)",node.text or "",re.S)
                    if match:
                        payload = json.loads(match[1])
                        if payload[0] == 1:
                            payload[1] = flight(payload[1])
                        node.text = "self.__next_f.push("+json.dumps(payload,ensure_ascii=False).replace("<","\\u003c")+")"
                    elif node.text:
                        node.text = text(node.text)
                elif node.text:
                    node.text = text(node.text)
                if node.tail:
                    node.tail = text(node.tail)
            path.write_text("<!DOCTYPE html>\n"+html.tostring(doc,encoding="unicode",method="html"))
        elif path.suffix in {".js",".css",".svg",".json",".webmanifest",".txt"}:
            path.write_text(text(path.read_text()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    args = parser.parse_args()
    if not args.old:
        parser.error("--old cannot be empty")
    replace(args.old,args.new)
    print("Canonical sources updated. Rebuild and audit before using the preview.")
