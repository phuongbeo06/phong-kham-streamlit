import importlib
import sys
import types
import unittest
from unittest.mock import patch


class FakeMySQLError(Exception):
    pass


class FakeCursor:
    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at
        self.lastrowid = 42

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, args=()):
        self.calls.append((sql, args))
        if len(self.calls) == self.fail_at:
            raise FakeMySQLError(1451, "related record")


class FakeConnection:
    def __init__(self, fail_at=None):
        self.current_cursor = FakeCursor(fail_at)
        self.begins = self.commits = self.rollbacks = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self.current_cursor

    def begin(self):
        self.begins += 1

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def import_db_without_external_packages():
    pymysql = types.ModuleType("pymysql")
    pymysql.MySQLError = FakeMySQLError
    pymysql.cursors = types.ModuleType("pymysql.cursors")
    pymysql.cursors.DictCursor = object
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None
    with patch.dict(sys.modules, {"pymysql": pymysql, "pymysql.cursors": pymysql.cursors, "dotenv": dotenv}):
        sys.modules.pop("db", None)
        return importlib.import_module("db")


class StaffTransactionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = import_db_without_external_packages()

    def test_add_doctor_commits_both_rows_together(self):
        conn = FakeConnection()
        with patch.object(self.db, "get_connection", return_value=conn):
            ok, staff_id, error = self.db.add_doctor("BS004", "123456789012", "A", "1980-01-01", "", "", 2, "I", "ĐH", "Nội")
        self.assertEqual((ok, staff_id, error), (True, 42, None))
        self.assertEqual((conn.begins, conn.commits, conn.rollbacks), (1, 1, 0))

    def test_add_nurse_rolls_back_if_second_insert_fails(self):
        conn = FakeConnection(fail_at=2)
        with patch.object(self.db, "get_connection", return_value=conn):
            ok, _, _ = self.db.add_nurse("YT005", "123456789012", "B", "1990-01-01", "", "", 1, "CĐ")
        self.assertFalse(ok)
        self.assertEqual((conn.begins, conn.commits, conn.rollbacks), (1, 0, 1))

    def test_update_doctor_changes_both_tables_in_one_transaction(self):
        conn = FakeConnection()
        with patch.object(self.db, "get_connection", return_value=conn):
            ok, error = self.db.update_staff(42, "BS", "A", "1980-01-01", "Hà Nội", "0901234567", 3, "I", "ĐH", "Nội")
        self.assertEqual((ok, error), (True, None))
        self.assertEqual((conn.begins, conn.commits, conn.rollbacks), (1, 1, 0))
        self.assertEqual(len(conn.current_cursor.calls), 2)

    def test_delete_staff_rolls_back_when_related_records_exist(self):
        conn = FakeConnection(fail_at=1)
        with patch.object(self.db, "get_connection", return_value=conn):
            ok, error = self.db.delete_staff(42, "BS")
        self.assertFalse(ok)
        self.assertEqual((conn.begins, conn.commits, conn.rollbacks), (1, 0, 1))


if __name__ == "__main__":
    unittest.main()
