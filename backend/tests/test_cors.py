import unittest

from tests.base import AppTestCase


class CorsDefaultTests(AppTestCase):
    def test_no_cors_headers_by_default(self):
        r = self.client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
        self.assertNotIn("Access-Control-Allow-Origin", r.headers)


class CorsConfiguredTests(AppTestCase):
    frontend_origins = ("http://localhost:5173",)

    def test_allowed_origin_is_echoed_not_wildcard(self):
        r = self.client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://localhost:5173")
        self.assertNotEqual(r.headers["Access-Control-Allow-Origin"], "*")
        self.assertIn("Origin", r.headers["Vary"])

    def test_other_origin_gets_nothing(self):
        r = self.client.get("/api/v1/health", headers={"Origin": "http://evil.example"})
        self.assertNotIn("Access-Control-Allow-Origin", r.headers)

    def test_preflight_allows_x_actor_for_allowed_origin(self):
        r = self.client.options("/api/v1/health", headers={
            "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-actor,content-type"})
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://localhost:5173")
        self.assertIn("X-Actor", r.headers["Access-Control-Allow-Headers"])

    def test_preflight_from_other_origin_gets_nothing(self):
        r = self.client.options("/api/v1/health", headers={
            "Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
        self.assertNotIn("Access-Control-Allow-Origin", r.headers)


if __name__ == "__main__":
    unittest.main()
