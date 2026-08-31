# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Módulo de Sincronización de Corredor Vial Multicruce y Olas Verdes Dinámicas (Corridor Mesh Sync)
Coordina múltiples intersecciones (Locales en Orange Pi 5 multi-núcleo o distribuidas en LAN).
Desarrollador Principal y Titular de Derechos: Moisés Emilio Martínez Arias
Todos los derechos reservados © 2026.
"""

import time
import json
import logging
import threading
from datetime import datetime

try:
    import urllib.request
    URLLIB_AVAILABLE = True
except ImportError:
    URLLIB_AVAILABLE = False


class CorridorNode:
    """Representación de un nodo / intersección en el corredor vial"""
    def __init__(self, node_id, name, distance_meters=300, target_url=None):
        self.node_id = str(node_id)
        self.name = name
        self.distance_meters = distance_meters
        self.target_url = target_url  # e.g., "http://192.168.1.102:5000"
        self.last_phase = "UNKNOWN"
        self.last_platoon_time = 0.0
        self.estimated_platoon_eta = 0.0
        self.incoming_platoons = []

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "name": self.name,
            "distance_meters": self.distance_meters,
            "target_url": self.target_url,
            "last_phase": self.last_phase,
            "incoming_platoons_count": len(self.incoming_platoons)
        }


class CorridorSyncManager:
    """
    Gestor de Coordinación Descentralizada de Corredor Vial y Olas Verdes.
    Permite calcular el tiempo de arribo de pelotones (Platoon Arrival Time)
    y anticipar la fase verde en cruces aguas abajo para evitar detenciones.
    """

    def __init__(self, current_node_id="CRUCE_01", corridor_name="Avenida Principal Coacalco", avg_speed_kmh=45.0):
        self.current_node_id = str(current_node_id)
        self.corridor_name = corridor_name
        self.avg_speed_kmh = max(20.0, float(avg_speed_kmh))
        self.avg_speed_mps = (self.avg_speed_kmh * 1000.0) / 3600.0  # m/s
        
        self.nodes = {}
        self.active_green_wave = False
        self.green_wave_expiry = 0.0
        self.green_wave_origin = None
        self.lock = threading.Lock()
        
        # Historial de eventos de ola verde
        self.wave_history = []
        self._init_default_corridor()

    def _init_default_corridor(self):
        """Inicializa una topología típica de corredor de 3 intersecciones"""
        self.add_or_update_node("CRUCE_01", "Intersección Norte (Av. Central)", distance_meters=0)
        self.add_or_update_node("CRUCE_02", "Intersección Centro (Av. Hidalgo)", distance_meters=320)
        self.add_or_update_node("CRUCE_03", "Intersección Sur (Av. del Parque)", distance_meters=650)

    def add_or_update_node(self, node_id, name, distance_meters=300, target_url=None):
        with self.lock:
            self.nodes[str(node_id)] = CorridorNode(node_id, name, distance_meters, target_url)

    def notify_departure_platoon(self, vehicle_count, direction="SUR", speed_kmh=None):
        """
        Invocado por el nodo actual cuando abre su fase verde principal con alta densidad vehicular.
        Calcula el tiempo de viaje estimado (ETA) y propaga la alerta a los nodos siguientes.
        """
        if vehicle_count < 2:
            return  # No se justifica una ola verde para 1 solo auto

        speed = speed_kmh if speed_kmh else self.avg_speed_kmh
        speed_mps = (speed * 1000.0) / 3600.0
        now = time.time()

        with self.lock:
            curr_node = self.nodes.get(self.current_node_id)
            curr_dist = curr_node.distance_meters if curr_node else 0

            for n_id, node in self.nodes.items():
                if n_id == self.current_node_id:
                    continue

                delta_dist = abs(node.distance_meters - curr_dist)
                if delta_dist <= 0:
                    continue

                eta_seconds = round(delta_dist / speed_mps, 1)
                platoon_payload = {
                    "origin_node": self.current_node_id,
                    "target_node": n_id,
                    "vehicle_count": vehicle_count,
                    "direction": direction,
                    "speed_kmh": speed,
                    "distance_meters": delta_dist,
                    "eta_seconds": eta_seconds,
                    "expected_arrival_timestamp": now + eta_seconds
                }

                # Si es un nodo remoto con URL configurada, enviar por HTTP en segundo plano
                if node.target_url and URLLIB_AVAILABLE:
                    threading.Thread(target=self._send_remote_platoon, args=(node.target_url, platoon_payload), daemon=True).start()
                else:
                    # Registro interno para simulación local multi-nodo
                    node.incoming_platoons.append(platoon_payload)

                logging.info(f"🌊 OLA VERDE EMITIDA: Desde {self.current_node_id} hacia {n_id} | Pelotón: {vehicle_count} veh | ETA: {eta_seconds}s")

    def _send_remote_platoon(self, target_url, payload):
        """Transmite la alerta de pelotón vía HTTP REST a otro nodo FLUXA en la red"""
        try:
            url = f"{target_url.rstrip('/')}/api/corridor/incoming_platoon"
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=1.5) as response:
                pass
        except Exception as e:
            logging.debug(f"Falla de comunicación de corredor con {target_url}: {e}")

    def receive_incoming_platoon(self, payload):
        """
        Recibe una alerta de pelotón entrante y activa la preparación de fase verde.
        """
        now = time.time()
        origin = payload.get("origin_node", "NODO_EXTERNO")
        v_count = payload.get("vehicle_count", 3)
        eta = payload.get("eta_seconds", 15.0)

        with self.lock:
            self.active_green_wave = True
            # La ventana de ola verde dura desde el ETA estimado hasta 15 segundos después
            self.green_wave_expiry = now + eta + 15.0
            self.green_wave_origin = origin

            event = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "origin": origin,
                "vehicles": v_count,
                "eta_sec": eta,
                "status": "OLA_VERDE_ACTIVA"
            }
            self.wave_history.append(event)
            if len(self.wave_history) > 20:
                self.wave_history.pop(0)

        logging.info(f"🟢 OLA VERDE RECIBIDA: Pelotón de {v_count} veh llegando desde {origin} en {eta}s. Adaptando ciclo.")

    def should_prioritize_green_wave(self):
        """
        Consulta si la FSM debe favorecer o extender la fase verde debido a una ola verde activa.
        """
        now = time.time()
        with self.lock:
            if self.active_green_wave:
                if now < self.green_wave_expiry:
                    return True, self.green_wave_origin, round(self.green_wave_expiry - now, 1)
                else:
                    self.active_green_wave = False
                    self.green_wave_origin = None
            return False, None, 0.0

    def get_status(self):
        """Retorna el estado completo del corredor para el SCADA C5"""
        is_active, origin, remaining = self.should_prioritize_green_wave()
        with self.lock:
            return {
                "corridor_name": self.corridor_name,
                "current_node_id": self.current_node_id,
                "avg_speed_kmh": self.avg_speed_kmh,
                "green_wave_active": is_active,
                "green_wave_origin": origin,
                "green_wave_remaining_sec": remaining,
                "nodes": [node.to_dict() for node in self.nodes.values()],
                "recent_waves": list(reversed(self.wave_history[-5:]))
            }
