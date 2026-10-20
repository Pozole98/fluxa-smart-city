# -*- coding: utf-8 -*-
"""
Tests unitarios de resiliencia de video, reconexión y modo degradado fail-safe (Fase 2).
Verifica que ningún fallo de cámara congele el cruce semafórico ni interrumpa la telemetría.
"""

import os
import sys
import unittest
import time
import numpy as np
from unittest.mock import MagicMock, patch

# Configurar path para importar src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ui4_way_cpu import SemaforoController4V_CPU, EstadoSemaforo4V
from videostream import VideoStream


class TestCameraResilience(unittest.TestCase):

    def setUp(self):
        with patch('core_semaforo.VideoStream'), \
             patch('core_semaforo.TelemetryAPI'), \
             patch('core_semaforo.DatabaseManager'), \
             patch('core_semaforo.get_notifier'), \
             patch('ultralytics.YOLO'):
            self.semaforo = SemaforoController4V_CPU(
                video_source="dummy.mp4",
                port=None,
                enable_arduino=False
            )
        self.semaforo.TIEMPO_FIJO_FALLBACK = 10.0
        self.semaforo.TIEMPO_AMARILLO = 2.0
        self.semaforo.TIEMPO_ROJO_TODOS = 1.0

    def test_videostream_get_status(self):
        """VideoStream.get_status retorna diccionario estructurado"""
        with patch.object(VideoStream, '_conectar_fuente', return_value=None):
            vs = VideoStream(src="test.mp4")
            status = vs.get_status()
            self.assertIn("connected", status)
            self.assertIn("is_file", status)
            self.assertIn("source", status)

    def test_fsm_modo_degradado_fixed_timings(self):
        """En modo degradado, verde respeta exactamente el tiempo fijo asignado"""
        self.semaforo.modo_degradado_camara = True
        self.semaforo.estado_actual = EstadoSemaforo4V.VERDE_NS
        self.semaforo.tiempo_ultimo_cambio = time.time() - 5.0  # 5s transcurridos

        # Demanda ficticia en eje 2 no debe interrumpir el tiempo fijo mínimo
        autos = {"norte": 0, "sur": 0, "este": 10, "oeste": 10}
        self.semaforo._procesar_logica_semaforo(autos)
        self.assertEqual(self.semaforo.fase_tiempo_asignado, 10.0)
        self.assertEqual(self.semaforo.estado_actual, EstadoSemaforo4V.VERDE_NS)

        # Tras expirar el tiempo fijo (10s), debe transicionar a AMARILLO_1 (AMARILLO_NS)
        self.semaforo.tiempo_ultimo_cambio = time.time() - 10.5
        self.semaforo._procesar_logica_semaforo(autos)
        self.assertEqual(self.semaforo.estado_actual, EstadoSemaforo4V.AMARILLO_NS)

    def test_process_frame_activates_degraded_mode_on_consecutive_failures(self):
        """10 fallos consecutivos de captura activan automáticamente el modo degradado"""
        self.semaforo.running = True
        self.semaforo.cap = MagicMock()
        self.semaforo.cap.read.return_value = (False, None)
        self.semaforo.notifier = MagicMock()

        self.assertFalse(self.semaforo.modo_degradado_camara)

        # Simular 10 frames fallidos
        for _ in range(10):
            frame = self.semaforo.process_frame()
            self.assertIsNotNone(frame)

        self.assertTrue(self.semaforo.modo_degradado_camara)
        # Notifier debió enviar el latido de watchdog para no reiniciar el servicio
        self.assertTrue(self.semaforo.notifier.notify_watchdog.called)

    def test_process_frame_auto_recovery_after_valid_frames(self):
        """15 frames válidos consecutivos restauran el modo adaptativo tras una falla"""
        self.semaforo.running = True
        self.semaforo.modo_degradado_camara = True
        self.semaforo.cap = MagicMock()
        self.semaforo.notifier = MagicMock()
        self.semaforo.model = MagicMock()
        self.semaforo.model.track.return_value = []

        valid_frame = np.full((480, 640, 3), 120, dtype=np.uint8)
        # Agregar algo de textura para no dar std < 1.0
        valid_frame[0:100, 0:100] = 200
        self.semaforo.cap.read.return_value = (True, valid_frame)

        # Procesar 14 frames: todavía degradado
        for _ in range(14):
            self.semaforo.process_frame()
        self.assertTrue(self.semaforo.modo_degradado_camara)

        # Frame 15: recuperación
        self.semaforo.process_frame()
        self.assertFalse(self.semaforo.modo_degradado_camara)

    def test_black_frame_detection_triggers_degraded_mode(self):
        """Un flujo con frames negros (sensor sin señal) activa el modo degradado"""
        self.semaforo.running = True
        self.semaforo.cap = MagicMock()
        self.semaforo.notifier = MagicMock()

        # Cuadro totalmente negro (std = 0.0)
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.semaforo.cap.read.return_value = (True, black_frame)

        # 16 cuadros negros provocan is_failsafe y 10 acumulan consecutive_failed_frames
        for _ in range(26):
            self.semaforo.process_frame()

        self.assertTrue(self.semaforo.modo_degradado_camara)


if __name__ == '__main__':
    unittest.main()
