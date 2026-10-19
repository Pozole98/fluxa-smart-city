# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Auditoría y Suite de Verificación Exhaustiva End-to-End
Valida la integridad de la FSM, ANPR, Sincronización de Corredor,
Persistencia Asíncrona, API Server y Tolerancia a Fallos sin hardware físico.
Desarrollador Principal: Moisés Emilio Martínez Arias
"""

import os
import sys
import time
import json
import unittest
from unittest.mock import MagicMock, patch

# Configurar path para importar src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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
    sys.modules['ultralytics'] = MagicMock()
    sys.modules['ultralytics.trackers'] = MagicMock()
    sys.modules['ultralytics.trackers.byte_tracker'] = MagicMock()

from corridor_sync import CorridorSyncManager, CorridorNode
from db_manager import DatabaseManager
from analytics import TrafficAnalyticsLogger
from hardware_monitor import HardwareMonitor
from ui4_way_cpu import SemaforoController4V_CPU, EstadoSemaforo4V
from ui2_way_cpu import SemaforoController2V_CPU, EstadoSemaforo2V
from ui3_tee_cpu import SemaforoController3V_CPU, EstadoSemaforo3Tee
from ui4_protected_cpu import SemaforoController4VProtected_CPU, EstadoSemaforoProtected
from ui_pedestrian_cpu import SemaforoControllerPedestrian_CPU, EstadoSemaforoPedestrian


class MockVideoStream:
    def __init__(self, src=0):
        self.src = src
        self.failed = False
    def start(self):
        return self
    def read(self):
        # Generar un fotograma simulado HD de 640x480 con 3 canales
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 50
        return True, frame
    def stop(self):
        pass


class TestFullAudit(unittest.TestCase):

    def setUp(self):
        # Base de datos mockeada para no requerir servidor MariaDB activo en la prueba unitaria
        self.db = DatabaseManager(host="localhost", user="root", password="mock_password", enabled=False)

    def tearDown(self):
        if hasattr(self, 'db') and self.db:
            self.db.close()

    def test_corridor_mesh_progression(self):
        """Auditoría 2: Cálculo de ETA y Propagación de Olas Verdes en Corredor"""
        corridor = CorridorSyncManager(current_node_id="CRUCE_01", avg_speed_kmh=50.0)
        
        # Verificar inicialización de nodos contiguos
        status = corridor.get_status()
        self.assertEqual(status["current_node_id"], "CRUCE_01")
        self.assertEqual(len(status["nodes"]), 3)
        self.assertFalse(status["green_wave_active"])

        # Notificar pelotón hacia nodo downstream
        corridor.notify_departure_platoon(vehicle_count=8, direction="SUR")
        
        # Simular recepción en el nodo downstream CRUCE_02
        cruce2_sync = CorridorSyncManager(current_node_id="CRUCE_02", avg_speed_kmh=50.0)
        payload = {
            "origin_node": "CRUCE_01",
            "target_node": "CRUCE_02",
            "vehicle_count": 8,
            "direction": "SUR",
            "speed_kmh": 50.0,
            "distance_meters": 320,
            "eta_seconds": 23.0
        }
        cruce2_sync.receive_incoming_platoon(payload)
        
        is_wave, origin, remaining = cruce2_sync.should_prioritize_green_wave()
        self.assertTrue(is_wave)
        self.assertEqual(origin, "CRUCE_01")
        self.assertGreater(remaining, 20.0)

    def test_all_topologies_instantiation_and_fsm(self):
        """Auditoría 3: Verificación de ciclo de vida de las 5 topologías soportadas"""
        topologias = [
            (SemaforoController4V_CPU, EstadoSemaforo4V),
            (SemaforoController2V_CPU, EstadoSemaforo2V),
            (SemaforoController3V_CPU, EstadoSemaforo3Tee),
            (SemaforoController4VProtected_CPU, EstadoSemaforoProtected),
            (SemaforoControllerPedestrian_CPU, EstadoSemaforoPedestrian),
        ]

        for controller_cls, enum_cls in topologias:
            with patch('core_semaforo.VideoStream', return_value=MockVideoStream()), \
                 patch('core_semaforo.TelemetryAPI'), \
                 patch('core_semaforo.DatabaseManager', return_value=self.db), \
                 patch('ultralytics.YOLO'):
                
                ctrl = controller_cls(port=5000, video_source="mock")
                ctrl.arduino = MagicMock()
                ctrl.arduino.is_open = True
                
                # Verificar atributos obligatorios
                self.assertIsNotNone(ctrl.corridor)
                self.assertTrue(hasattr(ctrl, 'estado_actual'))
                self.assertIsInstance(ctrl.estado_actual, enum_cls)
                
                # Ejecutar paso de FSM sin excepciones
                autos_simulados = {z: 2 for z in ctrl.zonas_raw.keys()}
                ctrl._procesar_logica_semaforo(autos_simulados, tiempo_minimo_actual=5.0)

    def test_violation_snapshot_forensic_capture(self):
        """Auditoría 3: Detección de Infracción con Captura Forense y Persistencia"""
        with patch('core_semaforo.VideoStream', return_value=MockVideoStream()), \
             patch('core_semaforo.TelemetryAPI'), \
             patch('core_semaforo.DatabaseManager', return_value=self.db), \
             patch('ultralytics.YOLO'):
            
            ctrl = SemaforoController4V_CPU(port=5000, video_source="mock")
            ctrl.estado_actual = EstadoSemaforo4V.VERDE_NS
            
            frame_mock = np.ones((480, 640, 3), dtype=np.uint8) * 30
            # Simular vehículo en carril 'este' (carril con semáforo en rojo cuando NS está en verde)
            bbox = (100, 100, 250, 220)
            
            ctrl._verificar_infraccion_luz_roja(
                zona_nombre="este", track_id=42, frame=frame_mock,
                cx=175, cy=160, bbox=bbox
            )
            
            # Verificar que la infracción quedó registrada en el set de ciclo
            self.assertIn("VERDE_NS_este_42", ctrl.infracciones_capturadas_ciclo)
            
            # Verificar que el gestor de base de datos tiene la infracción en su buffer
            violations = self.db.get_recent_violations(limit=10)
            self.assertGreater(len(violations), 0)
            last_v = violations[0]
            self.assertEqual(last_v["track_id"], 42)

    def test_database_graceful_recovery_and_memory_buffer(self):
        """Auditoría 4: Alta Disponibilidad de DatabaseManager ante Caídas del Servidor"""
        db_offline = DatabaseManager(host="127.0.0.1", user="invalid", password="bad", port=9999, enabled=True)
        self.assertFalse(db_offline.connected)
        
        # Debe registrar en memoria RAM sin lanzar excepción
        db_offline.log_event_async("TEST", "Mensaje de auditoría en memoria")
        db_offline.log_violation_async("este", 99, "ROJO", "mock.jpg")
        
        recent = db_offline.get_recent_violations(limit=5)
        self.assertGreater(len(recent), 0)
        self.assertEqual(recent[0]["track_id"], 99)
        self.assertEqual(recent[0]["lane"], "este")
        
        db_offline.close()


if __name__ == '__main__':
    unittest.main()
