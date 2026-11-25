"""Inject the first-party consent loader once; builds remain offline."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def apply():
    for path in (ROOT / "site-source").rglob("*.html"):
        text = path.read_text()
        text = re.sub(r'<script\b[^>]*data-getvout-ga4[^>]*>.*?</script>', '', text, flags=re.S)
        text = text.replace("</head>", '<script data-getvout-ga4="" defer src="/analytics-consent.js"></script></head>')
        path.write_text(text)


if __name__ == "__main__":
    apply()
