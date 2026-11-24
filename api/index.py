"""Vercel adapter for the same page/RSC routing used in the local preview."""
from pathlib import Path
import serve

serve.ROOT = Path(__file__).resolve().parents[1] / "site-source"


class handler(serve.PreviewHandler):
    def __init__(self, *args, **kwargs):
        kwargs["directory"] = str(serve.ROOT)
        super().__init__(*args, **kwargs)
