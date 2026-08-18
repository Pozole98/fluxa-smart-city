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

def set_password():
    print("\n" + "=" * 65)
    print("🔐 FLUXA SMART CITY • GESTOR DE CREDENCIALES DE ADMINISTRADOR C5")
    print("=" * 65)
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    instance_dir = os.path.join(base_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    creds_file = os.path.join(instance_dir, 'admin_credentials.json')

    user = input("\n👤 Ingrese el nombre de usuario administrador [admin]: ").strip()
    if not user:
        user = "admin"

    while True:
        pwd1 = getpass.getpass("🔑 Ingrese la nueva contraseña para el operador C5: ")
        if len(pwd1) < 6:
            print("⚠️ La contraseña debe contener al menos 6 caracteres. Intente de nuevo.")
            continue
            
        pwd2 = getpass.getpass("🔁 Confirme la nueva contraseña: ")
        if pwd1 != pwd2:
            print("❌ Las contraseñas no coinciden. Intente de nuevo.\n")
            continue
        break

    # Generar hash criptográfico seguro
    pass_hash = generate_password_hash(pwd1)
    
    data = {
        "enabled": True,
        "admin_user": user,
        "admin_pass_hash": pass_hash,
        "updated_at": datetime.now().isoformat()
    }

    try:
        with open(creds_file, 'w') as f:
            json.dump(data, f, indent=4)
        os.chmod(creds_file, 0o600)
        print("\n" + "=" * 65)
        print(f"✅ ¡Contraseña actualizada exitosamente para el usuario '{user}'!")
        print(f"📁 Credencial hasheada guardada en: {creds_file}")
        print("🔒 Permisos restringidos a 600 (Solo lectura/escritura del propietario).")
        print("=" * 65 + "\n")
    except Exception as e:
        print(f"❌ Error al guardar las credenciales: {e}")
        sys.exit(1)

if __name__ == '__main__':
    set_password()
