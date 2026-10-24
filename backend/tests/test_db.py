import sqlite3
import unittest

from app.db import init_db
from tests.base import AppTestCase

EXPECTED_TABLES = {"employees", "scans", "accounts", "exclusions", "findings", "evidence",
                   "deprovision_requests", "executions", "verifications", "audit_log"}


def _make_finding(db):
    db.execute("INSERT INTO scans (started_at, connector, status) VALUES ('t','synthetic','COMPLETED')")
    db.execute("INSERT INTO accounts (scan_id, system, external_account_id, account_type, status) "
               "VALUES (1,'Slack','S-1','INDIVIDUAL','ACTIVE')")
    db.execute("INSERT INTO findings (scan_id, account_id, classification, created_at) "
               "VALUES (1,1,'LEAVER_ACTIVE','t')")


def _request(db, key, status="PREPARED", action="DISABLE"):
    db.execute("INSERT INTO deprovision_requests (finding_id, system, external_account_id, action, status, "
               "idempotency_key, prepared_by, prepared_at) VALUES (1,'Slack','S-1',?,?,?,'a','t')",
               (action, status, key))


class SchemaTests(AppTestCase):
    def test_all_tables_created(self):
        names = {r[0] for r in self.raw_db().execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue(EXPECTED_TABLES <= names)

    def test_init_is_idempotent_and_does_not_wipe_data(self):
        db = self.raw_db()
        db.execute("INSERT INTO employees VALUES ('E1','A','a@x','ACTIVE',NULL,NULL)")
        db.commit()
        init_db(self.db_path)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM employees").fetchone()[0], 1)

    def test_audit_log_is_append_only(self):
        db = self.raw_db()
        db.execute("INSERT INTO audit_log (ts, actor, event, entity_type, entity_id) VALUES ('t','a','E','x','1')")
        db.commit()
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("UPDATE audit_log SET actor='b'")
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("DELETE FROM audit_log")

    def test_only_disable_action_can_be_stored(self):
        db = self.raw_db()
        _make_finding(db)
        with self.assertRaises(sqlite3.IntegrityError):
            _request(db, "k1", action="DELETE")

    def test_one_open_request_per_finding(self):
        db = self.raw_db()
        _make_finding(db)
        _request(db, "k1")
        with self.assertRaises(sqlite3.IntegrityError):
            _request(db, "k2")

    def test_rejected_request_allows_a_new_one(self):
        db = self.raw_db()
        _make_finding(db)
        _request(db, "k1", status="REJECTED")
        _request(db, "k2")  # must not raise

    def test_idempotency_key_unique(self):
        db = self.raw_db()
        _make_finding(db)
        _request(db, "k1", status="REJECTED")
        with self.assertRaises(sqlite3.IntegrityError):
            _request(db, "k1")

    def test_invalid_classification_rejected(self):
        db = self.raw_db()
        _make_finding(db)
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO findings (scan_id, account_id, classification, created_at) "
                       "VALUES (1,1,'BOGUS','t')")


if __name__ == "__main__":
    unittest.main()
