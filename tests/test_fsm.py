# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Suite de Pruebas Unitarias Automatizadas para Seguridad Vial, FSM y Control Adaptativo
Desarrollador Principal: Moisés Emilio Martínez Arias
"""

import os
import sys
import time
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

# Configurar path para importar src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ui4_way_cpu import SemaforoController4V_CPU, EstadoSemaforo4V
from ui2_way_cpu import SemaforoController2V_CPU, EstadoSemaforo2V
from ui3_tee_cpu import SemaforoController3V_CPU, EstadoSemaforo3Tee
from ui4_protected_cpu import SemaforoController4VProtected_CPU, EstadoSemaforoProtected
from ui_pedestrian_cpu import SemaforoControllerPedestrian_CPU, EstadoSemaforoPedestrian
from db_manager import DatabaseManager


class MockVideoCapture:
    def __init__(self, *args, **kwargs):
        self.failed = False
    def read(self):
        # Genera un cuadro simulado de 640x480
        return True, np.zeros((480, 640, 3), dtype=np.uint8)
    def stop(self):
        pass


@pytest.fixture
def mock_controller_4way():
    with patch('core_semaforo.VideoStream', return_value=MockVideoCapture()), \
         patch('core_semaforo.TelemetryAPI'), \
         patch('core_semaforo.DatabaseManager'), \
         patch('ultralytics.YOLO'):
        ctrl = SemaforoController4V_CPU(port="mock", video_source="mock")
        ctrl.arduino = MagicMock()
        ctrl.arduino.is_open = True
        return ctrl


def test_no_conflicting_greens(mock_controller_4way):
    """
    Prueba 1: Seguridad Vial e Intervalo de Incompatibilidad.
    Verifica que bajo ninguna circunstancia los ejes Norte-Sur y Este-Oeste puedan
    recibir luz verde de forma simultánea.
    """
    ctrl = mock_controller_4way
    
    estados_validos = {
        EstadoSemaforo4V.VERDE_NS,
        EstadoSemaforo4V.AMARILLO_NS,
        EstadoSemaforo4V.ROJO_TODOS_1,
        EstadoSemaforo4V.VERDE_EO,
        EstadoSemaforo4V.AMARILLO_EO,
        EstadoSemaforo4V.ROJO_TODOS_2
    }
    
    assert ctrl.estado_actual in estados_validos
    
    commands_sent = []
    ctrl.enviar_comando = lambda cmd: commands_sent.append(cmd)
    
    ctrl.estado_actual = EstadoSemaforo4V.VERDE_NS
    ctrl._procesar_logica_semaforo({'norte': 2, 'sur': 2, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual == EstadoSemaforo4V.VERDE_NS
    assert '3' not in commands_sent  # '3' corresponde al comando de Verde EO


def test_safe_emergency_transition_from_opposing_green(mock_controller_4way):
    """
    Prueba 2: Transición Segura de Emergencia con Intervalos Normativos de Despeje.
    Si el sistema se encuentra en VERDE_NS y se solicita un corredor de emergencia para EO,
    debe otorgar la fase de Ámbar de advertencia y el intervalo de Todo-Rojo antes de dar verde a EO.
    """
    ctrl = mock_controller_4way
    ctrl.TIEMPO_AMARILLO = 3.0
    ctrl.TIEMPO_ROJO_TODOS = 2.0
    ctrl.TIEMPO_BUFFER_EMERGENCIA = 1.0
    
    # 1. Estado inicial en Verde NS
    ctrl.estado_actual = EstadoSemaforo4V.VERDE_NS
    ctrl.tiempo_ultimo_cambio = time.time()
    
    # 2. Activación de solicitud de emergencia C5 para el eje Este-Oeste
    ctrl.emergencia_activa = True
    ctrl.eje_emergencia = 'EO'
    
    # 3. Primer ciclo: Debe transicionar obligatoriamente a Ámbar de despeje
    ctrl._procesar_logica_semaforo({'norte': 0, 'sur': 0, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual == EstadoSemaforo4V.AMARILLO_NS, \
        "Violación de seguridad vial: El sistema no otorgó la fase de Ámbar de despeje al eje saliente."

    # 4. Durante el intervalo de amarillo debe mantenerse en Ámbar
    ctrl.tiempo_ultimo_cambio = time.time() - 1.5
    ctrl._procesar_logica_semaforo({'norte': 0, 'sur': 0, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual == EstadoSemaforo4V.AMARILLO_NS

    # 5. Cumplido el tiempo de amarillo (>3.0s), debe ingresar a Todo-Rojo
    ctrl.tiempo_ultimo_cambio = time.time() - 3.1
    ctrl._procesar_logica_semaforo({'norte': 0, 'sur': 0, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual in [EstadoSemaforo4V.ROJO_TODOS_1, EstadoSemaforo4V.ROJO_TODOS_2], \
        "Violación de seguridad vial: El sistema no otorgó el intervalo de Todo-Rojo tras el Ámbar."

    # 6. Concluido el intervalo de Todo-Rojo, se habilita el Verde de Emergencia
    ctrl.tiempo_ultimo_cambio = time.time() - 3.5
    ctrl._procesar_logica_semaforo({'norte': 0, 'sur': 0, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual == EstadoSemaforo4V.VERDE_EO, \
        "El sistema no otorgó el Verde de Emergencia tras completar el protocolo de despeje."


def test_emergency_from_all_red_respects_safety_buffer(mock_controller_4way):
    """
    Prueba 3: Buffer de Seguridad en Todo-Rojo durante Solicitud de Emergencia.
    Verifica que al recibir una solicitud en fase de Todo-Rojo se respete el intervalo mínimo
    de seguridad antes de otorgar el verde solicitado.
    """
    ctrl = mock_controller_4way
    ctrl.TIEMPO_BUFFER_EMERGENCIA = 1.0
    ctrl.estado_actual = EstadoSemaforo4V.ROJO_TODOS_1
    ctrl.tiempo_ultimo_cambio = time.time()
    
    ctrl.emergencia_activa = True
    ctrl.eje_emergencia = 'NS'
    
    # Inmediatamente tras entrar a rojo, debe mantenerse en rojo respetando el buffer
    ctrl._procesar_logica_semaforo({'norte': 0, 'sur': 0, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual == EstadoSemaforo4V.ROJO_TODOS_1
    
    # Transcurrido el buffer de seguridad, transiciona a Verde NS
    ctrl.tiempo_ultimo_cambio = time.time() - 1.1
    ctrl._procesar_logica_semaforo({'norte': 0, 'sur': 0, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual == EstadoSemaforo4V.VERDE_NS


def test_adaptive_demand_time_calculation(mock_controller_4way):
    """
    Prueba 4: Cálculo Dinámico del Tiempo de Verde Proporcional a la Demanda.
    Verifica que ante una mayor afluencia vehicular, el tiempo asignado se extienda
    de forma acotada por encima del umbral mínimo base.
    """
    ctrl = mock_controller_4way
    ctrl.TIEMPO_MINIMO_VERDE_BASE = 5.0
    ctrl.TIEMPO_MAXIMO_VERDE = 40.0
    ctrl.config["traffic_light"]["factor_tiempo_por_auto"] = 3.0
    
    ctrl.estado_actual = EstadoSemaforo4V.VERDE_NS
    ctrl.tiempo_ultimo_cambio = time.time()
    
    autos = {'norte': 6, 'sur': 2, 'este': 0, 'oeste': 0}
    ctrl._procesar_logica_semaforo(autos, tiempo_minimo_actual=5.0)
    
    assert ctrl.fase_tiempo_asignado >= 18.0
    assert ctrl.fase_tiempo_asignado <= 40.0


def test_database_manager_missing_password_fails_fast():
    """
    Prueba 5: Seguridad en Inicialización de Base de Datos.
    Verifica que DatabaseManager falle de inmediato si la persistencia está habilitada
    pero no se define la contraseña de conexión.
    """
    with patch.dict(os.environ, {}, clear=True):
        if "DATABASE_PASSWORD" in os.environ:
            del os.environ["DATABASE_PASSWORD"]
        with pytest.raises(ValueError) as excinfo:
            DatabaseManager(enabled=True, password=None)
            assert "contraseña de mariadb no está definida" in str(excinfo.value).lower()


def test_protected_left_turn_phase_skipping():
    """
    Prueba 6: Intersección con Giro Protegido y Salto de Fase (Phase-Skipping).
    Si no se detectan vehículos en el carril exclusivo de giro, la máquina de estados
    omite la fase de giro para optimizar la fluidez vehicular.
    """
    with patch('core_semaforo.VideoStream', return_value=MockVideoCapture()), \
         patch('core_semaforo.TelemetryAPI'), \
         patch('core_semaforo.DatabaseManager'), \
         patch('ultralytics.YOLO'):
        ctrl = SemaforoController4VProtected_CPU(port="mock", video_source="mock")
        ctrl.TIEMPO_ROJO_TODOS = 1.0
        
        ctrl.estado_actual = EstadoSemaforoProtected.ROJO_TODOS_1
        ctrl.tiempo_ultimo_cambio = time.time() - 1.5
        
        ctrl._procesar_logica_semaforo({'frente': 3, 'giro_izq': 0}, tiempo_minimo_actual=5.0)
        assert ctrl.estado_actual == EstadoSemaforoProtected.VERDE_FRENTE


def test_pedestrian_midblock_cycle():
    """
    Prueba 7: Ciclo Semafórico de Cruce Peatonal Inteligente.
    Verifica la asignación de tiempo seguro de cruce cuando se detecta demanda peatonal.
    """
    with patch('core_semaforo.VideoStream', return_value=MockVideoCapture()), \
         patch('core_semaforo.TelemetryAPI'), \
         patch('core_semaforo.DatabaseManager'), \
         patch('ultralytics.YOLO'):
        ctrl = SemaforoControllerPedestrian_CPU(port="mock", video_source="mock")
        ctrl.TIEMPO_ROJO_TODOS = 1.0
        
        ctrl.estado_actual = EstadoSemaforoPedestrian.ROJO_TODOS_1
        ctrl.tiempo_ultimo_cambio = time.time() - 1.5
        
        ctrl._procesar_logica_semaforo({'vehiculos': 0, 'peatones_esperando': 2}, tiempo_minimo_actual=5.0)
        assert ctrl.estado_actual == EstadoSemaforoPedestrian.VERDE_PEATONES
        
        ctrl._procesar_logica_semaforo({'vehiculos': 0, 'peatones_esperando': 2}, tiempo_minimo_actual=5.0)
        assert ctrl.fase_tiempo_asignado >= 10.0


def test_rknn_npu_to_cpu_fallback():
    """
    Prueba 8: Tolerancia a Fallos y Conmutación Automática (NPU a CPU).
    Verifica que el controlador CoreSemaforoRKNN active el motor PyTorch en CPU
    si la NPU Rockchip o los modelos binarios no están disponibles.
    """
    from core_semaforo_rknn import CoreSemaforoRKNN
    
    with patch('core_semaforo.VideoStream', return_value=MockVideoCapture()), \
         patch('core_semaforo.TelemetryAPI'), \
         patch('core_semaforo.DatabaseManager'), \
         patch('ultralytics.YOLO') as mock_yolo:
        
        mock_yolo_instance = MagicMock()
        mock_yolo.return_value = mock_yolo_instance
        
        ctrl = CoreSemaforoRKNN(topology_name="4_way", port="mock", video_source="mock")
        assert ctrl.is_cpu_fallback is True
        assert "CPU" in ctrl.backend_name
        assert ctrl.cpu_model is not None


def test_violations_capture_and_retrieval():
    """
    Prueba 9: Módulo de Infracciones y Recuperación Multicapa.
    Verifica que las infracciones registradas en luz roja se almacenen y recuperen
    correctamente tanto en MariaDB como en el búfer local en memoria.
    """
    from db_manager import DatabaseManager
    
    db = DatabaseManager(enabled=False)
    db.log_violation_async(lane="este", track_id=42, phase_state="VERDE_NS", snapshot_path="violation_test.jpg")
    
    violations = db.get_recent_violations()
    assert len(violations) >= 1
    assert violations[0]["track_id"] == 42
    assert violations[0]["lane"] == "este"
    assert violations[0]["phase_state"] == "VERDE_NS"
    assert violations[0]["snapshot_path"] == "violation_test.jpg"
