import unittest

from tests.base import AppTestCase


class HealthAndErrorTests(AppTestCase):
    def test_health_ok(self):
        r = self.client.get("/api/v1/health")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()["data"]
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["connector"], "synthetic")
        self.assertEqual(data["database"], "ok")
        self.assertFalse(data["demo_mode"])

    def test_unknown_route_uses_error_envelope(self):
        r = self.client.get("/api/v1/nope")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()["error"]["code"], "NOT_FOUND")

    def test_wrong_method_uses_error_envelope(self):
        r = self.client.post("/api/v1/health")
        self.assertEqual(r.status_code, 405)
        self.assertEqual(r.get_json()["error"]["code"], "METHOD_NOT_ALLOWED")

    def test_unhandled_exception_hides_internals(self):
        @self.app.get("/boom")
        def boom():
            raise RuntimeError("secret internals")
        with self.assertLogs(self.app.logger, level="ERROR"):
            r = self.client.get("/boom")
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.get_json()["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("secret internals", r.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
