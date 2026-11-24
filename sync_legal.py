"""Sync legal draft fragments into paired HTML and server-component sources."""
import copy
import json
import re
from pathlib import Path
from lxml import html
from site_data import records, encode

ROOT = Path(__file__).resolve().parent


def element(node):
    children = [node.text] if node.text else []
    for child in node:
        children.append(element(child))
        if child.tail and child.tail.strip():
            children.append(child.tail)
    props = {("className" if key == "class" else key): value for key, value in node.attrib.items()}
    if children:
        props["children"] = children[0] if len(children) == 1 else children
    return ["$", node.tag, None, props]


def sync(base):
    for slug in ("privacy", "imprint"):
        fragment = html.fragment_fromstring((ROOT / f"legal-content/{slug}.html").read_text(), create_parent="div")
        children = [element(node) for node in fragment]
        def transform(value):
            if isinstance(value, list):
                if len(value) == 4 and value[:2] == ["$", "div"] and isinstance(value[3], dict) and value[3].get("className") == "prose":
                    return value[:3] + [{**value[3], "children":children}]
                return [transform(item) for item in value]
            if isinstance(value, dict):
                return {key:transform(item) for key,item in value.items()}
            return value
        def flight(source):
            return encode((key, kind, transform(value) if kind == "J" else value) for key,kind,value in records(source))
        path = base / f"en/{slug}/index.html"
        doc = html.document_fromstring(path.read_text())
        prose = doc.xpath('//main//div[@class="prose"]')[0]
        for node in list(prose):
            prose.remove(node)
        prose.text = None
        for node in fragment:
            copied = copy.deepcopy(node)
            # Flight element children omit formatting-only whitespace.
            for descendant in copied.iter():
                if descendant.tail and not descendant.tail.strip():
                    descendant.tail = None
                if descendant.text and not descendant.text.strip():
                    descendant.text = None
            prose.append(copied)
        for script in doc.xpath("//script"):
            match = re.fullmatch(r"self\.__next_f\.push\((.*)\)", script.text or "", re.S)
            if match:
                payload = json.loads(match[1])
                if payload[0] == 1:
                    payload[1] = flight(payload[1])
                script.text = "self.__next_f.push(" + json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c") + ")"
        path.write_text("<!DOCTYPE html>\n" + html.tostring(doc, encoding="unicode", method="html"))
        rsc = path.with_suffix(".rsc")
        rsc.write_text(flight(rsc.read_text()))


if __name__ == "__main__":
    sync(ROOT / ("site-source" if (ROOT / "site-source").is_dir() else "faithful"))
    print("Legal sources synchronized. Run build_local.py to refresh the preview.")
