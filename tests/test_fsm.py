"""
Tests Automatizados para FLUXA Traffic Management System
Verificación de Seguridad Vial, Transiciones de FSM, Despeje de Emergencia,
Control Adaptativo por Demanda y Protección contra Errores Críticos (P2.1).
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
        # 640x480 black image
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
    Test 1: Seguridad Básica (Intervalo de Incompatibilidad).
    Verifica que en ningún momento los ejes Norte-Sur y Este-Oeste puedan tener
    luz verde simultáneamente en la máquina de estados.
    """
    ctrl = mock_controller_4way
    
    # Estados válidos
    estados_validos = {
        EstadoSemaforo4V.VERDE_NS,
        EstadoSemaforo4V.AMARILLO_NS,
        EstadoSemaforo4V.ROJO_TODOS_1,
        EstadoSemaforo4V.VERDE_EO,
        EstadoSemaforo4V.AMARILLO_EO,
        EstadoSemaforo4V.ROJO_TODOS_2
    }
    
    assert ctrl.estado_actual in estados_validos
    
    # Verificar que el comando de luz verde NS ('1') nunca se envíe al mismo tiempo que luz verde EO ('3')
    commands_sent = []
    ctrl.enviar_comando = lambda cmd: commands_sent.append(cmd)
    
    # Ciclo normal
    ctrl.estado_actual = EstadoSemaforo4V.VERDE_NS
    ctrl._procesar_logica_semaforo({'norte': 2, 'sur': 2, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual == EstadoSemaforo4V.VERDE_NS
    assert '3' not in commands_sent  # '3' es verde EO


def test_safe_emergency_transition_from_opposing_green(mock_controller_4way):
    """
    Test 2: Transición Segura de Emergencia desde Verde Contrario (P1.1).
    Si el sistema está en VERDE_NS y llega una emergencia para EO:
    Debe transicionar a AMARILLO_NS (no saltar a VERDE_EO), esperar el tiempo de
    ámbar, pasar a ROJO_TODOS, y solo entonces otorgar VERDE_EO.
    """
    ctrl = mock_controller_4way
    ctrl.TIEMPO_AMARILLO = 3.0
    ctrl.TIEMPO_ROJO_TODOS = 2.0
    ctrl.TIEMPO_BUFFER_EMERGENCIA = 1.0
    
    # 1. Estado inicial: Verde NS
    ctrl.estado_actual = EstadoSemaforo4V.VERDE_NS
    ctrl.tiempo_ultimo_cambio = time.time()
    
    # 2. Se activa emergencia para EO
    ctrl.emergencia_activa = True
    ctrl.eje_emergencia = 'EO'
    
    # 3. Primer ciclo: Debe forzar AMARILLO_NS (despeje de seguridad)
    ctrl._procesar_logica_semaforo({'norte': 0, 'sur': 0, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual == EstadoSemaforo4V.AMARILLO_NS, \
        "Violación de seguridad vial: El sistema no otorgó la fase de Ámbar de despeje al eje saliente."

    # 4. Durante el tiempo de amarillo (ej. transcurridos 1.5s): debe permanecer en AMARILLO_NS
    ctrl.tiempo_ultimo_cambio = time.time() - 1.5
    ctrl._procesar_logica_semaforo({'norte': 0, 'sur': 0, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual == EstadoSemaforo4V.AMARILLO_NS

    # 5. Terminado el tiempo de amarillo (>3.0s): debe pasar a ROJO_TODOS_1
    ctrl.tiempo_ultimo_cambio = time.time() - 3.1
    ctrl._procesar_logica_semaforo({'norte': 0, 'sur': 0, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual in [EstadoSemaforo4V.ROJO_TODOS_1, EstadoSemaforo4V.ROJO_TODOS_2], \
        "Violación de seguridad vial: El sistema no otorgó el intervalo de Todo-Rojo tras el Ámbar."

    # 6. Terminado el buffer de Todo-Rojo: ahora sí debe pasar a VERDE_EO
    ctrl.tiempo_ultimo_cambio = time.time() - 3.5
    ctrl._procesar_logica_semaforo({'norte': 0, 'sur': 0, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual == EstadoSemaforo4V.VERDE_EO, \
        "El sistema no otorgó el Verde de Emergencia tras completar el protocolo de despeje."


def test_emergency_from_all_red_respects_safety_buffer(mock_controller_4way):
    """
    Test 3: Buffer de Todo-Rojo antes de Verde de Emergencia desde Rojo (P1.3).
    Si el sistema está en ROJO_TODOS cuando llega una emergencia, debe respetar
    el buffer de seguridad antes de habilitar el verde.
    """
    ctrl = mock_controller_4way
    ctrl.TIEMPO_BUFFER_EMERGENCIA = 1.0
    ctrl.estado_actual = EstadoSemaforo4V.ROJO_TODOS_1
    ctrl.tiempo_ultimo_cambio = time.time()  # acaba de entrar a rojo (0s transcurridos)
    
    ctrl.emergencia_activa = True
    ctrl.eje_emergencia = 'NS'
    
    # Inmediatamente tras entrar a rojo, debe mantenerse en rojo (respetando buffer)
    ctrl._procesar_logica_semaforo({'norte': 0, 'sur': 0, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual == EstadoSemaforo4V.ROJO_TODOS_1
    
    # Tras transcurrir el buffer de 1s, pasa a Verde NS
    ctrl.tiempo_ultimo_cambio = time.time() - 1.1
    ctrl._procesar_logica_semaforo({'norte': 0, 'sur': 0, 'este': 0, 'oeste': 0}, tiempo_minimo_actual=5.0)
    assert ctrl.estado_actual == EstadoSemaforo4V.VERDE_NS


def test_adaptive_demand_time_calculation(mock_controller_4way):
    """
    Test 4: Asignación Dinámica Proporcional a la Demanda.
    Verifica que si la demanda vehicular en NS es alta (ej. 8 autos), el tiempo
    asignado de verde se extienda por encima del tiempo mínimo base.
    """
    ctrl = mock_controller_4way
    ctrl.TIEMPO_MINIMO_VERDE_BASE = 5.0
    ctrl.TIEMPO_MAXIMO_VERDE = 40.0
    ctrl.config["traffic_light"]["factor_tiempo_por_auto"] = 3.0
    
    ctrl.estado_actual = EstadoSemaforo4V.VERDE_NS
    ctrl.tiempo_ultimo_cambio = time.time()
    
    autos = {'norte': 6, 'sur': 2, 'este': 0, 'oeste': 0}
    ctrl._procesar_logica_semaforo(autos, tiempo_minimo_actual=5.0)
    
    # 6 autos * 3.0 factor = 18.0 segundos
    assert ctrl.fase_tiempo_asignado >= 18.0
    assert ctrl.fase_tiempo_asignado <= 40.0


def test_database_manager_missing_password_fails_fast():
    """
    Test 5: Seguridad Crítica de Base de Datos (P0.1).
    Verifica que DatabaseManager no permita contraseñas hardcodeadas ni arranque
    inseguro si enabled=True y no se suministra DATABASE_PASSWORD.
    """
    with patch.dict(os.environ, {}, clear=True):
        if "DATABASE_PASSWORD" in os.environ:
            del os.environ["DATABASE_PASSWORD"]
        with pytest.raises(ValueError) as excinfo:
            DatabaseManager(enabled=True, password=None)
            assert "contraseña de mariadb no está definida" in str(excinfo.value).lower()


def test_protected_left_turn_phase_skipping():
    """
    Test 6: Giro Protegido con Phase-Skipping (4_way_protected).
    Si no hay demanda en el carril de giro a la izquierda (autos=0), el sistema
    debe saltar la fase de giro y volver de inmediato a VERDE_FRENTE.
    """
    with patch('core_semaforo.VideoStream', return_value=MockVideoCapture()), \
         patch('core_semaforo.TelemetryAPI'), \
         patch('core_semaforo.DatabaseManager'), \
         patch('ultralytics.YOLO'):
        ctrl = SemaforoController4VProtected_CPU(port="mock", video_source="mock")
        ctrl.TIEMPO_ROJO_TODOS = 1.0
        
        # En ROJO_TODOS_1 con 0 autos en giro_izq
        ctrl.estado_actual = EstadoSemaforoProtected.ROJO_TODOS_1
        ctrl.tiempo_ultimo_cambio = time.time() - 1.5
        
        # Sin demanda en giro_izq
        ctrl._procesar_logica_semaforo({'frente': 3, 'giro_izq': 0}, tiempo_minimo_actual=5.0)
        
        # Debe saltar el verde de giro y retornar a VERDE_FRENTE
        assert ctrl.estado_actual == EstadoSemaforoProtected.VERDE_FRENTE


def test_pedestrian_midblock_cycle():
    """
    Test 7: Cruce Peatonal Inteligente (pedestrian).
    Verifica que la fase peatonal se habilite tras demanda peatonal y que el tiempo
    de cruce sea seguro.
    """
    with patch('core_semaforo.VideoStream', return_value=MockVideoCapture()), \
         patch('core_semaforo.TelemetryAPI'), \
         patch('core_semaforo.DatabaseManager'), \
         patch('ultralytics.YOLO'):
        ctrl = SemaforoControllerPedestrian_CPU(port="mock", video_source="mock")
        ctrl.TIEMPO_ROJO_TODOS = 1.0
        
        ctrl.estado_actual = EstadoSemaforoPedestrian.ROJO_TODOS_1
        ctrl.tiempo_ultimo_cambio = time.time() - 1.5
        
        # Transición de Rojo a Verde Peatonal
        ctrl._procesar_logica_semaforo({'vehiculos': 0, 'peatones_esperando': 2}, tiempo_minimo_actual=5.0)
        assert ctrl.estado_actual == EstadoSemaforoPedestrian.VERDE_PEATONES
        
        # En fase VERDE_PEATONES se calcula y asigna el tiempo seguro de cruce
        ctrl._procesar_logica_semaforo({'vehiculos': 0, 'peatones_esperando': 2}, tiempo_minimo_actual=5.0)
        assert ctrl.fase_tiempo_asignado >= 10.0


def test_rknn_npu_to_cpu_fallback():
    """
    Test 8: Tolerancia a Fallos y Fail-Safe Fallback (NPU -> CPU).
    Verifica que si la NPU Rockchip no está disponible o el modelo RKNN falla,
    el controlador CoreSemaforoRKNN conmute automáticamente a inferencia por CPU sin crash.
    """
    from core_semaforo_rknn import CoreSemaforoRKNN
    
    with patch('core_semaforo.VideoStream', return_value=MockVideoCapture()), \
         patch('core_semaforo.TelemetryAPI'), \
         patch('core_semaforo.DatabaseManager'), \
         patch('ultralytics.YOLO') as mock_yolo:
        
        mock_yolo_instance = MagicMock()
        mock_yolo.return_value = mock_yolo_instance
        
        # Instanciar controlador RKNN sin hardware NPU
        ctrl = CoreSemaforoRKNN(topology_name="4_way", port="mock", video_source="mock")
        
        # Debe haber detectado la ausencia de RKNN/NPU y activado el fallback a CPU
        assert ctrl.is_cpu_fallback is True
        assert "CPU" in ctrl.backend_name
        assert ctrl.cpu_model is not None


def test_violations_capture_and_retrieval():
    """
    Test 9: Módulo de Infracciones y Tolerancia a Fallos.
    Verifica que las infracciones en luz roja se detecten y puedan consultarse
    correctamente tanto en MariaDB como en el buffer local de respaldo.
    """
    from db_manager import DatabaseManager
    
    # Instanciar DatabaseManager con MariaDB deshabilitado (Modo local)
    db = DatabaseManager(enabled=False)
    
    # Registrar infracción en buffer local
    db.log_violation_async(lane="este", track_id=42, phase_state="VERDE_NS", snapshot_path="violation_test.jpg")
    
    violations = db.get_recent_violations()
    assert len(violations) >= 1
    assert violations[0]["track_id"] == 42
    assert violations[0]["lane"] == "este"
    assert violations[0]["phase_state"] == "VERDE_NS"
    assert violations[0]["snapshot_path"] == "violation_test.jpg"



