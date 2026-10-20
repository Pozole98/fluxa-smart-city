#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 FLUXA Smart Mobility • Migrador y Fusionador Inteligente de Configuración
 Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
 Desarrollador Principal: Moisés Emilio Martínez Arias
==============================================================================
Este script realiza una migración y fusión profunda (deep merge) no destructiva
entre la plantilla de configuración del sistema (config.example.json) y el archivo
de configuración en producción (config.json).

Garantías de seguridad vial y resiliencia:
1. Preservación absoluta de la calibración geométrica de zonas (ROI) y hardware.
2. Inyección recursiva de nuevas claves de configuración introducidas en updates.
3. Respaldo atómico previo con marca de tiempo (config.json.bak.YYYYMMDD_HHMMSS).
4. Escritura atómica vía fsync y replace para inmunidad contra cortes de energía.
5. Modos --check y --dry-run para integración con el pipeline de actualización.
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from typing import Dict, Any, Tuple, List


def deep_merge(template: Any, current: Any, path: str = "") -> Tuple[Any, List[str], List[str]]:
    """
    Fusiona recursivamente template y current.
    - Preserva los valores existentes en current.
    - Incorpora claves nuevas de template que falten en current.
    - Registra claves añadidas y discrepancias de tipo.
    """
    added_keys = []
    type_warnings = []

    # Si el valor de current es None o no existe, adoptamos el template
    if current is None:
        return template, [path] if path else [], type_warnings

    # Si ambos son diccionarios, fusionar recursivamente
    if isinstance(template, dict) and isinstance(current, dict):
        merged = dict(current)
        for key, val in template.items():
            sub_path = f"{path}.{key}" if path else key
            if key not in current:
                merged[key] = val
                added_keys.append(sub_path)
            else:
                merged_val, sub_added, sub_warn = deep_merge(val, current[key], sub_path)
                merged[key] = merged_val
                added_keys.extend(sub_added)
                type_warnings.extend(sub_warn)
        return merged, added_keys, type_warnings

    # Si los tipos son incompatibles (y ninguno es None)
    if type(template) != type(current):
        # Excepción admisible: int y float en valores numéricos
        if isinstance(template, (int, float)) and isinstance(current, (int, float)):
            return current, added_keys, type_warnings

        type_warnings.append(
            f"Discrepancia de tipo en '{path}': plantilla={type(template).__name__}, "
            f"actual={type(current).__name__}. Conservando valor actual de producción."
        )
        return current, added_keys, type_warnings

    # Para tipos primitivos o listas, se conserva el valor actual del usuario
    return current, added_keys, type_warnings


def migrate_config(
    current_path: str,
    template_path: str,
    output_path: str = None,
    backup_dir: str = None,
    dry_run: bool = False,
    check_only: bool = False
) -> Dict[str, Any]:
    """
    Ejecuta el proceso completo de verificación, respaldo y migración.
    """
    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"Plantilla no encontrada en: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        try:
            template_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error sintáctico en la plantilla {template_path}: {e}")

    # Si no existe el archivo actual, crearlo copiando la plantilla
    if not os.path.isfile(current_path):
        if check_only:
            return {"status": "needs_migration", "reason": "current_config_missing", "added_keys": list(template_data.keys())}
        
        target_out = output_path or current_path
        if dry_run:
            return {
                "status": "dry_run",
                "action": "initialize_from_template",
                "added_keys": list(template_data.keys()),
                "warnings": []
            }
        
        os.makedirs(os.path.dirname(os.path.abspath(target_out)), exist_ok=True)
        with open(target_out, "w", encoding="utf-8") as f:
            json.dump(template_data, f, indent=4, ensure_ascii=False)
            f.write("\n")
        return {
            "status": "initialized",
            "message": f"Configuración inicializada desde plantilla en {target_out}",
            "added_keys": list(template_data.keys()),
            "warnings": []
        }

    with open(current_path, "r", encoding="utf-8") as f:
        try:
            current_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error de formato JSON en el archivo actual {current_path}: {e}")

    merged_data, added_keys, warnings = deep_merge(template_data, current_data)

    needs_migration = len(added_keys) > 0

    if check_only:
        return {
            "status": "needs_migration" if needs_migration else "up_to_date",
            "added_keys": added_keys,
            "warnings": warnings
        }

    if dry_run:
        return {
            "status": "dry_run",
            "needs_migration": needs_migration,
            "added_keys": added_keys,
            "warnings": warnings,
            "preview": merged_data if needs_migration else None
        }

    if not needs_migration:
        return {
            "status": "up_to_date",
            "message": "La configuración ya se encuentra sincronizada con la plantilla.",
            "added_keys": [],
            "warnings": warnings
        }

    target_out = output_path or current_path
    target_dir = os.path.dirname(os.path.abspath(target_out))
    os.makedirs(target_dir, exist_ok=True)

    # 1. Crear respaldo previo antes de modificar
    backup_folder = backup_dir or target_dir
    os.makedirs(backup_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{os.path.basename(current_path)}.bak.{timestamp}"
    backup_path = os.path.join(backup_folder, backup_filename)

    shutil.copy2(current_path, backup_path)

    # 2. Escritura atómica con fsync y rename
    tmp_target = f"{target_out}.tmp.{os.getpid()}"
    try:
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(merged_data, f, indent=4, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_target, target_out)
    finally:
        if os.path.exists(tmp_target):
            try:
                os.remove(tmp_target)
            except OSError:
                pass

    return {
        "status": "migrated",
        "backup_path": backup_path,
        "output_path": target_out,
        "added_keys": added_keys,
        "warnings": warnings
    }


def main():
    parser = argparse.ArgumentParser(
        description="FLUXA - Migrador y Fusionador No Destructivo de Configuración",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, ".."))

    default_config = os.path.join(repo_root, "config.json")
    default_template = os.path.join(repo_root, "config.example.json")

    parser.add_argument("--config", "--input", dest="config_path", default=default_config,
                        help=f"Ruta al archivo config.json actual (default: {default_config})")
    parser.add_argument("--template", dest="template_path", default=default_template,
                        help=f"Ruta a la plantilla config.example.json (default: {default_template})")
    parser.add_argument("--output", dest="output_path", default=None,
                        help="Ruta destino (por defecto sobreescribe atómicamente el archivo de entrada)")
    parser.add_argument("--backup-dir", dest="backup_dir", default=None,
                        help="Directorio donde almacenar el respaldo timestamped")
    parser.add_argument("--check", action="store_true",
                        help="Solo verifica si se requiere migración; sale con 0 si está al día, 1 si requiere cambios")
    parser.add_argument("--dry-run", action="store_true",
                        help="Muestra los cambios que se aplicarían sin modificar archivos en disco")
    parser.add_argument("--json", dest="json_output", action="store_true",
                        help="Imprime el resultado estructurado en formato JSON")

    args = parser.parse_args()

    try:
        result = migrate_config(
            current_path=args.config_path,
            template_path=args.template_path,
            output_path=args.output_path,
            backup_dir=args.backup_dir,
            dry_run=args.dry_run,
            check_only=args.check
        )
    except Exception as e:
        if args.json_output:
            print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            print(f"❌ Error en migración de configuración: {e}", file=sys.stderr)
        sys.exit(2)

    if args.json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.check:
            sys.exit(0 if result["status"] == "up_to_date" else 1)
        return

    # Salida estándar legible para terminal
    status = result["status"]
    if status == "up_to_date":
        print("✅ La configuración está al día. No se requieren cambios.")
        if result.get("warnings"):
            for w in result["warnings"]:
                print(f"⚠️  {w}")
        sys.exit(0)
    elif status == "needs_migration":
        print("⚠️  La configuración requiere migración. Claves faltantes detectadas:")
        for k in result.get("added_keys", []):
            print(f"   + {k}")
        sys.exit(1)
    elif status == "dry_run":
        print("🔍 Simulación (Dry Run) de migración:")
        if result.get("needs_migration"):
            print("Nuevas claves a incorporar:")
            for k in result.get("added_keys", []):
                print(f"   + {k}")
        else:
            print("No hay claves pendientes de incorporar.")
        if result.get("warnings"):
            for w in result["warnings"]:
                print(f"⚠️  {w}")
        sys.exit(0)
    elif status == "migrated":
        print("✅ Migración de configuración completada exitosamente.")
        print(f"   Respaldo de seguridad creado en: {result['backup_path']}")
        print(f"   Archivo actualizado: {result['output_path']}")
        print(f"   Claves añadidas ({len(result['added_keys'])}):")
        for k in result["added_keys"]:
            print(f"   + {k}")
        if result.get("warnings"):
            print("\nAdvertencias:")
            for w in result["warnings"]:
                print(f"⚠️  {w}")
        sys.exit(0)
    elif status == "initialized":
        print(f"✅ {result['message']}")
        sys.exit(0)


if __name__ == "__main__":
    main()
