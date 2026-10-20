#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas Unitarias para el Gestor de Migraciones MariaDB (scripts/migrate_db.py)
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.migrate_db import DatabaseMigrator, compute_file_checksum


class TestMigrateDB(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="fluxa_test_migrations_")
        self.migrations_dir = os.path.join(self.test_dir, "migrations")
        self.backup_dir = os.path.join(self.test_dir, "backups")
        os.makedirs(self.migrations_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

        # Crear archivo 001_baseline.sql de prueba
        self.baseline_file = os.path.join(self.migrations_dir, "001_baseline.sql")
        with open(self.baseline_file, "w", encoding="utf-8") as f:
            f.write("""
                CREATE TABLE IF NOT EXISTS traffic_telemetry (id BIGINT AUTO_INCREMENT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS system_events (id BIGINT AUTO_INCREMENT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS red_light_violations (id BIGINT AUTO_INCREMENT PRIMARY KEY);
            """)

        self.migrator = DatabaseMigrator(
            host="localhost",
            port=3306,
            user="fluxa",
            password="test_password",
            database="fluxa_traffic",
            migrations_dir=self.migrations_dir,
            backup_dir=self.backup_dir
        )

    def test_checksum_computation(self):
        checksum1 = compute_file_checksum(self.baseline_file)
        self.assertTrue(len(checksum1) == 64)
        checksum2 = compute_file_checksum(self.baseline_file)
        self.assertEqual(checksum1, checksum2)

    def test_get_available_migrations(self):
        # Agregar una segunda migración 002
        file_002 = os.path.join(self.migrations_dir, "002_add_telemetry_column.sql")
        with open(file_002, "w", encoding="utf-8") as f:
            f.write("ALTER TABLE traffic_telemetry ADD COLUMN extra_metric INT DEFAULT 0;")

        available = self.migrator.get_available_migrations()
        self.assertEqual(len(available), 2)
        self.assertEqual(available[0]["version"], "001_baseline")
        self.assertEqual(available[1]["version"], "002_add_telemetry_column")

    @patch.object(DatabaseMigrator, "get_connection")
    def test_check_status_empty_db_needs_all(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Simular base de datos vacía (sin tablas aplicadas ni schema_migrations)
        mock_cursor.fetchall.side_effect = [
            [],  # get_applied_migrations -> SELECT version... -> vacía
            []   # get_existing_tables -> SHOW TABLES -> vacía
        ]

        status = self.migrator.check_status()
        self.assertFalse(status["up_to_date"])
        self.assertEqual(status["pending_count"], 1)
        self.assertEqual(status["pending"][0]["version"], "001_baseline")
        self.assertEqual(status["pending"][0]["action"], "execute_sql")

    @patch.object(DatabaseMigrator, "get_connection")
    def test_check_status_existing_db_adopts_baseline(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Simular base de datos existente previa con tablas pero sin schema_migrations
        mock_cursor.fetchall.side_effect = [
            [],  # schema_migrations vacía
            [{"Tables_in_fluxa_traffic": "traffic_telemetry"}, {"Tables_in_fluxa_traffic": "red_light_violations"}]
        ]

        status = self.migrator.check_status()
        self.assertFalse(status["up_to_date"])
        self.assertEqual(status["pending_count"], 1)
        self.assertEqual(status["pending"][0]["version"], "001_baseline")
        # Debe adoptar el baseline sin ejecutar DDL redundantes
        self.assertEqual(status["pending"][0]["action"], "adopt_baseline_existing_db")

    @patch.object(DatabaseMigrator, "create_database_snapshot")
    @patch.object(DatabaseMigrator, "check_status")
    @patch.object(DatabaseMigrator, "get_connection")
    def test_run_migrations_executes_and_records(self, mock_get_conn, mock_check_status, mock_snapshot):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        mock_snapshot.return_value = "/tmp/test_backup.sql.gz"

        mock_check_status.return_value = {
            "database": "fluxa_traffic",
            "applied_count": 0,
            "pending_count": 1,
            "pending": [{
                "version": "001_baseline",
                "action": "execute_sql",
                "filepath": self.baseline_file
            }],
            "warnings": [],
            "up_to_date": False
        }

        result = self.migrator.run_migrations(make_backup=True, dry_run=False)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["applied_migrations"]), 1)
        self.assertEqual(result["applied_migrations"][0]["version"], "001_baseline")
        self.assertEqual(result["applied_migrations"][0]["mode"], "executed")
        mock_snapshot.assert_called_once()

    @patch.object(DatabaseMigrator, "check_status")
    def test_run_migrations_already_up_to_date(self, mock_check_status):
        mock_check_status.return_value = {
            "database": "fluxa_traffic",
            "applied_count": 1,
            "pending_count": 0,
            "pending": [],
            "warnings": [],
            "up_to_date": True
        }

        result = self.migrator.run_migrations(make_backup=True, dry_run=False)
        self.assertEqual(result["status"], "up_to_date")
        self.assertEqual(len(result["applied_migrations"]), 0)


if __name__ == "__main__":
    unittest.main()
