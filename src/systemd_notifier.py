# -*- coding: utf-8 -*-
"""
==============================================================================
 FLUXA Smart Mobility • Notificador Nativo para Systemd Watchdog
 Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
 Desarrollador Principal: Moisés Emilio Martínez Arias
==============================================================================
Implementación ligera y resiliente del protocolo de notificación sd_notify(3)
utilizando sockets de datagrama UNIX nativos (AF_UNIX / SOCK_DGRAM).

No requiere bibliotecas C externas (libsystemd) ni dependencias adicionales,
lo que garantiza compatibilidad universal en Orange Pi 5 (RK3588) y x86_64.
"""

import os
import socket
import time
import logging
from typing import Optional


class SystemdNotifier:
    """
    Gestiona los latidos del Watchdog y cambios de estado hacia Systemd.
    Si el proceso se ejecuta fuera de systemd (ej. pruebas manuales o desarrollo),
    opera en modo No-Op transparente sin penalizaciones de rendimiento.
    """

    def __init__(self, watchdog_interval_sec: float = 2.0):
        self.notify_socket_path = os.environ.get("NOTIFY_SOCKET")
        self.watchdog_interval_sec = watchdog_interval_sec
        self._last_watchdog_time = 0.0
        self.enabled = bool(self.notify_socket_path)

    def notify(self, state: str) -> bool:
        """
        Envía un comando de estado a systemd a través del socket UNIX especificado
        en la variable de entorno NOTIFY_SOCKET.
        """
        if not self.notify_socket_path:
            return False

        path = self.notify_socket_path
        # Manejo de sockets abstractos de Linux (inician con @)
        if path.startswith("@"):
            path = "\0" + path[1:]

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
                sock.settimeout(0.5)
                sock.connect(path)
                sock.sendall(state.encode("utf-8"))
            return True
        except Exception as e:
            # En sistemas embebidos, una falla en el socket de notificación
            # no debe derribar la lógica del semáforo.
            logging.debug(f"SystemdNotifier: no fue posible enviar estado '{state}': {e}")
            return False

    def notify_ready(self) -> bool:
        """Indica a systemd que el servicio completó la inicialización y está operativo."""
        return self.notify("READY=1")

    def notify_watchdog(self, force: bool = False) -> bool:
        """
        Envía el pulso de vida WATCHDOG=1 con limitación de frecuencia (rate limit).
        Evita saturar el socket si el ciclo de inferencia opera a 30+ FPS.
        """
        now = time.time()
        if force or (now - self._last_watchdog_time >= self.watchdog_interval_sec):
            success = self.notify("WATCHDOG=1")
            if success:
                self._last_watchdog_time = now
            return success
        return False

    def notify_status(self, status_message: str) -> bool:
        """Actualiza la línea de estado descriptiva visible en 'systemctl status'."""
        clean_status = status_message.replace("\n", " ").strip()
        return self.notify(f"STATUS={clean_status}")

    def notify_stopping(self) -> bool:
        """Informa que el servicio inició la secuencia ordenada de apagado."""
        return self.notify("STOPPING=1")


# Instancia singleton predeterminada
_default_notifier: Optional[SystemdNotifier] = None


def get_notifier() -> SystemdNotifier:
    global _default_notifier
    if _default_notifier is None:
        _default_notifier = SystemdNotifier()
    return _default_notifier
