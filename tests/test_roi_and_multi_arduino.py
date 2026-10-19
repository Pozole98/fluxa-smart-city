# -*- coding: utf-8 -*-
"""
Pruebas de blindaje anti-crash para ROIs (áreas vacías, overlapping, puntos insuficientes)
y de asignación exclusiva de Arduinos entre múltiples nodos concurrentes.
"""
import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from core_semaforo import CoreSemaforoBase
from arduino_locker import ArduinoDeviceLock, inspect_port_lock

class DummyController(CoreSemaforoBase):
    """Instancia de prueba que no carga modelos de IA pesados ni levanta HTTP real"""
    def _load_config(self):
        cfg = super()._load_config()
        if "api" not in cfg:
            cfg["api"] = {}
        cfg["api"]["enabled"] = False
        return cfg

    def _init_model(self):
        pass
    def _predict(self, frame):
        return []

def test_roi_empty_and_insufficient_points_no_crash():
    """Verifica que ROIs vacías o con < 3 vértices no generen IndexErrors ni crasheen el sistema"""
    ctrl = DummyController(topology_name="4_way", port=5900, video_source="test.mp4")
    ctrl.w = 640
    ctrl.h = 480

    # Configurar zonas con áreas vacías, 1 punto, 2 puntos o nulas
    ctrl.zonas_raw = {
        "norte": [],                         # Vacía
        "sur": [[0.5, 0.5]],                 # 1 punto
        "este": [[0.1, 0.1], [0.2, 0.2]],    # 2 puntos (insuficiente)
        "oeste": [[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]], # 3 puntos colineales (área 0)
        "valida": [[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5]] # Cuadrilátero válido
    }

    # No debe lanzar ninguna excepción
    ctrl._construir_poligonos()

    # Solo la zona válida debe estar en self.poligonos activa
    assert "valida" in ctrl.poligonos
    assert "norte" not in ctrl.poligonos
    assert "sur" not in ctrl.poligonos
    assert "este" not in ctrl.poligonos
    assert "oeste" not in ctrl.poligonos

    # Pero todas las zonas deben tener contadores para evitar KeyError
    for z in ctrl.zonas_raw.keys():
        assert z in ctrl.last_autos
        assert z in ctrl.last_demanda_ponderada
        assert z in ctrl._zona_centroids

    # Simular paso de tracking con detecciones
    dummy_tracked = np.array([
        [100, 100, 140, 140, 1, 0.9, 2],  # Auto dentro de zona válida
        [50, 50, 80, 80, 2, 0.85, 2]      # Auto fuera
    ])
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_overlay = np.zeros_like(dummy_frame)

    # No debe crashear
    ctrl._procesar_tracking(dummy_tracked, dummy_frame, dummy_overlay)
    assert ctrl.last_autos["valida"] >= 1
    assert ctrl.last_autos["norte"] == 0

    ctrl.stop()

def test_roi_overlapping_resolution():
    """Verifica que polígonos solapados resuelvan la pertenencia sin crashear ni duplicar conteos"""
    ctrl = DummyController(topology_name="4_way", port=5901, video_source="test.mp4")
    ctrl.w = 640
    ctrl.h = 480

    # Dos zonas fuertemente solapadas
    ctrl.zonas_raw = {
        "zona_a": [[0.1, 0.1], [0.6, 0.1], [0.6, 0.6], [0.1, 0.6]],
        "zona_b": [[0.3, 0.3], [0.8, 0.3], [0.8, 0.8], [0.3, 0.8]]
    }
    ctrl._construir_poligonos()

    # Auto con centroide en (250, 250), que cae en ambas zonas (intersección)
    # x1=230, y1=230, x2=270, y2=270 -> cx=250, cy=250
    dummy_tracked = np.array([
        [230, 230, 270, 270, 42, 0.95, 2]
    ])
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_overlay = np.zeros_like(dummy_frame)

    ctrl._procesar_tracking(dummy_tracked, dummy_frame, dummy_overlay)

    # El auto debe asignarse a UNA SOLA zona (no duplicarse)
    total_asignados = ctrl.last_autos["zona_a"] + ctrl.last_autos["zona_b"]
    assert total_asignados == 1

    ctrl.stop()

def test_multi_node_arduino_exclusive_hijack():
    """Verifica que un nodo secuestre un Arduino y otro nodo no pueda quitárselo"""
    ctrl1 = DummyController(topology_name="4_way", port=5902, video_source="test.mp4")
    ctrl2 = DummyController(topology_name="4_way", port=5903, video_source="test.mp4")

    fake_port = "/dev/ttyTestExclusive"

    # Nodo 1 secuestra el puerto
    res1 = ctrl1.set_arduino_port(fake_port)
    assert res1.get("status") == "ok"
    assert ctrl1.arduino_port_actual == fake_port

    # Nodo 2 intenta secuestrar el mismo puerto: DEBE SER RECHAZADO
    res2 = ctrl2.set_arduino_port(fake_port)
    assert res2.get("status") == "error"
    assert "secuestrado" in res2.get("error", "").lower()
    assert ctrl2.arduino_port_actual != fake_port

    # Nodo 1 conmuta a modo VIRTUAL (libera el puerto)
    res_v = ctrl1.set_arduino_port("VIRTUAL")
    assert res_v.get("status") == "ok"
    assert ctrl1.arduino_port_actual == "VIRTUAL"

    # Ahora Nodo 2 sí puede secuestrarlo
    res2_retry = ctrl2.set_arduino_port(fake_port)
    assert res2_retry.get("status") == "ok"
    assert ctrl2.arduino_port_actual == fake_port

    ctrl1.stop()
    ctrl2.stop()
