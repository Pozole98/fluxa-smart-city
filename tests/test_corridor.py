# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Suite de Pruebas Unitarias para el Módulo de Sincronización de Corredor y Olas Verdes
Desarrollador Principal: Moisés Emilio Martínez Arias
"""

import os
import sys
import time
import unittest

# Configurar path para importar src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from corridor_sync import CorridorSyncManager


class TestCorridorSync(unittest.TestCase):

    def setUp(self):
        self.manager = CorridorSyncManager(current_node_id="CRUCE_01", avg_speed_kmh=45.0)

    def test_default_corridor_nodes(self):
        """Verifica que el corredor se inicialice con al menos 3 nodos conectados"""
        status = self.manager.get_status()
        self.assertEqual(status["current_node_id"], "CRUCE_01")
        self.assertEqual(len(status["nodes"]), 3)
        self.assertFalse(status["green_wave_active"])

    def test_notify_departure_platoon_and_receive(self):
        """Verifica el cálculo de ETA y la activación de la ventana de paso de ola verde"""
        # CRUCE_02 recibe una notificación de pelotón proveniente de CRUCE_01
        payload = {
            "origin_node": "CRUCE_01",
            "target_node": "CRUCE_02",
            "vehicle_count": 6,
            "direction": "SUR",
            "speed_kmh": 45.0,
            "distance_meters": 320,
            "eta_seconds": 12.0
        }
        
        node2_manager = CorridorSyncManager(current_node_id="CRUCE_02", avg_speed_kmh=45.0)
        node2_manager.receive_incoming_platoon(payload)

        is_active, origin, remaining = node2_manager.should_prioritize_green_wave()
        self.assertTrue(is_active)
        self.assertEqual(origin, "CRUCE_01")
        self.assertGreater(remaining, 10.0)

        # Estado reportado para la consola SCADA C5
        status = node2_manager.get_status()
        self.assertTrue(status["green_wave_active"])
        self.assertEqual(status["green_wave_origin"], "CRUCE_01")
        self.assertGreater(len(status["recent_waves"]), 0)


if __name__ == '__main__':
    unittest.main()
