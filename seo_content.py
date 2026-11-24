"""Apply approved SEO content to SSR, Flight, metadata and discovery files."""
import copy
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from lxml import html, etree
from PIL import Image, ImageOps
from site_data import records, encode

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "site-source"
CONFIG = json.loads((ROOT / "seo-config.json").read_text())
ORIGIN = CONFIG["origin"]
HOME = ORIGIN + CONFIG["home"]
NOINDEX = set(CONFIG["noindex"])
ARTICLES = json.loads((ROOT / "journal-content/articles.json").read_text())
PAGES = copy.deepcopy(CONFIG["pages"])
OLD_DISCLOSURE = "getvout journal · AI-assisted editorial draft. Primary sources are linked above; review before public publication."
DISCLOSURE = "getvout journal · AI-assisted content reviewed by the getvout team. Primary sources are linked above."
for index, article in enumerate(ARTICLES):
    route = "/en/journal/" + article["slug"]
    PAGES[route] = {
        "title": article["title"] + " | getvout",
        "description": article["description"], "label": article["title"],
        "article": article, "image": f"/img/getvout/social-journal-{index}.jpg",
    }


def organization():
    return {
        "@type": "Organization", "@id": ORIGIN + "/#organization",
        "name": "getvout", "url": HOME,
        "description": "Design and development team in Karnal, Haryana, India building websites, web applications, online shops and workflow automation.",
        "logo": {"@type": "ImageObject", "@id": ORIGIN + "/#logo",
                 "url": ORIGIN + "/img/getvout/icon-v2-512.png", "width": 512, "height": 512},
        "email": ["hello@getvout.com", "contact@getvout.com"],
        "address": {"@type": "PostalAddress", "addressLocality": "Karnal",
                    "addressRegion": "Haryana", "addressCountry": "IN"},
        "contactPoint": {"@type": "ContactPoint", "contactType": "WhatsApp enquiries",
                         "url": "https://wa.me/917404511743", "availableLanguage": ["English"]},
        "sameAs": ["https://www.linkedin.com/company/getvout/", "https://www.instagram.com/getvout"],
    }


def schema(route, info):
    url = ORIGIN + route
    kind = "ContactPage" if route == "/en/contact" else "AboutPage" if route == "/en/studio" else "CollectionPage" if route in {"/en/work", "/en/services", "/en/journal"} else "WebPage"
    crumbs = [("Home", HOME)]
    if route.startswith("/en/services/"):
        crumbs.append(("Services", ORIGIN + "/en/services"))
    if route.startswith("/en/journal/"):
        crumbs.append(("Journal", ORIGIN + "/en/journal"))
    if route != "/en":
        crumbs.append((info["label"], url))
    nodes = [
        organization(),
        {"@type": "WebSite", "@id": ORIGIN + "/#website", "url": HOME, "name": "getvout",
         "inLanguage": "en-IN", "publisher": {"@id": ORIGIN + "/#organization"}},
        {"@type": kind, "@id": url + "#webpage", "url": url, "name": info["title"],
         "description": info["description"], "inLanguage": "en-IN",
         "isPartOf": {"@id": ORIGIN + "/#website"}, "about": {"@id": ORIGIN + "/#organization"},
         "breadcrumb": {"@id": url + "#breadcrumb"}},
        {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": href}
            for i, (name, href) in enumerate(crumbs)
        ]},
    ]
    if route.startswith("/en/services/"):
        nodes[2]["mainEntity"] = {"@id": url + "#service"}
        nodes.append({"@type": "Service", "@id": url + "#service", "name": info["label"],
                      "serviceType": info["label"], "url": url,
                      "description": info["description"],
                      "provider": {"@id": ORIGIN + "/#organization"}})
    elif route == "/en/services":
        nodes[2]["mainEntity"] = {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": ORIGIN + key,
             "name": value["label"]}
            for i, (key, value) in enumerate((k, v) for k, v in PAGES.items() if k.startswith("/en/services/"))
        ]}
    elif route == "/en/journal":
        nodes[2]["mainEntity"] = {"@id": url + "#blog"}
        nodes.append({"@type": "Blog", "@id": url + "#blog", "name": "getvout Journal",
                      "url": url, "publisher": {"@id": ORIGIN + "/#organization"},
                      "blogPost": [{"@id": ORIGIN + "/en/journal/" + a["slug"] + "#article"} for a in ARTICLES]})
    if "article" in info:
        article = info["article"]
        nodes[2]["mainEntity"] = {"@id": url + "#article"}
        nodes.append({
            "@type": "BlogPosting", "@id": url + "#article",
            "headline": article["title"], "description": info["description"],
            "url": url, "mainEntityOfPage": {"@id": url + "#webpage"},
            "image": ORIGIN + info["image"],
            "datePublished": CONFIG["publicationDate"], "dateModified": CONFIG["publicationDate"],
            "inLanguage": "en-IN", "timeRequired": f"PT{article['minutes']}M",
            "creativeWorkStatus": "Published",
            "author": {"@id": ORIGIN + "/#organization"},
            "publisher": {"@id": ORIGIN + "/#organization"},
            "isPartOf": {"@id": ORIGIN + "/en/journal#blog"},
        })
    return json.dumps({"@context": "https://schema.org", "@graph": nodes}, ensure_ascii=False, separators=(",", ":"))


def metadata(route, info):
    url = ORIGIN + route
    image = ORIGIN + info.get("image", "/img/getvout/social-site.jpg")
    title, desc = info["title"], info["description"]
    robots = "noindex, follow" if route in NOINDEX else "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
    image_alt = info["label"] + " — getvout journal illustration" if "article" in info else "getvout portfolio — JAC Creation website"
    result = [("title", {}, title)]
    result += [("meta", {"name": name, "content": value}, None) for name, value in [
        ("description", desc), ("application-name", "getvout"), ("author", "getvout"),
        ("robots", robots), ("twitter:card", "summary_large_image"),
        ("twitter:title", title), ("twitter:description", desc),
        ("twitter:image", image), ("twitter:image:alt", image_alt),
    ]]
    result += [("link", {"rel": "canonical", "href": url}, None)]
    result += [("meta", {"property": name, "content": value}, None) for name, value in [
        ("og:title", title), ("og:description", desc), ("og:url", url), ("og:site_name", "getvout"),
        ("og:locale", "en_IN"), ("og:type", "article" if "article" in info else "website"),
        ("og:image", image), ("og:image:type", "image/jpeg"),
        ("og:image:width", "1200"), ("og:image:height", "630"), ("og:image:alt", image_alt),
    ]]
    if "article" in info:
        result += [("meta", {"property": name, "content": value}, None) for name, value in [
            ("article:published_time", CONFIG["publicationDate"]),
            ("article:modified_time", CONFIG["publicationDate"]),
        ]]
    result += [
        ("link", {"rel": "manifest", "href": "/manifest.webmanifest"}, None),
        ("link", {"rel": "icon", "href": "/img/getvout/favicon-v2.svg", "type": "image/svg+xml", "sizes": "any"}, None),
        ("link", {"rel": "icon", "href": "/img/getvout/icon-v2-96.png", "type": "image/png", "sizes": "96x96"}, None),
        ("link", {"rel": "apple-touch-icon", "href": "/img/getvout/icon-v2-180.png", "sizes": "180x180"}, None),
    ]
    return result


def is_schema(value):
    if not isinstance(value, str) or not value.startswith("{"):
        return False
    try:
        return json.loads(value).get("@context") == "https://schema.org"
    except (ValueError, AttributeError):
        return False


def apply_page(route, info):
    path = SOURCE / route.lstrip("/") / "index.html"
    graph = schema(route, info)
    entries = metadata(route, info)
    def text(value):
        value = value.replace(OLD_DISCLOSURE, DISCLOSURE)
        value = value.replace("23 November 2026", CONFIG["publishedDateLabel"])
        value = value.replace("2026-11-23", CONFIG["publicationDate"][:10])
        return value
    def flight(source):
        rows = list(records(source))
        schema_keys = {key for key, kind, value in rows if kind in {"T", "J"} and is_schema(value)}
        def find_schema(value):
            if isinstance(value, list):
                if len(value) == 4 and value[:2] == ["$", "script"] and isinstance(value[3], dict) and value[3].get("type") == "application/ld+json":
                    return value[3].get("dangerouslySetInnerHTML", {}).get("__html")
                for child in value:
                    found = find_schema(child)
                    if found is not None:
                        return found
            elif isinstance(value, dict):
                for child in value.values():
                    found = find_schema(child)
                    if found is not None:
                        return found
            return None
        # Flight records arrive out of visual order. Keep the layout's schema,
        # not whichever page-level script happens to occur first in the stream.
        layout_row = next(((key, value) for key, kind, value in rows if kind == "J" and isinstance(value, list) and value[:2] == ["$", "html"]), None)
        layout = layout_row[1] if layout_row else None
        owner = layout_row[0] if layout_row else None
        root_schema = find_schema(layout) if layout else None
        if root_schema is None:
            found = next(((key, find_schema(v)) for key, t, v in rows if t == "J" and find_schema(v) is not None), (None, None))
            owner, root_schema = found
        def visit(value):
            if isinstance(value, str):
                return graph if is_schema(value) else text(value)
            if isinstance(value, list):
                # Metadata array: preserve framework-specific marker components.
                if value and all(isinstance(n, list) and len(n) == 4 for n in value) and any(n[:2] == ["$", "meta"] and isinstance(n[3], dict) and n[3].get("name") == "robots" for n in value):
                    others = [visit(n) for n in value if n[1] not in {"title", "meta", "link"}]
                    return [["$", tag, "seo-" + str(i), {**props, **({"children": content} if content else {})}]
                            for i, (tag, props, content) in enumerate(entries)] + others
                if len(value) == 4 and value[:2] == ["$", "script"] and isinstance(value[3], dict) and value[3].get("type") == "application/ld+json":
                    pointer = value[3].get("dangerouslySetInnerHTML", {}).get("__html")
                    if pointer != root_schema or current_record != owner:
                        return None
                    return ["$", "$Lfffd", value[2], {}]
                if len(value) == 4 and value[:2] == ["$", "$Lfffd"]:
                    return value
                return [visit(v) for v in value]
            if isinstance(value, dict):
                result = {k: visit(v) for k, v in value.items()}
                return result
            return value
        output = []
        for key, kind, value in rows:
            current_record = key
            if key in schema_keys:
                # Remove disconnected historical schema data as well.
                value = graph
            elif kind == "J":
                value = visit(value)
            elif kind == "T":
                value = text(value)
            output.append((key, kind, value))
        if not any(key == "fffd" for key, _, _ in output):
            output.append(("fffd", "R", 'I[987655,["/_next/static/chunks/getvout-seo.js"],"default"]'))
        return encode(output)
    doc = html.document_fromstring(path.read_text())
    head = doc.find("head")
    for node in list(head):
        if node.tag in {"title", "meta", "link"} and (
            node.tag == "title" or
            (node.tag == "meta" and not node.get("charset") and node.get("name") not in {"viewport", "theme-color"}) or
            (node.tag == "link" and node.get("rel") in {"canonical", "alternate", "manifest", "icon", "apple-touch-icon"})
        ):
            head.remove(node)
    for tag, props, content in entries:
        node = etree.SubElement(head, tag, props)
        node.text = content
    schema_nodes = doc.xpath('//script[@type="application/ld+json"]')
    if schema_nodes:
        schema_nodes[0].text = graph
        for node in schema_nodes[1:]:
            node.getparent().remove(node)
    else:
        schema_node = etree.SubElement(head, "script", {"type": "application/ld+json"})
        schema_node.text = graph
    pushes, chunks = [], []
    for script in doc.xpath("//script"):
        match = re.fullmatch(r"self\.__next_f\.push\((.*)\)", script.text or "", re.S)
        if match:
            payload = json.loads(match[1])
            if payload[0] == 1:
                pushes.append(script)
                chunks.append(payload[1])
    if pushes:
        pushes[0].text = "self.__next_f.push(" + json.dumps([1, flight("".join(chunks))], ensure_ascii=False).replace("<", "\\u003c") + ")"
        for node in pushes[1:]:
            node.getparent().remove(node)
    for node in doc.iter():
        if node.tag == "script":
            continue
        if node.text:
            node.text = text(node.text)
        if node.tail:
            node.tail = text(node.tail)
        for key, value in node.attrib.items():
            node.set(key, text(value))
    path.write_text("<!DOCTYPE html>\n" + html.tostring(doc, encoding="unicode", method="html"))
    rsc = path.with_suffix(".rsc")
    rsc.write_text(flight(rsc.read_text()))


def apply():
    media = SOURCE / "img/getvout"
    ImageOps.fit(Image.open(SOURCE / "api/media/file/getvout-jac-creation.jpg").convert("RGB"), (1200, 630)).save(media / "social-site.jpg", quality=90)
    for index in range(len(ARTICLES)):
        ImageOps.fit(Image.open(media / f"journal-{index}.jpg").convert("RGB"), (1200, 630)).save(media / f"social-journal-{index}.jpg", quality=90)
    graphs = {route: schema(route, info) for route, info in PAGES.items()}
    # A shared layout persists during client navigation. A real React component
    # observes the route so rendered JSON-LD stays identical to canonical SSR.
    # This is not a post-hydration DOM replacement.
    (SOURCE / "_next/static/chunks/getvout-seo.js").write_text(
        '(()=>{(globalThis.TURBOPACK||(globalThis.TURBOPACK=[])).push(['
        '"object"==typeof document?document.currentScript:void 0,987655,e=>{'
        'var a=e.i(843476),n=e.i(618566);const graphs=' +
        json.dumps(graphs, ensure_ascii=False, separators=(",", ":")) +
        ';e.s(["default",0,function(){const p=(0,n.usePathname)().replace(/\\/$/,"");'
        'const graph=graphs[p];return graph?(0,a.jsx)("script",{type:"application/ld+json",'
        'dangerouslySetInnerHTML:{__html:graph}}):null}])}])})();'
    )
    for route, info in PAGES.items():
        apply_page(route, info)
    (SOURCE / "index.html").write_bytes((SOURCE / "en/index.html").read_bytes())
    # Keep reusable editorial fragments aligned with the approved publication.
    for path in (ROOT / "journal-content").glob("*.html"):
        text = path.read_text().replace(OLD_DISCLOSURE, DISCLOSURE)
        path.write_text(text)
    # No guessed lastmod: only approved publication dates for the reviewed posts.
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    tree = ET.Element(ns + "urlset")
    for route, info in PAGES.items():
        if route in NOINDEX:
            continue
        node = ET.SubElement(tree, ns + "url")
        ET.SubElement(node, ns + "loc").text = ORIGIN + route
        if "article" in info:
            ET.SubElement(node, ns + "lastmod").text = CONFIG["publicationDate"]
    ET.ElementTree(tree).write(SOURCE / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    print(f"Updated {len(PAGES)} pages; {len(PAGES) - len(NOINDEX)} indexable canonical URLs.")


if __name__ == "__main__":
    apply()
