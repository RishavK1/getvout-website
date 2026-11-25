"""Tests for enquiry validation, Resend delivery and the production endpoint.

No test contacts Resend or any other network service. Delivery is mocked.
"""
from datetime import datetime, timezone
import http.client
import json
import os
import threading
import time
import unittest
import urllib.error
from http.server import ThreadingHTTPServer
from unittest import mock

import enquiries
import serve

KEY = "test-resend-key"
SENDER = "getvout <contact@getvout.com>"


def payload(**overrides):
    data = {
        "kind": "project", "name": "Ada Lovelace", "email": "ada@example.com",
        "phone": "+44 20 0000 0000", "company": "Analytical Engines",
        "existingSite": "https://example.com", "message": "A new site.\nTwo lines.",
        "website": "", "projectType": ["website", "automation"],
        "budget": "b2", "timeline": "quarter", "modules": ["cms", "payment"],
        "submissionId": "6f1c2f7e-3d5a-4c8b-9a11-2b3c4d5e6f70",
        "submittedAt": datetime.now(timezone.utc).isoformat(),
        "token": "",
    }
    data.update(overrides)
    return data


def aged_token(age=2):
    """Sign a token as if it had been issued `age` seconds ago."""
    with mock.patch("enquiries.time.time", return_value=time.time() - age):
        return enquiries.token(KEY)


class FakeResponse:
    def __init__(self, body, status=200):
        self.body, self.status = body, status

    def read(self, amount=-1):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.request, self.timeout = response, error, None, None

    def open(self, request, timeout=None):
        self.request, self.timeout = request, timeout
        if self.error:
            raise self.error
        return self.response


class Base(unittest.TestCase):
    def setUp(self):
        enquiries._buckets.clear()
        env = mock.patch.dict(os.environ, {"RESEND_API_KEY": KEY, "VERCEL_ENV": "production"}, clear=False)
        env.start()
        self.addCleanup(env.stop)

    def valid(self, **overrides):
        overrides.setdefault("token", aged_token())
        return enquiries.validate(payload(**overrides), KEY)


class TokenTests(Base):
    def test_aged_token_verifies(self):
        self.assertTrue(enquiries.verify_token(aged_token(2), KEY))

    def test_token_needs_a_real_delay(self):
        self.assertFalse(enquiries.verify_token(aged_token(0.2), KEY))

    def test_expired_token_fails(self):
        self.assertFalse(enquiries.verify_token(aged_token(7300), KEY))

    def test_tampered_token_fails(self):
        value = aged_token(2)
        unsigned, signature = value.rsplit(".", 1)
        self.assertFalse(enquiries.verify_token(unsigned + "." + "0" * 64, KEY))
        self.assertFalse(enquiries.verify_token(unsigned + "." + signature[:-1] + "0", KEY))
        self.assertFalse(enquiries.verify_token("not-a-token", KEY))
        self.assertFalse(enquiries.verify_token(value, "another-key"))


class ValidationTests(Base):
    def test_complete_project_is_accepted(self):
        fields = self.valid()
        self.assertEqual(fields["name"], "Ada Lovelace")
        self.assertEqual(fields["projectType"], ["website", "automation"])
        self.assertEqual(fields["modules"], ["cms", "payment"])
        self.assertEqual(fields["budget"], "b2")
        self.assertEqual(fields["kind"], "project")

    def test_duplicate_selections_are_collapsed(self):
        fields = self.valid(projectType=["website", "website", "shop"])
        self.assertEqual(fields["projectType"], ["website", "shop"])

    def test_contact_needs_no_project_fields(self):
        fields = self.valid(kind="contact", projectType=[], modules=[], budget="", timeline="")
        self.assertEqual(fields["kind"], "contact")
        self.assertEqual(fields["modules"], [])

    def test_required_fields(self):
        for change in ({"name": ""}, {"email": ""}, {"message": ""}, {"email": "not-an-email"}):
            with self.subTest(change=change), self.assertRaises(enquiries.EnquiryError) as caught:
                self.valid(**change)
            self.assertEqual(caught.exception.status, 400)

    def test_honeypot_is_rejected(self):
        with self.assertRaises(enquiries.EnquiryError) as caught:
            self.valid(website="https://spam.example")
        self.assertEqual(caught.exception.status, 400)

    def test_unknown_choices_are_rejected(self):
        for change in ({"projectType": ["crypto"]}, {"modules": ["ads"]},
                       {"budget": "b9"}, {"timeline": "yesterday"}, {"kind": "other"}):
            with self.subTest(change=change), self.assertRaises(enquiries.EnquiryError):
                self.valid(**change)

    def test_oversized_fields_are_rejected(self):
        with self.assertRaises(enquiries.EnquiryError):
            self.valid(message="x" * 8001)
        with self.assertRaises(enquiries.EnquiryError):
            self.valid(name="x" * 121)

    def test_header_injection_is_rejected(self):
        with self.assertRaises(enquiries.EnquiryError):
            self.valid(name="Ada\r\nBcc: victim@example.com")

    def test_reference_and_timestamp_are_validated(self):
        with self.assertRaises(enquiries.EnquiryError):
            self.valid(submissionId="not-a-uuid")
        with self.assertRaises(enquiries.EnquiryError):
            self.valid(submittedAt="2020-01-01T00:00:00+00:00")
        with self.assertRaises(enquiries.EnquiryError):
            self.valid(submittedAt="not-a-time")

    def test_non_object_is_rejected(self):
        with self.assertRaises(enquiries.EnquiryError):
            enquiries.validate([], KEY)


class MessageTests(Base):
    def test_every_answer_is_included(self):
        fields = self.valid(message="Please build <b>this</b> & that.")
        message = enquiries.email_payload(fields, SENDER)
        self.assertEqual(message["to"], ["hello@getvout.com"])
        self.assertEqual(message["reply_to"], "ada@example.com")
        self.assertEqual(message["from"], SENDER)
        self.assertIn("New project brief", message["subject"])
        for expected in ("Ada Lovelace", "ada@example.com", "+44 20 0000 0000", "Analytical Engines",
                         "https://example.com", "Website, Workflow automation", "A complete build",
                         "In the next three months", "Content management, Online payment",
                         "Please build <b>this</b> & that.", "https://getvout.com/en/start-project",
                         "6f1c2f7e-3d5a-4c8b-9a11-2b3c4d5e6f70"):
            self.assertIn(expected, message["text"])
        self.assertIn("&lt;b&gt;this&lt;/b&gt; &amp; that.", message["html"])
        self.assertNotIn("<b>this</b>", message["html"])

    def test_contact_message_has_no_project_answers(self):
        fields = self.valid(kind="contact", projectType=[], modules=[], budget="", timeline="")
        message = enquiries.email_payload(fields, SENDER)
        self.assertIn("New contact enquiry", message["subject"])
        self.assertIn("https://getvout.com/en/contact", message["text"])
        self.assertNotIn("Project types", message["text"])


class DeliveryTests(Base):
    def open_with(self, opener):
        return mock.patch("enquiries.urllib.request.build_opener", return_value=opener)

    def test_request_is_signed_and_idempotent(self):
        opener = FakeOpener(FakeResponse(b'{"id":"provider-123"}'))
        with self.open_with(opener):
            receipt = enquiries.send(self.valid(), KEY, SENDER)
        self.assertEqual(receipt, "provider-123")
        request = opener.request
        self.assertEqual(request.full_url, "https://api.resend.com/emails")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer " + KEY)
        self.assertTrue(request.get_header("Idempotency-key").startswith("getvout-enquiry/6f1c2f7e"))
        self.assertLessEqual(opener.timeout, 10)
        body = json.loads(request.data)
        self.assertEqual(body["reply_to"], "ada@example.com")
        self.assertEqual(body["to"], ["hello@getvout.com"])

    def test_provider_rejection_is_not_success(self):
        error = urllib.error.HTTPError("https://api.resend.com/emails", 403, "Forbidden", {}, None)
        with self.open_with(FakeOpener(error=error)), self.assertRaises(enquiries.EnquiryError) as caught:
            enquiries.send(self.valid(), KEY, SENDER)
        self.assertEqual(caught.exception.status, 502)

    def test_missing_receipt_is_not_success(self):
        for body in (b'{"id":""}', b"{}", b"not json"):
            with self.subTest(body=body), self.open_with(FakeOpener(FakeResponse(body))), \
                    self.assertRaises(enquiries.EnquiryError) as caught:
                enquiries.send(self.valid(), KEY, SENDER)
            self.assertEqual(caught.exception.status, 502)

    def test_configuration_requires_a_getvout_sender(self):
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": ""}):
            with self.assertRaises(enquiries.EnquiryError) as caught:
                enquiries.configuration()
            self.assertEqual(caught.exception.status, 503)
        with mock.patch.dict(os.environ, {"ENQUIRY_FROM": "getvout <hello@example.com>"}):
            with self.assertRaises(enquiries.EnquiryError):
                enquiries.configuration()
        with mock.patch.dict(os.environ, {"ENQUIRY_FROM": "getvout <contact@getvout.com>\r\nBcc: x@example.com>"}):
            with self.assertRaises(enquiries.EnquiryError):
                enquiries.configuration()
        key, sender = enquiries.configuration()
        self.assertEqual(key, KEY)
        self.assertEqual(sender, SENDER)

    def test_production_gate(self):
        headers = {"Host": "getvout.com", "Origin": "https://getvout.com"}
        enquiries.require_production(headers)
        enquiries.require_production({"Host": "www.getvout.com", "Origin": "https://www.getvout.com"})
        with mock.patch.dict(os.environ, {"VERCEL_ENV": "preview"}):
            with self.assertRaises(enquiries.EnquiryError):
                enquiries.require_production(headers)
        for change in ({"Host": "localhost:3000"}, {"Origin": "https://evil.example"}):
            with self.subTest(change=change), self.assertRaises(enquiries.EnquiryError):
                enquiries.require_production({**headers, **change})


class RateLimitTests(Base):
    def test_ten_attempts_then_limited(self):
        headers = {"X-Vercel-Forwarded-For": "203.0.113.7"}
        for _ in range(10):
            enquiries.check_rate(headers, KEY)
        with self.assertRaises(enquiries.EnquiryError) as caught:
            enquiries.check_rate(headers, KEY)
        self.assertEqual(caught.exception.status, 429)
        enquiries.check_rate({"X-Vercel-Forwarded-For": "203.0.113.8"}, KEY)

    def test_forwarded_for_is_a_fallback(self):
        headers = {"X-Forwarded-For": "198.51.100.4, 10.0.0.1"}
        for _ in range(10):
            enquiries.check_rate(headers, KEY)
        with self.assertRaises(enquiries.EnquiryError):
            enquiries.check_rate(headers, KEY)


class QuietHandler(serve.PreviewHandler):
    def log_message(self, *args):
        pass


class EndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        enquiries._buckets.clear()
        self.sent = []
        env = mock.patch.dict(os.environ, {"RESEND_API_KEY": KEY, "VERCEL_ENV": "production"}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        send = mock.patch.object(enquiries, "send", side_effect=lambda fields, key, sender: self.sent.append(fields) or "provider-id")
        send.start()
        self.addCleanup(send.stop)

    def request(self, method, path, body=None, headers=None, host="getvout.com"):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        connection.putrequest(method, path, skip_host=True)
        connection.putheader("Host", host)
        for name, value in (headers or {}).items():
            connection.putheader(name, value)
        if body is not None:
            connection.putheader("Content-Length", str(len(body)))
        connection.endheaders(body)
        response = connection.getresponse()
        raw = response.read()
        connection.close()
        return response.status, json.loads(raw or b"{}")

    def token(self):
        status, result = self.request("GET", "/api/enquiry")
        self.assertEqual(status, 200)
        self.assertTrue(result["token"])
        # The endpoint issues tokens that become valid after one second.
        time.sleep(1.05)
        return result["token"]

    def test_token_and_submission(self):
        token = self.token()
        body = json.dumps(payload(token=token)).encode()
        status, result = self.request("POST", "/api/enquiry", body, {
            "Content-Type": "application/json", "Origin": "https://getvout.com",
            "X-Vercel-Forwarded-For": "203.0.113.9"})
        self.assertEqual(status, 200, result)
        self.assertTrue(result["ok"])
        self.assertEqual(result["reference"], payload()["submissionId"])
        self.assertIn("6f1c2f7e", result["message"])
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["name"], "Ada Lovelace")
        self.assertEqual(self.sent[0]["modules"], ["cms", "payment"])

    def test_preview_never_sends(self):
        with mock.patch.dict(os.environ, {"VERCEL_ENV": "preview"}):
            status, result = self.request("GET", "/api/enquiry")
            self.assertEqual(status, 403)
            body = json.dumps(payload(token=aged_token())).encode()
            status, result = self.request("POST", "/api/enquiry", body, {
                "Content-Type": "application/json", "Origin": "https://getvout.com"})
        self.assertEqual(status, 403)
        self.assertFalse(result["ok"])
        self.assertEqual(self.sent, [])

    def test_wrong_origin_is_rejected(self):
        body = json.dumps(payload(token=aged_token())).encode()
        status, _ = self.request("POST", "/api/enquiry", body, {
            "Content-Type": "application/json", "Origin": "https://evil.example"})
        self.assertEqual(status, 403)
        self.assertEqual(self.sent, [])

    def test_content_type_and_size_are_enforced(self):
        body = json.dumps(payload(token=aged_token())).encode()
        status, _ = self.request("POST", "/api/enquiry", body, {
            "Content-Type": "text/plain", "Origin": "https://getvout.com"})
        self.assertEqual(status, 415)
        oversized = b"{" + b" " * enquiries.MAX_BODY + b"}"
        status, _ = self.request("POST", "/api/enquiry", oversized, {
            "Content-Type": "application/json", "Origin": "https://getvout.com"})
        self.assertEqual(status, 413)
        self.assertEqual(self.sent, [])

    def test_honeypot_and_duplicate_clicks(self):
        token = self.token()
        body = json.dumps(payload(token=token, website="spam")).encode()
        status, _ = self.request("POST", "/api/enquiry", body, {
            "Content-Type": "application/json", "Origin": "https://getvout.com"})
        self.assertEqual(status, 400)
        self.assertEqual(self.sent, [])
        # An identical retry is delivered once by Resend because both requests
        # carry the same Idempotency-Key; here the endpoint itself stays callable.
        body = json.dumps(payload(token=token)).encode()
        for _ in range(2):
            status, result = self.request("POST", "/api/enquiry", body, {
                "Content-Type": "application/json", "Origin": "https://getvout.com"})
            self.assertEqual(status, 200, result)
        self.assertEqual(len(self.sent), 2)


if __name__ == "__main__":
    unittest.main()
