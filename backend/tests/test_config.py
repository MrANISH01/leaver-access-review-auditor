import unittest

from app import create_app
from app.config import Config, ConfigError, validate_bind_host


class ConfigTests(unittest.TestCase):
    def test_defaults_are_safe(self):
        cfg = Config.from_env({})
        self.assertFalse(cfg.demo_mode)
        self.assertEqual(cfg.frontend_origins, ())      # no CORS by default
        self.assertEqual(cfg.connector, "synthetic")

    def test_origin_is_normalised_and_comma_separated(self):
        cfg = Config.from_env({"FRONTEND_ORIGIN": "http://localhost:5173/, https://demo.example"})
        self.assertEqual(cfg.frontend_origins, ("http://localhost:5173", "https://demo.example"))
        cfg.validate()

    def test_wildcard_origin_rejected(self):
        with self.assertRaises(ConfigError):
            Config.from_env({"FRONTEND_ORIGIN": "*"}).validate()

    def test_malformed_origin_rejected(self):
        for bad in ("localhost:5173", "http://localhost:5173/app", "http://*.example.com"):
            with self.subTest(origin=bad), self.assertRaises(ConfigError):
                Config.from_env({"FRONTEND_ORIGIN": bad}).validate()

    def test_unknown_connector_rejected(self):
        with self.assertRaises(ConfigError):
            Config(connector="nope").validate()

    def test_mock_admin_fails_loudly_until_implemented(self):
        with self.assertRaises(ConfigError) as ctx:
            create_app(Config(connector="mock_admin"))
        self.assertIn("not implemented", str(ctx.exception))

    def test_demo_mode_refuses_non_loopback_bind(self):
        with self.assertRaises(ConfigError):
            validate_bind_host("0.0.0.0", demo_mode=True, allow_lan=False)
        validate_bind_host("127.0.0.1", demo_mode=True, allow_lan=False)
        validate_bind_host("0.0.0.0", demo_mode=True, allow_lan=True)
        validate_bind_host("0.0.0.0", demo_mode=False, allow_lan=False)


if __name__ == "__main__":
    unittest.main()
