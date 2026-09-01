# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Interfaz de Línea de Comandos (CLI) y Despachador de Topologías Viales
Desarrollador Principal y Titular de Derechos: Moisés Emilio Martínez Arias
Todos los derechos reservados © 2026.
"""

import os
import sys
import argparse
import socket
import json

# Agregar directorio src al path
sys.path.append(os.path.dirname(__file__))

TOPOLOGIAS_DISPONIBLES = {
    "4_way": {
        "descripcion": "Intersección clásica de 4 vías (Eje Norte-Sur vs Eje Este-Oeste)",
        "cpu_module": "ui4_way_cpu",
        "cpu_controller": "SemaforoController4V_CPU",
        "cpu_gui_app": "App4V_CPU",
        "rknn_module": "ui4_way",
        "rknn_controller": "SemaforoController4V_RKNN",
        "rknn_gui_app": "App4V_RKNN"
    },
    "2_way": {
        "descripcion": "Avenida continua de 2 vías (Sentido A vs Sentido B)",
        "cpu_module": "ui2_way_cpu",
        "cpu_controller": "SemaforoController2V_CPU",
        "cpu_gui_app": "App2V_CPU",
        "rknn_module": "ui2_way",
        "rknn_controller": "SemaforoController2V_RKNN",
        "rknn_gui_app": "App2V_RKNN"
    },
    "3_way_t": {
        "descripcion": "Intersección en T de 3 vías (Vía Principal vs Calle Secundaria)",
        "cpu_module": "ui3_tee_cpu",
        "cpu_controller": "SemaforoController3V_CPU",
        "cpu_gui_app": "App3V_CPU",
        "rknn_module": "ui3_tee",
        "rknn_controller": "SemaforoController3V_RKNN",
        "rknn_gui_app": "App3V_RKNN"
    },
    "4_way_protected": {
        "descripcion": "Intersección de 4 vías con fase de Giro a la Izquierda Protegido (Phase-skipping)",
        "cpu_module": "ui4_protected_cpu",
        "cpu_controller": "SemaforoController4VProtected_CPU",
        "cpu_gui_app": "App4VProtected_CPU",
        "rknn_module": "ui4_protected",
        "rknn_controller": "SemaforoController4VProtected_RKNN",
        "rknn_gui_app": "App4VProtected_RKNN"
    },
    "pedestrian": {
        "descripcion": "Cruce Peatonal Inteligente Mid-block con detección de personas y demanda",
        "cpu_module": "ui_pedestrian_cpu",
        "cpu_controller": "SemaforoControllerPedestrian_CPU",
        "cpu_gui_app": "AppPedestrian_CPU",
        "rknn_module": "ui_pedestrian",
        "rknn_controller": "SemaforoControllerPedestrian_RKNN",
        "rknn_gui_app": "AppPedestrian_RKNN"
    }
}

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def print_banner(topology, backend, is_headless, port):
    ip = get_local_ip()
    print("=" * 72)
    print("   FLUXA: CONTROL SEMAFÓRICO INTELIGENTE Y TELEMETRÍA EDGE")
    print("   Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM")
    print("   Desarrollador Principal: Moisés Emilio Martínez Arias")
    print("=" * 72)
    print(f"Topología Activa:   {topology.upper()} ({TOPOLOGIAS_DISPONIBLES[topology]['descripcion']})")
    print(f"Motor Inferencia:   {backend.upper()}")
    print(f"Modo de Operación:  {'HEADLESS (Servicio de Fondo)' if is_headless else 'DESKTOP GUI'}")
    print(f"Consola WebUI:      http://{ip}:{port} (o http://localhost:{port})")
    print(f"Streaming MJPEG:    http://{ip}:{port}/video_feed")
    print(f"API Telemetría:     http://{ip}:{port}/api/status")
    print("=" * 72)
    print()

def ejecutar_cli():
    parser = argparse.ArgumentParser(
        description="FLUXA - Sistema Industrial de Semáforos Inteligentes Edge con IA y Telemetría",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de Uso:
  python3 main.py --topology 4_way --backend cpu --headless
  python3 main.py --topology 3_way_t --backend rknn --headless --port 5000
  python3 main.py --topology pedestrian --backend cpu --headless
  python3 main.py --topology 4_way_protected --backend cpu --gui
  python3 main.py --list-topologies
        """
    )

    parser.add_argument(
        "--topology", "-t",
        choices=list(TOPOLOGIAS_DISPONIBLES.keys()),
        default="4_way",
        help="Topología vial de la intersección (por defecto: 4_way)"
    )

    parser.add_argument(
        "--backend", "-b",
        choices=["cpu", "rknn"],
        default="cpu",
        help="Motor de inferencia: 'cpu' (PyTorch/ONNX) o 'rknn' (Orange Pi 5 NPU RK3588)"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Ejecutar en modo Headless sin interfaz gráfica de escritorio (por defecto: True)"
    )

    parser.add_argument(
        "--gui",
        action="store_true",
        help="Ejecutar con interfaz gráfica de escritorio Tkinter (para pruebas con monitor)"
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        default=5000,
        help="Puerto TCP para el servidor WebUI y API REST (por defecto: 5000)"
    )

    parser.add_argument(
        "--video", "-v",
        type=str,
        default=None,
        help="Ruta a un archivo de video de demostración o flujo RTSP (ej: videos/demo.mp4)"
    )

    parser.add_argument(
        "--npu-core",
        choices=["0", "1", "2", "all"],
        default=None,
        help="Núcleo NPU RK3588 asignado para Orange Pi 5: '0', '1', '2' o 'all' (por defecto: all)"
    )

    parser.add_argument(
        "--list-topologies",
        action="store_true",
        help="Listar todas las topologías viales soportadas y salir"
    )

    args = parser.parse_args()

    if args.list_topologies:
        print("\n Topologías Viales Soportadas en FLUXA:")
        for k, v in TOPOLOGIAS_DISPONIBLES.items():
            print(f"  • {k:<18} : {v['descripcion']}")
        print()
        sys.exit(0)

    # Si se especificó --gui explícitamente, desactivar headless
    is_headless = not args.gui

    topology_info = TOPOLOGIAS_DISPONIBLES[args.topology]
    print_banner(args.topology, args.backend, is_headless, args.port)
    if args.video:
        print(f" Fuente de video especificada por CLI: {args.video}\n")
    if args.npu_core and args.backend == "rknn":
        print(f"Núcleo NPU RK3588 asignado: Core {args.npu_core}\n")

    # Instanciar el controlador según backend
    if args.backend == "cpu":
        mod = __import__(topology_info["cpu_module"])
        if is_headless:
            controller_cls = getattr(mod, topology_info["cpu_controller"])
            controller = controller_cls(port=args.port, video_source=args.video)
            controller.run_headless()
        else:
            tk = getattr(mod, "tk", None)
            if tk is None or not getattr(mod, "TKINTER_AVAILABLE", True):
                print("\n❌ Error: La interfaz gráfica de escritorio (--gui) requiere Tkinter.")
                print(" Solución:")
                print("   • En Ubuntu/Debian/Armbian:  sudo apt install python3-tk")
                print("   • En Fedora/RHEL:           sudo dnf install python3-tkinter")
                print("   • O ejecuta en modo Headless (WebUI): python3 main.py --headless\n")
                sys.exit(1)
            gui_cls = getattr(mod, topology_info["cpu_gui_app"])
            ventana = tk.Tk()
            app = gui_cls(ventana, video_source=args.video)
            ventana.mainloop()
    else:
        mod = __import__(topology_info["rknn_module"])
        if is_headless:
            controller_cls = getattr(mod, topology_info["rknn_controller"])
            controller = controller_cls(port=args.port, video_source=args.video, npu_core_id=args.npu_core)
            controller.run_headless()
        else:
            tk = getattr(mod, "tk", None)
            if tk is None or not getattr(mod, "TKINTER_AVAILABLE", True):
                print("\n❌ Error: La interfaz gráfica de escritorio (--gui) requiere Tkinter.")
                print(" Solución:")
                print("   • En Ubuntu/Debian/Armbian:  sudo apt install python3-tk")
                print("   • En Fedora/RHEL:           sudo dnf install python3-tkinter")
                print("   • O ejecuta en modo Headless (WebUI): python3 main.py --backend rknn --headless\n")
                sys.exit(1)
            gui_cls = getattr(mod, topology_info["rknn_gui_app"])
            ventana = tk.Tk()
            app = gui_cls(ventana, video_source=args.video)
            ventana.mainloop()

if __name__ == "__main__":
    ejecutar_cli()
