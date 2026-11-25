"""Production enquiry delivery through Resend; standard library only.

No passwords or API keys are sent to the client. No automatic replies are sent
to visitor-controlled addresses. Failed requests never return success.
"""
from collections import deque
from datetime import datetime, timezone
import hashlib
import hmac
from html import escape
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
import uuid

RECIPIENT = "hello@getvout.com"
HOSTS = {"getvout.com", "www.getvout.com"}
ORIGINS = {"https://" + host for host in HOSTS}
PROJECTS = {
    "website": "Website", "shop": "Online shop",
    "software": "Custom software / app", "branding": "Brand & logo",
    "automation": "Workflow automation", "ai": "AI assistant",
    "unsure": "Not sure yet",
}
BUDGETS = {
    "b1": "A focused project", "b2": "A complete build",
    "b3": "A larger initiative", "b4": "An ongoing partnership",
    "open": "Let's discuss",
}
TIMELINES = {
    "asap": "As soon as possible", "quarter": "In the next three months",
    "year": "This year", "flex": "Flexible",
}
MODULES = {
    "booking": "Online booking", "cms": "Content management",
    "automation": "Automations", "payment": "Online payment",
    "languages": "Multilingual", "reviews": "Google reviews",
    "newsletter": "Newsletter", "analytics": "Cookie-free analytics",
    "chat": "AI chat",
}
EMAIL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}$")
MAX_BODY = 24000
_buckets = {}
_lock = threading.Lock()


class EnquiryError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


def configuration():
    key = os.environ.get("RESEND_API_KEY", "").strip()
    sender = os.environ.get("ENQUIRY_FROM", "getvout <contact@getvout.com>").strip()
    if not key or "\n" in key or "\r" in key:
        raise EnquiryError(503, "Email delivery is temporarily unavailable. Please email hello@getvout.com directly.")
    address = sender[sender.find("<") + 1:-1] if "<" in sender and sender.endswith(">") else sender
    if not EMAIL.fullmatch(address) or address.rsplit("@", 1)[-1].lower() != "getvout.com" or any(c in sender for c in "\r\n"):
        raise EnquiryError(503, "Email delivery is temporarily unavailable. Please email hello@getvout.com directly.")
    return key, sender


def require_production(headers):
    host = headers.get("Host", "").lower()
    if os.environ.get("VERCEL_ENV") != "production" or host not in HOSTS:
        raise EnquiryError(403, "This preview does not send enquiries. Please use getvout.com or email hello@getvout.com.")
    if headers.get("Origin", "") not in ORIGINS:
        raise EnquiryError(403, "Please submit this form directly from getvout.com.")


def token(key):
    # Fractional issue time keeps the one-second minimum verifiable without
    # depending on whole-second truncation.
    value = f"{time.time():.3f}_{uuid.uuid4().hex}"
    signature = hmac.new(key.encode(), value.encode(), hashlib.sha256).hexdigest()
    return value + "." + signature


def verify_token(value, key):
    if not isinstance(value, str) or len(value) > 160:
        return False
    try:
        unsigned, signature = value.rsplit(".", 1)
        issued, nonce = unsigned.split("_")
        age = time.time() - float(issued)
        expected = hmac.new(key.encode(), unsigned.encode(), hashlib.sha256).hexdigest()
        return (re.fullmatch(r"[0-9]{10,}\.[0-9]{3}", issued) is not None
                and re.fullmatch(r"[0-9a-f]{32}", nonce) is not None
                and 1 <= age <= 7200 and hmac.compare_digest(signature, expected))
    except (ValueError, TypeError):
        return False


def validate(data, key):
    if not isinstance(data, dict):
        raise EnquiryError(400, "Please check the form and try again.")
    if not verify_token(data.get("token"), key):
        raise EnquiryError(400, "This form session expired or is not ready. Please try submitting again.")
    if data.get("website"):
        raise EnquiryError(400, "We could not accept this submission. Please email hello@getvout.com.")
    if data.get("kind") not in {"contact", "project"}:
        raise EnquiryError(400, "Please use one of our enquiry forms.")
    fields = {}
    limits = {"name": 120, "email": 254, "phone": 80, "company": 200,
              "existingSite": 1000, "message": 8000}
    for field, limit in limits.items():
        value = data.get(field, "")
        if not isinstance(value, str) or len(value) > limit:
            raise EnquiryError(400, f"Please shorten or check the {field} field.")
        value = value.strip()
        if any(ord(c) < 32 and c not in "\r\n\t" for c in value):
            raise EnquiryError(400, "Please remove unsupported characters.")
        if field != "message" and any(c in value for c in "\r\n"):
            raise EnquiryError(400, f"Please check the {field} field.")
        fields[field] = value
    if not fields["name"] or not fields["message"] or not EMAIL.fullmatch(fields["email"]):
        raise EnquiryError(400, "Please provide your name, a valid email address and a message.")
    for field, choices in (("projectType", PROJECTS), ("modules", MODULES)):
        values = data.get(field, [])
        if not isinstance(values, list) or len(values) > len(choices) or any(not isinstance(v, str) or v not in choices for v in values):
            raise EnquiryError(400, "Please check your service selections.")
        fields[field] = list(dict.fromkeys(values))
    for field, choices in (("budget", BUDGETS), ("timeline", TIMELINES)):
        value = data.get(field, "")
        if not isinstance(value, str) or value and value not in choices:
            raise EnquiryError(400, "Please check your project preferences.")
        fields[field] = value
    try:
        fields["submissionId"] = str(uuid.UUID(data.get("submissionId", "")))
        submitted = datetime.fromisoformat(data.get("submittedAt", "").replace("Z", "+00:00"))
        if submitted.tzinfo is None or abs((datetime.now(timezone.utc) - submitted).total_seconds()) > 86400:
            raise ValueError("timestamp out of range")
        fields["submittedAt"] = submitted.isoformat()
    except (ValueError, TypeError, AttributeError):
        raise EnquiryError(400, "Please refresh this form and try again.")
    fields["kind"] = data["kind"]
    return fields


def check_rate(headers, key):
    # Best-effort instance-local limit, not a substitute for an edge/WAF limit.
    # Prefer Vercel's own client-IP header; a single shared bucket would throttle
    # every visitor if the header were ever absent.
    address = ""
    for name in ("X-Vercel-Forwarded-For", "X-Real-IP", "X-Forwarded-For"):
        address = headers.get(name, "").split(",")[0].strip()
        if address:
            break
    if not address:
        address = "unknown"
    digest = hmac.new(key.encode(), address.encode(), hashlib.sha256).hexdigest()
    now = time.monotonic()
    with _lock:
        for old in list(_buckets):
            if not _buckets[old] or now - _buckets[old][-1] > 600:
                del _buckets[old]
        bucket = _buckets.setdefault(digest, deque())
        while bucket and now - bucket[0] > 600:
            bucket.popleft()
        if len(bucket) >= 10 or len(_buckets) > 5000:
            raise EnquiryError(429, "Too many attempts. Please wait a few minutes or email hello@getvout.com.")
        bucket.append(now)


def email_payload(fields, sender):
    project = fields["kind"] == "project"
    rows = [
        ("Form", "Start a project" if project else "Contact"),
        ("Name", fields["name"]), ("Email", fields["email"]),
        ("Phone", fields["phone"] or "Not provided"),
    ]
    if project:
        rows += [
            ("Company", fields["company"] or "Not provided"),
            ("Project types", ", ".join(PROJECTS[v] for v in fields["projectType"]) or "Not selected"),
            ("Existing website", fields["existingSite"] or "Not provided"),
            ("Project scope", BUDGETS.get(fields["budget"], "Not selected")),
            ("Timeline", TIMELINES.get(fields["timeline"], "Not selected")),
            ("Requested add-ons", ", ".join(MODULES[v] for v in fields["modules"]) or "None selected"),
        ]
    rows += [
        ("Message", fields["message"]),
        ("Source", "https://getvout.com/en/" + ("start-project" if project else "contact")),
        ("Submitted at (browser clock)", fields["submittedAt"]),
        ("Reference", fields["submissionId"]),
    ]
    plain = "\n\n".join(label + ":\n" + value for label, value in rows)
    body = "".join(
        '<tr><th style="text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #ddd">'
        + escape(label) + '</th><td style="padding:12px;border-bottom:1px solid #ddd;white-space:pre-wrap;overflow-wrap:anywhere">'
        + escape(value) + "</td></tr>" for label, value in rows
    )
    return {
        "from": sender, "to": [RECIPIENT], "reply_to": fields["email"],
        "subject": ("New project brief" if project else "New contact enquiry") + " | getvout | " + fields["name"],
        "text": plain,
        "html": '<!doctype html><html><body><h1>New getvout enquiry</h1><table style="border-collapse:collapse;font:15px/1.5 Arial,sans-serif">'
                + body + "</table></body></html>",
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def send(fields, key, sender):
    payload = email_payload(fields, sender)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    # Same reference + same content produces the same request on safe retries.
    identity = hashlib.sha256(encoded).hexdigest()
    request = urllib.request.Request(
        "https://api.resend.com/emails", data=encoded, method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "User-Agent": "getvout-enquiries/1.0",
                 "Idempotency-Key": "getvout-enquiry/" + fields["submissionId"] + "/" + identity},
    )
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=10) as response:
            result = json.loads(response.read(64000))
            if response.status != 200 or not isinstance(result, dict) or not isinstance(result.get("id"), str) or not result["id"]:
                raise ValueError("No provider receipt")
            return result["id"]
    except urllib.error.HTTPError as error:
        # Status only: provider error bodies and visitor content stay out of logs.
        print("enquiry delivery rejected: HTTP " + str(error.code), flush=True)
        raise EnquiryError(502, "We could not confirm your enquiry. Please try again or email hello@getvout.com. Your form has not been cleared.")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError):
        # Never print provider responses: they may contain PII/configuration.
        print("enquiry delivery could not be confirmed", flush=True)
        raise EnquiryError(502, "We could not confirm your enquiry. Please try again or email hello@getvout.com. Your form has not been cleared.")
