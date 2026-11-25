"""Offline regression tests for the production-only regional analytics policy."""
import os
import unittest
from unittest.mock import patch
from pathlib import Path
import serve


class AnalyticsTests(unittest.TestCase):
    def test_regional_policy(self):
        with patch.dict(os.environ, {"VERCEL_ENV": "production"}):
            for country in serve.CONSENT_COUNTRIES | {"", "XX", "ZZ", "INVALID"}:
                self.assertEqual(serve.analytics_policy({"Host": "getvout.com",
                    "X-Vercel-IP-Country": country}), {"active": True, "consentRequired": True})
            for country in ("IN", "US", "AU"):
                self.assertEqual(serve.analytics_policy({"Host": "getvout.com",
                    "X-Vercel-IP-Country": country}), {"active": True, "consentRequired": False})

    def test_previews_disabled(self):
        with patch.dict(os.environ, {"VERCEL_ENV": "preview"}):
            self.assertFalse(serve.analytics_policy({"Host": "getvout.com"})["active"])
        with patch.dict(os.environ, {"VERCEL_ENV": "production"}):
            for host in ("localhost", "getvout-website.vercel.app", "getvout.com.attacker.com"):
                self.assertFalse(serve.analytics_policy({"Host": host})["active"])

    def test_one_local_loader_per_page(self):
        for path in (Path(__file__).parent / "site-source").rglob("*.html"):
            text = path.read_text()
            if "</head>" not in text:
                continue
            self.assertEqual(text.count('src="/analytics-consent.js"'), 1, str(path))
            self.assertNotIn("GTM-P68LKSCW", text)
            self.assertNotIn('src="https://www.googletagmanager.com', text)


if __name__ == "__main__":
    unittest.main()
