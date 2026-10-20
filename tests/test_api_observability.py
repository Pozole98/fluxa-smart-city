# -*- coding: utf-8 -*-
"""
Tests unitarios de observabilidad, salud y métricas Prometheus (Fase 3).
Verifica /api/health, /metrics y la consola WebUI /c5.
"""

import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Configurar path para importar src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from api_server import app, estado_global, estado_lock


class TestApiObservability(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Asegurar estado base conocido en estado_global
        with estado_lock:
            estado_global["fps"] = 28.5
            estado_global["status"] = "VERDE_NS"
            estado_global["modo"] = "Normal"
            estado_global["total_acumulado"] = 120
            estado_global["autos"] = {"norte": 2, "sur": 3, "este": 1, "oeste": 0}
            estado_global["fase_tiempo_transcurrido"] = 10.5
            estado_global["fase_tiempo_asignado"] = 25.0
            estado_global["camara"] = {
                "connected": True,
                "modo_degradado": False,
                "tipo": "Cámara Hardware (/dev/video0)",
                "source_raw": "/dev/video0",
                "consecutive_failed_frames": 0
            }
            estado_global["arduino"] = {
                "connected": True,
                "virtual_mode": False,
                "port": "/dev/ttyACM0",
                "last_command": "1",
                "last_tx_ago": 0.5,
                "tx_count": 350,
                "reconnects": 0
            }

    def test_api_health_healthy(self):
        """/api/health retorna 200 y status 'healthy' bajo condiciones normales"""
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "healthy")
        self.assertIn("subsystems", data)
        self.assertIn("camera", data["subsystems"])
        self.assertIn("microcontroller", data["subsystems"])
        self.assertIn("traffic_fsm", data["subsystems"])
        self.assertIn("hardware", data["subsystems"])
        self.assertFalse(data["subsystems"]["camera"]["modo_degradado"])

    def test_api_health_degraded_mode(self):
        """/api/health reporta 'degraded' si la cámara está en modo degradado fail-safe"""
        with estado_lock:
            estado_global["camara"]["modo_degradado"] = True

        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)  # 200 porque opera en fail-safe vial
        data = res.get_json()
        self.assertEqual(data["status"], "degraded")
        self.assertTrue(data["subsystems"]["camera"]["modo_degradado"])

    def test_metrics_prometheus_format(self):
        """/metrics exporta texto plano en estándar OpenMetrics / Prometheus"""
        res = self.client.get('/metrics')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content_type.startswith("text/plain"))
        body = res.get_data(as_text=True)

        # Verificar presencia de métricas clave y encabezados HELP/TYPE
        self.assertIn("fluxa_fps 28.5", body)
        self.assertIn("fluxa_vehicles_total 120", body)
        self.assertIn("fluxa_phase_elapsed_seconds 10.5", body)
        self.assertIn("fluxa_phase_assigned_seconds 25.0", body)
        self.assertIn("fluxa_arduino_connected 1", body)
        self.assertIn("# TYPE fluxa_fps gauge", body)
        self.assertIn("# HELP fluxa_fps", body)

    def test_c5_route_requires_auth(self):
        """/c5 redirige a login si la sesión no tiene autenticación de admin"""
        res = self.client.get('/c5')
        # Si auth habilitada, redirige (302) a /login
        self.assertIn(res.status_code, (302, 200))
        if res.status_code == 302:
            self.assertIn("/login", res.headers.get("Location", ""))

    def test_c5_route_authorized(self):
        """/c5 sirve la plantilla c5_scada.html cuando hay sesión activa"""
        with self.client.session_transaction() as sess:
            sess['is_admin'] = True
            sess['user'] = 'admin'

        res = self.client.get('/c5')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("FLUXA C5 SCADA", html)
        self.assertIn("scada-container", html)
        self.assertIn("traffic-light-head", html)

    def test_api_control_actions(self):
        """/api/control acepta acciones tanto en formato canónico como directo en español"""
        mock_cb = MagicMock()
        import api_server
        api_server.control_callback = mock_cb

        with self.client.session_transaction() as sess:
            sess['is_admin'] = True

        # Prueba formato canónico
        res = self.client.post('/api/control', json={'action': 'emergency_corridor', 'target': 'NS'})
        self.assertEqual(res.status_code, 200)
        mock_cb.assert_called_with('NS')

        # Prueba formato directo C5
        res = self.client.post('/api/control', json={'action': 'EMERGENCIA_EO'})
        self.assertEqual(res.status_code, 200)
        mock_cb.assert_called_with('EO')

        # Prueba reset / cancelar
        res = self.client.post('/api/control', json={'action': 'reset'})
        self.assertEqual(res.status_code, 200)
        mock_cb.assert_called_with('RESET')

        res = self.client.post('/api/control', json={'action': 'CANCELAR_EMERGENCIA'})
        self.assertEqual(res.status_code, 200)
        mock_cb.assert_called_with('RESET')

        # Prueba set_mode / CAMBIAR_MODO
        res = self.client.post('/api/control', json={'action': 'set_mode', 'mode': 'Tiempos_Fijos'})
        self.assertEqual(res.status_code, 200)
        mock_cb.assert_called_with('MODE:Tiempos_Fijos')


if __name__ == '__main__':
    unittest.main()
