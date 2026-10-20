#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas Unitarias para el Migrador y Fusionador de Configuración (scripts/migrate_config.py)
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

# Agregar directorio raíz al PYTHONPATH
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.migrate_config import deep_merge, migrate_config


class TestMigrateConfig(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="fluxa_test_config_")
        self.template_path = os.path.join(self.test_dir, "config.example.json")
        self.current_path = os.path.join(self.test_dir, "config.json")

        self.sample_template = {
            "system": {
                "camera_index": 0,
                "serial_port": "/dev/ttyACM0",
                "log_analytics": True,
                "new_system_flag": "default_value"
            },
            "traffic_light": {
                "tiempo_minimo_verde": 6.0,
                "tiempo_maximo_verde": 40.0,
                "factor_tiempo_por_auto": 2.5
            },
            "zones": {
                "4_way": {
                    "norte": [[0.0, 0.0], [1.0, 1.0]],
                    "sur": [[0.0, 0.5], [1.0, 1.0]]
                },
                "new_topology": {
                    "zona_1": [[0.1, 0.1], [0.9, 0.9]]
                }
            },
            "telemetry": {
                "mqtt_broker": "localhost",
                "mqtt_port": 1883
            }
        }

        with open(self.template_path, "w", encoding="utf-8") as f:
            json.dump(self.sample_template, f, indent=4)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_deep_merge_preserves_custom_values_and_adds_new_keys(self):
        current = {
            "system": {
                "camera_index": 2,  # Personalizado por el usuario
                "serial_port": "/dev/ttyUSB1"
            },
            "traffic_light": {
                "tiempo_minimo_verde": 12.0  # Calibración del cruce
            },
            "zones": {
                "4_way": {
                    "norte": [[0.2, 0.1], [0.8, 0.9]]  # Polígono calibrado
                }
            }
        }

        merged, added, warnings = deep_merge(self.sample_template, current)

        # 1. Valores personalizados deben prevalecer
        self.assertEqual(merged["system"]["camera_index"], 2)
        self.assertEqual(merged["system"]["serial_port"], "/dev/ttyUSB1")
        self.assertEqual(merged["traffic_light"]["tiempo_minimo_verde"], 12.0)
        self.assertEqual(merged["zones"]["4_way"]["norte"], [[0.2, 0.1], [0.8, 0.9]])

        # 2. Claves nuevas de la plantilla deben agregarse
        self.assertIn("log_analytics", merged["system"])
        self.assertTrue(merged["system"]["log_analytics"])
        self.assertEqual(merged["system"]["new_system_flag"], "default_value")
        self.assertEqual(merged["traffic_light"]["tiempo_maximo_verde"], 40.0)
        self.assertIn("sur", merged["zones"]["4_way"])
        self.assertIn("new_topology", merged["zones"])
        self.assertIn("telemetry", merged)
        self.assertEqual(merged["telemetry"]["mqtt_port"], 1883)

        # 3. Comprobar lista de claves añadidas
        self.assertIn("system.log_analytics", added)
        self.assertIn("system.new_system_flag", added)
        self.assertIn("traffic_light.tiempo_maximo_verde", added)
        self.assertIn("zones.4_way.sur", added)
        self.assertIn("zones.new_topology", added)
        self.assertIn("telemetry", added)

    def test_migrate_config_creates_backup_and_updates_atomically(self):
        current_data = {
            "system": {
                "camera_index": 1,
                "serial_port": "/dev/ttyACM0"
            }
        }
        with open(self.current_path, "w", encoding="utf-8") as f:
            json.dump(current_data, f, indent=4)

        result = migrate_config(
            current_path=self.current_path,
            template_path=self.template_path
        )

        self.assertEqual(result["status"], "migrated")
        self.assertTrue(os.path.isfile(result["backup_path"]))

        # Verificar contenido del respaldo (debe ser el original)
        with open(result["backup_path"], "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        self.assertEqual(backup_data, current_data)

        # Verificar archivo actualizado
        with open(self.current_path, "r", encoding="utf-8") as f:
            updated_data = json.load(f)
        self.assertEqual(updated_data["system"]["camera_index"], 1)
        self.assertIn("telemetry", updated_data)

    def test_check_mode(self):
        # 1. Requiere migración
        with open(self.current_path, "w", encoding="utf-8") as f:
            json.dump({"system": {"camera_index": 0}}, f)

        res_check = migrate_config(
            current_path=self.current_path,
            template_path=self.template_path,
            check_only=True
        )
        self.assertEqual(res_check["status"], "needs_migration")
        self.assertTrue(len(res_check["added_keys"]) > 0)

        # 2. Ya está al día
        with open(self.current_path, "w", encoding="utf-8") as f:
            json.dump(self.sample_template, f)

        res_up_to_date = migrate_config(
            current_path=self.current_path,
            template_path=self.template_path,
            check_only=True
        )
        self.assertEqual(res_up_to_date["status"], "up_to_date")
        self.assertEqual(len(res_up_to_date["added_keys"]), 0)

    def test_dry_run_does_not_modify_disk(self):
        with open(self.current_path, "w", encoding="utf-8") as f:
            json.dump({"system": {"camera_index": 5}}, f)

        mtime_before = os.path.getmtime(self.current_path)

        res_dry = migrate_config(
            current_path=self.current_path,
            template_path=self.template_path,
            dry_run=True
        )

        self.assertEqual(res_dry["status"], "dry_run")
        self.assertTrue(res_dry["needs_migration"])
        self.assertEqual(os.path.getmtime(self.current_path), mtime_before)

        # Verificar que no se generó ningún backup en disco
        backups = [f for f in os.listdir(self.test_dir) if ".bak." in f]
        self.assertEqual(len(backups), 0)


if __name__ == "__main__":
    unittest.main()
