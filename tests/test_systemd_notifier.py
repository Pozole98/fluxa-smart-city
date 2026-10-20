#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas Unitarias para el Notificador de Systemd Watchdog (src/systemd_notifier.py)
"""

import os
import sys
import socket
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.systemd_notifier import SystemdNotifier


class TestSystemdNotifier(unittest.TestCase):

    def test_noop_when_not_under_systemd(self):
        # Asegurarse de que NOTIFY_SOCKET no esté configurado
        orig_env = os.environ.pop("NOTIFY_SOCKET", None)
        try:
            notifier = SystemdNotifier()
            self.assertFalse(notifier.enabled)
            self.assertFalse(notifier.notify_ready())
            self.assertFalse(notifier.notify_watchdog(force=True))
            self.assertFalse(notifier.notify_status("Test status"))
            self.assertFalse(notifier.notify_stopping())
        finally:
            if orig_env is not None:
                os.environ["NOTIFY_SOCKET"] = orig_env

    def test_notify_delivers_packet_over_unix_datagram(self):
        tmp_dir = tempfile.mkdtemp()
        socket_path = os.path.join(tmp_dir, "systemd_test.sock")

        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        server_sock.bind(socket_path)
        server_sock.settimeout(2.0)

        try:
            os.environ["NOTIFY_SOCKET"] = socket_path
            notifier = SystemdNotifier(watchdog_interval_sec=0.1)
            self.assertTrue(notifier.enabled)

            # 1. Enviar READY=1
            self.assertTrue(notifier.notify_ready())
            data, _ = server_sock.recvfrom(1024)
            self.assertEqual(data.decode("utf-8"), "READY=1")

            # 2. Enviar WATCHDOG=1
            self.assertTrue(notifier.notify_watchdog(force=True))
            data, _ = server_sock.recvfrom(1024)
            self.assertEqual(data.decode("utf-8"), "WATCHDOG=1")

            # 3. Enviar STATUS
            self.assertTrue(notifier.notify_status("Operando | 30 FPS"))
            data, _ = server_sock.recvfrom(1024)
            self.assertEqual(data.decode("utf-8"), "STATUS=Operando | 30 FPS")

            # 4. Enviar STOPPING=1
            self.assertTrue(notifier.notify_stopping())
            data, _ = server_sock.recvfrom(1024)
            self.assertEqual(data.decode("utf-8"), "STOPPING=1")
        finally:
            server_sock.close()
            if os.path.exists(socket_path):
                os.remove(socket_path)
            os.rmdir(tmp_dir)
            os.environ.pop("NOTIFY_SOCKET", None)


if __name__ == "__main__":
    unittest.main()
