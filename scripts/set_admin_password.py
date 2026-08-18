#!/usr/bin/env python3
"""
FLUXA - Gestor de Credenciales de Administrador C5
Permite fijar o actualizar interactivamente la contraseña del operador C5 de forma segura,
almacenándola como un hash criptográfico (PBKDF2-SHA256) sin exponer texto plano.
"""

import os
import sys
import json
import getpass
from datetime import datetime

try:
    from werkzeug.security import generate_password_hash
except ImportError:
    print("❌ Error: Werkzeug no está instalado en el entorno Python actual.")
    print("💡 Ejecuta: pip install werkzeug")
    sys.exit(1)

import argparse

def set_password(username=None, password=None):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    instance_dir = os.path.join(base_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    creds_file = os.path.join(instance_dir, 'admin_credentials.json')

    if not username:
        print("\n" + "=" * 65)
        print("🔐 FLUXA SMART CITY • GESTOR DE CREDENCIALES DE ADMINISTRADOR C5")
        print("=" * 65)
        username = input("\n👤 Ingrese el nombre de usuario administrador [admin]: ").strip()
        if not username:
            username = "admin"

    if not password:
        while True:
            pwd1 = getpass.getpass("🔑 Ingrese la nueva contraseña para el operador C5: ")
            if len(pwd1) < 4:
                print("⚠️ La contraseña debe contener al menos 4 caracteres. Intente de nuevo.")
                continue
                
            pwd2 = getpass.getpass("🔁 Confirme la nueva contraseña: ")
            if pwd1 != pwd2:
                print("❌ Las contraseñas no coinciden. Intente de nuevo.\n")
                continue
            password = pwd1
            break

    # Generar hash criptográfico seguro
    pass_hash = generate_password_hash(password)
    
    data = {
        "enabled": True,
        "admin_user": username,
        "admin_pass_hash": pass_hash,
        "updated_at": datetime.now().isoformat()
    }

    try:
        with open(creds_file, 'w') as f:
            json.dump(data, f, indent=4)
        os.chmod(creds_file, 0o600)
        print("\n" + "=" * 65)
        print(f"✅ ¡Contraseña configurada exitosamente para el usuario '{username}'!")
        print(f"📁 Credencial hasheada guardada en: {creds_file}")
        print("🔒 Permisos restringidos a 600 (Solo lectura/escritura del propietario).")
        print("=" * 65 + "\n")
    except Exception as e:
        print(f"❌ Error al guardar las credenciales: {e}")
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Configuración de Credenciales de Administrador FLUXA C5")
    parser.add_argument("--username", type=str, default=None, help="Nombre de usuario administrador")
    parser.add_argument("--password", type=str, default=None, help="Contraseña en texto plano a hashear")
    parser.add_argument("--force", action="store_true", help="Forzar escritura")
    args = parser.parse_args()
    set_password(username=args.username, password=args.password)
