"""Regression checks for canonical SEO content before deployment."""
import json
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from lxml import html
from PIL import Image
from site_data import records

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "site-source"
CONFIG = json.loads((ROOT / "seo-config.json").read_text())


def metadata_arrays(value):
    if isinstance(value, list):
        if value and all(isinstance(n, list) and len(n) == 4 for n in value) and any(n[:2] == ["$", "title"] for n in value):
            yield value
        for child in value:
            yield from metadata_arrays(child)
    elif isinstance(value, dict):
        for child in value.values():
            yield from metadata_arrays(child)


def flight_metadata(source):
    arrays = []
    for _, kind, value in records(source):
        if kind == "J":
            arrays.extend(metadata_arrays(value))
    return [a for a in arrays if any(n[:2] == ["$", "meta"] and n[3].get("name") == "robots" for n in a)]


class SEOTests(unittest.TestCase):
    def test_all_pages(self):
        titles, descriptions, indexable = [], [], set()
        for path in sorted((SOURCE / "en").glob("**/index.html")):
            route = "/" + str(path.parent.relative_to(SOURCE))
            with self.subTest(route=route):
                doc = html.fromstring(path.read_text())
                title = doc.xpath("//title/text()")
                description = doc.xpath('//meta[@name="description"]/@content')
                canonical = doc.xpath('//link[@rel="canonical"]/@href')
                robots = doc.xpath('//meta[@name="robots"]/@content')
                self.assertEqual(len(title), 1)
                self.assertEqual(len(description), 1)
                self.assertEqual(canonical, [CONFIG["origin"] + route])
                self.assertEqual(len(robots), 1)
                self.assertEqual("noindex" in robots[0], route in CONFIG["noindex"])
                self.assertEqual(doc.xpath('//meta[@name="google-site-verification"]/@content'),
                                 ["UNnS-iB2-2Q0rEg0HKKW2tmBNIlDZ5jHdmdYsWVxGU0"])
                if route not in CONFIG["noindex"]:
                    indexable.add(canonical[0])
                titles += title
                descriptions += description
                scripts = doc.xpath('//script[@type="application/ld+json"]')
                self.assertEqual(len(scripts), 1)
                graph = json.loads(scripts[0].text)["@graph"]
                ids = [node["@id"] for node in graph]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertIn(CONFIG["origin"] + "/#organization", ids)
                self.assertIn(CONFIG["origin"] + "/#website", ids)
                self.assertIn(CONFIG["origin"] + route + "#webpage", ids)
                if route.startswith("/en/services/"):
                    self.assertIn("Service", [n["@type"] for n in graph])
                if route == "/en/contact":
                    self.assertIn("ContactPage", [n["@type"] for n in graph])
                if route.startswith("/en/journal/"):
                    article = next(n for n in graph if n["@type"] == "BlogPosting")
                    self.assertEqual(article["creativeWorkStatus"], "Published")
                    self.assertEqual(article["datePublished"], CONFIG["publicationDate"])
                    self.assertIn("AI-assisted content reviewed by the getvout team", doc.text_content())
                self.assertFalse(doc.xpath('//meta[@property="og:locale:alternate"]'))
                image_url = doc.xpath('//meta[@property="og:image"]/@content')[0]
                self.assertIn("/img/getvout/social-v2/", image_url)
                self.assertEqual(doc.xpath('//meta[@name="twitter:image"]/@content'), [image_url])
                self.assertEqual(doc.xpath('//meta[@property="og:image:secure_url"]/@content'), [image_url])
                local_image = SOURCE / image_url.removeprefix(CONFIG["origin"] + "/")
                with Image.open(local_image) as image:
                    self.assertEqual(image.size, (1200, 630))
                streams = [path.with_suffix(".rsc").read_text()]
                for node in doc.xpath("//script"):
                    match = re.fullmatch(r"self\.__next_f\.push\((.*)\)", node.text or "", re.S)
                    if match:
                        payload = json.loads(match[1])
                        if payload[0] == 1:
                            streams.append(payload[1])
                self.assertEqual(len(streams), 2)
                for stream in streams:
                    arrays = flight_metadata(stream)
                    self.assertEqual(len(arrays), 1)
                    array = arrays[0]
                    self.assertEqual(next(n[3]["children"] for n in array if n[1] == "title"), title[0])
                    self.assertEqual(next(n[3]["content"] for n in array if n[1] == "meta" and n[3].get("name") == "robots"), robots[0])
                    self.assertEqual(next(n[3]["href"] for n in array if n[1] == "link" and n[3].get("rel") == "canonical"), canonical[0])
        self.assertEqual(len(titles), 23)
        self.assertEqual(len(titles), len(set(titles)))
        self.assertEqual(len(descriptions), len(set(descriptions)))
        sitemap = ET.parse(SOURCE / "sitemap.xml")
        urls = [n.text for n in sitemap.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertEqual(len(urls), 20)
        self.assertEqual(set(urls), indexable)

    def test_discovery(self):
        robots = (SOURCE / "robots.txt").read_text()
        self.assertIn("Sitemap: https://getvout.com/sitemap.xml", robots)
        self.assertNotIn("Disallow: /\n", robots)
        self.assertNotIn("Disallow: /_next/image", robots)
        llms = (SOURCE / "llms.txt").read_text()
        self.assertTrue(llms.startswith("# getvout\n"))
        self.assertIn("WhatsApp-only", llms)
        for url in re.findall(r"\]\((https://getvout.com[^)]+)\)", llms):
            target = SOURCE / url.removeprefix("https://getvout.com/")
            self.assertTrue(target.is_file() or (target / "index.html").is_file(), url)


if __name__ == "__main__":
    unittest.main()
