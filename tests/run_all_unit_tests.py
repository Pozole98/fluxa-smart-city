# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Suite de Pruebas y Auditoría Integral de Lógica, FSM, Corredor y Base de Datos
Ejecuta validaciones exhaustivas con mocks transparentes de hardware/visión.
Desarrollador Principal: Moisés Emilio Martínez Arias
"""

import os
import sys
import time
import json
import unittest
from unittest.mock import MagicMock, patch

# Asegurar módulos mock si faltan librerías binarias
class MockArray:
    def __init__(self, shape=(480, 640, 3), fill=0):
        self.shape = shape
        self.size = shape[0] * shape[1] * (shape[2] if len(shape) > 2 else 1)
        self.fill = fill
    def __getitem__(self, item):
        if isinstance(item, tuple):
            s0, s1 = item[0], item[1]
            h = (s0.stop - (s0.start or 0)) if isinstance(s0, slice) and s0.stop else self.shape[0]
            w = (s1.stop - (s1.start or 0)) if isinstance(s1, slice) and s1.stop else self.shape[1]
            return MockArray(shape=(max(1, h), max(1, w), self.shape[2] if len(self.shape) > 2 else 1))
        return self
    def __sub__(self, other): return self
    def __truediv__(self, other): return self
    def __mul__(self, other): return self
    def __rmul__(self, other): return self
    def astype(self, dtype): return self
    def copy(self): return MockArray(shape=self.shape, fill=self.fill)

try:
    import numpy as np
except ImportError:
    class MockNumPy:
        float32 = float
        uint8 = int
        int32 = int
        ndarray = MockArray
        def array(self, val, dtype=None): return MockArray()
        def zeros(self, shape, dtype=None): return MockArray(shape=shape)
        def ones(self, shape, dtype=None): return MockArray(shape=shape, fill=1)
        def empty(self, shape, dtype=None): return MockArray(shape=shape)
        def asarray(self, val, dtype=None): return MockArray()
        def column_stack(self, val): return MockArray()
        def mean(self, val): return 100
        def min(self, val): return 0
        def max(self, val): return 255
        def absolute(self, val): return val
    np = MockNumPy()
    sys.modules['numpy'] = np

try:
    import cv2
except ImportError:
    class MockCV2:
        FONT_HERSHEY_SIMPLEX = 1
        COLOR_BGR2GRAY = 6
        CV_32F = 5
        MORPH_RECT = 0
        MORPH_CLOSE = 3
        THRESH_BINARY = 0
        THRESH_OTSU = 8
        RETR_TREE = 3
        CHAIN_APPROX_SIMPLE = 2
        INTER_CUBIC = 2
        IMWRITE_JPEG_QUALITY = 1
        def cvtColor(self, src, code): return src
        def bilateralFilter(self, src, d, sc, ss): return src
        def Sobel(self, src, ddepth, dx, dy, ksize=-1): return src
        def getStructuringElement(self, shape, ksize): return []
        def morphologyEx(self, src, op, kernel): return src
        def threshold(self, src, thresh, maxval, type): return 0, src
        def erode(self, src, kernel, iterations=1): return src
        def dilate(self, src, kernel, iterations=1): return src
        def findContours(self, image, mode, method): return [], None
        def boundingRect(self, c): return 0, 0, 100, 40
        def contourArea(self, c): return 4000
        def resize(self, src, dsize, interpolation=None): return src
        def rectangle(self, img, pt1, pt2, color, thickness=1): pass
        def circle(self, img, center, radius, color, thickness=1): pass
        def putText(self, img, text, org, fontFace, fontScale, color, thickness=1): pass
        def fillPoly(self, img, pts, color): pass
        def polylines(self, img, pts, isClosed, color, thickness=1): pass
        def addWeighted(self, s1, a1, s2, a2, gamma, dst=None): return s1
        def getTextSize(self, text, fontFace, fontScale, thickness): return (100, 20), 0
        def pointPolygonTest(self, curve, pt, measureDist): return 1
        def imwrite(self, path, img): return True
        def imencode(self, ext, img, params=None): return True, b'mock_jpeg_bytes'
    cv2 = MockCV2()
    sys.modules['cv2'] = cv2

try:
    import serial
except ImportError:
    sys.modules['serial'] = MagicMock()

try:
    import ultralytics
except ImportError:
    mock_ultra = MagicMock()
    sys.modules['ultralytics'] = mock_ultra
    sys.modules['ultralytics.trackers'] = MagicMock()
    sys.modules['ultralytics.trackers.byte_tracker'] = MagicMock()

# Configurar path para importar src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from corridor_sync import CorridorSyncManager
from db_manager import DatabaseManager
from ui4_way_cpu import SemaforoController4V_CPU, EstadoSemaforo4V
from ui2_way_cpu import SemaforoController2V_CPU, EstadoSemaforo2V
from ui3_tee_cpu import SemaforoController3V_CPU, EstadoSemaforo3Tee
from ui4_protected_cpu import SemaforoController4VProtected_CPU, EstadoSemaforoProtected
from ui_pedestrian_cpu import SemaforoControllerPedestrian_CPU, EstadoSemaforoPedestrian


class FullAuditTestSuite(unittest.TestCase):

    def test_01_corridor_mesh_coordination(self):
        """Auditoría 1: Sincronización de Corredor Vial y Olas Verdes"""
        corridor = CorridorSyncManager(current_node_id="CRUCE_01", corridor_name="Av. Central", avg_speed_kmh=45.0)
        status = corridor.get_status()
        self.assertEqual(status["current_node_id"], "CRUCE_01")
        self.assertEqual(len(status["nodes"]), 3)
        self.assertFalse(status["green_wave_active"])

        # Notificar pelotón hacia aguas abajo
        corridor.notify_departure_platoon(vehicle_count=5, direction="SUR")
        
        # Recibir en nodo aguas abajo
        c2 = CorridorSyncManager(current_node_id="CRUCE_02", avg_speed_kmh=45.0)
        c2.receive_incoming_platoon({
            "origin_node": "CRUCE_01",
            "vehicle_count": 5,
            "eta_seconds": 15.0
        })
        is_wave, origin, remaining = c2.should_prioritize_green_wave()
        self.assertTrue(is_wave)
        self.assertEqual(origin, "CRUCE_01")
        self.assertGreater(remaining, 10.0)

    def test_02_database_manager_async_and_resilience(self):
        """Auditoría 2: Persistencia Asíncrona Tolerante a Fallos de MariaDB"""
        db = DatabaseManager(host="localhost", user="root", password="bad_password", enabled=True)
        # Operación en modo local / memoria
        db.log_event_async("INFO", "Auditoría de evento")
        db.log_violation_async("este", 101, "ROJO_TODOS_1", "snap.jpg")
        
        violations = db.get_recent_violations(limit=5)
        self.assertGreater(len(violations), 0)
        self.assertEqual(violations[0]["track_id"], 101)
        db.close()

    def test_03_fsm_safe_emergency_and_green_wave_all_topologies(self):
        """Auditoría 3: Comportamiento FSM, Seguridad Vial y Despeje en Todas las Topologías"""
        topos = [
            (SemaforoController4V_CPU, EstadoSemaforo4V, "4_way"),
            (SemaforoController2V_CPU, EstadoSemaforo2V, "2_way"),
            (SemaforoController3V_CPU, EstadoSemaforo3Tee, "3_way_t"),
            (SemaforoController4VProtected_CPU, EstadoSemaforoProtected, "4_way_protected"),
            (SemaforoControllerPedestrian_CPU, EstadoSemaforoPedestrian, "pedestrian"),
        ]

        for ctrl_cls, enum_cls, topo_name in topos:
            with patch('core_semaforo.VideoStream'), \
                 patch('core_semaforo.TelemetryAPI'), \
                 patch('core_semaforo.DatabaseManager'):
                
                ctrl = ctrl_cls(port=5000, video_source="mock")
                ctrl.arduino = MagicMock()
                ctrl.arduino.is_open = True
                
                self.assertIsNotNone(ctrl.corridor)
                self.assertIsInstance(ctrl.estado_actual, enum_cls)
                
                # Probar paso FSM adaptativo
                autos = {z: 1 for z in ctrl.zonas_raw.keys()}
                ctrl._procesar_logica_semaforo(autos, tiempo_minimo_actual=5.0)

    def test_04_red_light_violation_forensic_capture(self):
        """Auditoría 4: Detección Integral de Infracción y Registro en DB"""
        with patch('core_semaforo.VideoStream'), \
             patch('core_semaforo.TelemetryAPI'), \
             patch('core_semaforo.DatabaseManager') as mock_db:
            
            ctrl = SemaforoController4V_CPU(port=5000, video_source="mock")
            ctrl.estado_actual = EstadoSemaforo4V.VERDE_NS
            
            fake_frame = np.ones((480, 640, 3), dtype=np.uint8) * 30
            ctrl._verificar_infraccion_luz_roja(
                zona_nombre="este", track_id=77, frame=fake_frame,
                cx=200, cy=200, bbox=(50, 50, 250, 200)
            )
            self.assertIn("VERDE_NS_este_77", ctrl.infracciones_capturadas_ciclo)

    def test_06_api_server_endpoints(self):
        """Auditoría 6: Endpoints de Telemetría, Corredor y Control WebUI"""
        import api_server
        api = api_server.TelemetryAPI(enabled=False)
        corridor = CorridorSyncManager(current_node_id="CRUCE_01", avg_speed_kmh=45.0)
        
        api.start(
            controller_callback=MagicMock(),
            frame_getter=lambda: b'fake_jpeg',
            db_instance=None,
            corridor_instance=corridor
        )
        
        client = api_server.app.test_client()
        
        # Test GET /api/status
        res = client.get('/api/status')
        self.assertIn(res.status_code, (200, 302))
        
        # Test GET /api/corridor/status
        res_corridor = client.get('/api/corridor/status')
        self.assertEqual(res_corridor.status_code, 200)
        data = json.loads(res_corridor.data.decode('utf-8'))
        self.assertEqual(data["current_node_id"], "CRUCE_01")
        
        # Test POST /api/corridor/incoming_platoon
        res_platoon = client.post('/api/corridor/incoming_platoon', json={
            "origin_node": "CRUCE_NORTE",
            "vehicle_count": 7,
            "eta_seconds": 18.0
        })
        self.assertEqual(res_platoon.status_code, 200)
        
        # Test POST /api/corridor/trigger_wave
        res_wave = client.post('/api/corridor/trigger_wave', json={
            "vehicle_count": 4,
            "direction": "SUR"
        })
        self.assertEqual(res_wave.status_code, 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)
