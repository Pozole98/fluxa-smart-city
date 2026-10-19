# -*- coding: utf-8 -*-
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from arduino_locker import ArduinoDeviceLock, inspect_port_lock, get_lock_file_path

def test_arduino_locker_virtual():
    locker = ArduinoDeviceLock(node_port=5000)
    assert locker.acquire("VIRTUAL") is True
    assert locker.current_device == "VIRTUAL"
    locker.release()
    assert locker.current_device is None

def test_arduino_locker_exclusive():
    test_device = "/dev/ttyTestDummy0"
    locker1 = ArduinoDeviceLock(node_port=5000)
    locker2 = ArduinoDeviceLock(node_port=5001)

    # Nodo 1 secuestra el puerto
    assert locker1.acquire(test_device) is True
    assert locker1.current_device == test_device

    # Inspeccionar estado: debe figurar ocupado/propio
    info1 = inspect_port_lock(test_device, current_node_port=5000)
    assert info1["is_locked"] is True
    assert info1["is_mine"] is True
    assert info1["status"] == "propio"

    info2 = inspect_port_lock(test_device, current_node_port=5001)
    assert info2["is_locked"] is True
    assert info2["is_mine"] is False
    assert info2["status"] == "ocupado"
    assert "5000" in str(info2["owner"])

    # Nodo 2 intenta secuestrar el mismo puerto: DEBE FALLAR
    assert locker2.acquire(test_device) is False
    assert locker2.current_device is None

    # Nodo 1 libera el puerto
    locker1.release()

    # Ahora debe figurar disponible
    info_free = inspect_port_lock(test_device, current_node_port=5001)
    assert info_free["is_locked"] is False
    assert info_free["status"] == "disponible"

    # Nodo 2 ahora sí puede secuestrarlo
    assert locker2.acquire(test_device) is True
    assert locker2.current_device == test_device

    locker2.release()

def test_three_nodes_distinct_devices():
    """Verifica que 3 nodos en la Orange Pi 5 puedan secuestrar 3 Arduinos distintos concurrentemente"""
    dev0 = "/dev/ttyTestNode0"
    dev1 = "/dev/ttyTestNode1"
    dev2 = "/dev/ttyTestNode2"

    lock0 = ArduinoDeviceLock(node_port=5000)
    lock1 = ArduinoDeviceLock(node_port=5001)
    lock2 = ArduinoDeviceLock(node_port=5002)

    assert lock0.acquire(dev0) is True
    assert lock1.acquire(dev1) is True
    assert lock2.acquire(dev2) is True

    # Ninguno puede secuestrar el del otro
    assert lock0.acquire(dev1) is False
    assert lock1.acquire(dev2) is False
    assert lock2.acquire(dev0) is False

    # Liberación
    lock0.release()
    lock1.release()
    lock2.release()

def test_switch_ports_cleanly():
    """Verifica que cambiar de un puerto libre a otro libere el anterior y tome el nuevo."""
    devA = "/dev/ttySwitchA"
    devB = "/dev/ttySwitchB"

    locker = ArduinoDeviceLock(node_port=5000)
    assert locker.acquire(devA) is True
    assert locker.current_device == devA

    # Cambiar a devB
    assert locker.acquire(devB) is True
    assert locker.current_device == devB

    # devA ahora debe estar libre
    infoA = inspect_port_lock(devA, current_node_port=5000)
    assert infoA["is_locked"] is False

    # devB debe figurar como propio
    infoB = inspect_port_lock(devB, current_node_port=5000)
    assert infoB["is_locked"] is True
    assert infoB["is_mine"] is True

    locker.release()
