#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 FLUXA Smart Mobility • Gestor de Migraciones de Base de Datos MariaDB
 Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
 Desarrollador Principal: Moisés Emilio Martínez Arias
==============================================================================
Este script administra de forma transaccional e idempotente las migraciones de
esquema en MariaDB para cruces viales y clusters de semáforos inteligentes.

Características de robustez y seguridad de grado industrial:
1. Tabla de control canónica `schema_migrations` (version, applied_at, checksum).
2. Detección automática de instalaciones preexistentes: si las tablas del sistema
   ya existen, adopta 001_baseline sin ejecutar DDL redundantes.
3. Snapshot lógico atómico previo con `mariadb-dump` / `mysqldump` con permisos
   600 y compresión gzip antes de aplicar DDL (necesario por el COMMIT implícito
   de MariaDB en operaciones DDL).
4. CLI versátil con soporte para --check, --dry-run, --status, --json y --rollback.
5. Inmunidad a inyección de credenciales mediante --defaults-extra-file y pymysql.
"""

import os
import sys
import gzip
import json
import glob
import hashlib
import tempfile
import argparse
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

try:
    import pymysql
    PYMYSQL_AVAILABLE = True
except ImportError:
    pymysql = None
    PYMYSQL_AVAILABLE = False


def load_env_file(env_path: str):
    """Carga variables simples desde un archivo .env si existen y no están en os.environ"""
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


def compute_file_checksum(filepath: str) -> str:
    """Calcula el hash SHA-256 del contenido de un archivo de migración"""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class DatabaseMigrator:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        migrations_dir: Optional[str] = None,
        backup_dir: Optional[str] = None
    ):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(script_dir, ".."))
        load_env_file(os.path.join(repo_root, ".env"))

        self.host = host or os.environ.get("DATABASE_HOST", "localhost")
        self.port = int(port or os.environ.get("DATABASE_PORT", 3306))
        self.user = user or os.environ.get("DATABASE_USER", "fluxa")
        self.password = password or os.environ.get("DATABASE_PASSWORD", "")
        self.database = database or os.environ.get("DATABASE_NAME", "fluxa_traffic")

        self.migrations_dir = migrations_dir or os.path.join(repo_root, "migrations")
        self.backup_dir = backup_dir or os.path.join(repo_root, "backups", "db")

        self._find_cli_tools()

    def _find_cli_tools(self):
        """Identifica los ejecutables del cliente MariaDB/MySQL en el sistema"""
        self.mysql_bin = shutil_which("mariadb") or shutil_which("mysql")
        self.dump_bin = shutil_which("mariadb-dump") or shutil_which("mysqldump")

    def get_connection(self):
        """Establece conexión directa con MariaDB vía pymysql o aborta con mensaje claro"""
        if not PYMYSQL_AVAILABLE:
            raise RuntimeError(
                "La librería 'pymysql' no está instalada en el entorno Python actual.\n"
                "Instale las dependencias desde requirements.txt o ejecute en el entorno virtual .venv."
            )
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=5,
            cursorclass=pymysql.cursors.DictCursor
        )

    def _execute_sql_via_cli(self, sql_commands: str) -> None:
        """Ejecuta SQL usando el cliente CLI oficial con defaults-extra-file seguro"""
        if not self.mysql_bin:
            raise RuntimeError("No se encontró el binario cliente 'mariadb' ni 'mysql' en el sistema.")

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as cnf:
            cnf_path = cnf.name
            cnf.write(f"[client]\nhost='{self.host}'\nport='{self.port}'\nuser='{self.user}'\npassword='{self.password}'\n")
        
        try:
            os.chmod(cnf_path, 0o600)
            proc = subprocess.run(
                [self.mysql_bin, f"--defaults-extra-file={cnf_path}", self.database],
                input=sql_commands,
                text=True,
                capture_output=True
            )
            if proc.returncode != 0:
                raise RuntimeError(f"Error ejecutando SQL por CLI: {proc.stderr.strip()}")
        finally:
            if os.path.exists(cnf_path):
                os.remove(cnf_path)

    def ensure_migrations_table(self, conn) -> None:
        """Crea la tabla de control schema_migrations si no existe"""
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(100) PRIMARY KEY,
                    applied_at DATETIME NOT NULL,
                    checksum VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

    def get_existing_tables(self, conn) -> List[str]:
        """Obtiene la lista de tablas existentes en la base de datos"""
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES;")
            rows = cur.fetchall()
            tables = []
            for r in rows:
                tables.append(list(r.values())[0])
            return tables

    def get_applied_migrations(self, conn) -> Dict[str, Dict[str, Any]]:
        """Devuelve diccionario {version: {applied_at, checksum}}"""
        self.ensure_migrations_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT version, applied_at, checksum FROM schema_migrations ORDER BY version ASC;")
            rows = cur.fetchall()
            return {
                r["version"]: {
                    "applied_at": r["applied_at"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(r["applied_at"], datetime) else str(r["applied_at"]),
                    "checksum": r["checksum"]
                }
                for r in rows
            }

    def get_available_migrations(self) -> List[Dict[str, Any]]:
        """Obtiene y ordena todos los archivos .sql en el directorio de migraciones"""
        if not os.path.isdir(self.migrations_dir):
            return []
        files = sorted(glob.glob(os.path.join(self.migrations_dir, "*.sql")))
        migrations = []
        for f in files:
            version = os.path.splitext(os.path.basename(f))[0]
            checksum = compute_file_checksum(f)
            migrations.append({
                "version": version,
                "filepath": f,
                "checksum": checksum
            })
        return migrations

    def create_database_snapshot(self) -> str:
        """
        Genera un dump lógico completo (mysqldump / mariadb-dump) antes de aplicar DDL.
        Protege las credenciales mediante archivo temporal 600 y comprime en gzip.
        """
        if not self.dump_bin:
            raise RuntimeError(
                "No se encontró 'mariadb-dump' ni 'mysqldump' en el sistema. "
                "Instale mariadb-client o use --no-backup bajo su propio riesgo."
            )

        os.makedirs(self.backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"db_{self.database}_pre_migration_{timestamp}.sql.gz"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as cnf:
            cnf_path = cnf.name
            cnf.write(f"[client]\nhost='{self.host}'\nport='{self.port}'\nuser='{self.user}'\npassword='{self.password}'\n")

        try:
            os.chmod(cnf_path, 0o600)
            cmd = [
                self.dump_bin,
                f"--defaults-extra-file={cnf_path}",
                "--single-transaction",
                "--quick",
                "--routines",
                "--triggers",
                self.database
            ]
            with open(backup_path, "wb") as f_out:
                with gzip.GzipFile(filename="", mode="wb", fileobj=f_out, mtime=0) as gz_out:
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    while True:
                        chunk = proc.stdout.read(65536)
                        if not chunk:
                            break
                        gz_out.write(chunk)
                    stderr = proc.stderr.read().decode("utf-8", errors="replace")
                    proc.wait()

            if proc.returncode != 0:
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                raise RuntimeError(f"Fallo en generación de snapshot MariaDB: {stderr.strip()}")

            os.chmod(backup_path, 0o600)
            return backup_path
        finally:
            if os.path.exists(cnf_path):
                os.remove(cnf_path)

    def restore_database_snapshot(self, snapshot_path: str) -> None:
        """Restaura un respaldo lógico generado previamente (.sql o .sql.gz)"""
        if not os.path.isfile(snapshot_path):
            raise FileNotFoundError(f"Snapshot no encontrado en: {snapshot_path}")

        if not self.mysql_bin:
            raise RuntimeError("No se encontró el binario cliente 'mariadb' ni 'mysql' para restaurar el snapshot.")

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as cnf:
            cnf_path = cnf.name
            cnf.write(f"[client]\nhost='{self.host}'\nport='{self.port}'\nuser='{self.user}'\npassword='{self.password}'\n")

        try:
            os.chmod(cnf_path, 0o600)
            is_gz = snapshot_path.endswith(".gz")
            if is_gz:
                with gzip.open(snapshot_path, "rt", encoding="utf-8", errors="replace") as f_in:
                    proc = subprocess.run(
                        [self.mysql_bin, f"--defaults-extra-file={cnf_path}", self.database],
                        stdin=f_in,
                        capture_output=True,
                        text=True
                    )
            else:
                with open(snapshot_path, "rt", encoding="utf-8", errors="replace") as f_in:
                    proc = subprocess.run(
                        [self.mysql_bin, f"--defaults-extra-file={cnf_path}", self.database],
                        stdin=f_in,
                        capture_output=True,
                        text=True
                    )

            if proc.returncode != 0:
                raise RuntimeError(f"Fallo restaurando snapshot: {proc.stderr.strip()}")
        finally:
            if os.path.exists(cnf_path):
                os.remove(cnf_path)

    def execute_migration_file(self, conn, filepath: str) -> None:
        """
        Ejecuta el script SQL de migración sentencia por sentencia.
        Maneja delimitadores y comentarios SQL de forma limpia.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Separar sentencias por ';' ignorando líneas de comentarios y vacías
        statements = []
        current_stmt = []
        for line in sql_content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("--") or stripped.startswith("/*"):
                continue
            current_stmt.append(line)
            if stripped.endswith(";"):
                statements.append("\n".join(current_stmt))
                current_stmt = []

        if current_stmt:
            stmt_rest = "\n".join(current_stmt).strip()
            if stmt_rest:
                statements.append(stmt_rest)

        with conn.cursor() as cur:
            for stmt in statements:
                stmt_clean = stmt.strip()
                if stmt_clean:
                    cur.execute(stmt_clean)

    def check_status(self) -> Dict[str, Any]:
        """Comprueba el estado actual de las migraciones sin modificar nada"""
        conn = self.get_connection()
        try:
            applied = self.get_applied_migrations(conn)
            available = self.get_available_migrations()
            existing_tables = self.get_existing_tables(conn)

            # Detectar si se requiere adoptar baseline
            baseline_adoption_needed = False
            if "001_baseline" not in applied and any(t in existing_tables for t in ["traffic_telemetry", "system_events", "red_light_violations"]):
                baseline_adoption_needed = True

            pending = []
            drift_warnings = []
            for m in available:
                v = m["version"]
                if v not in applied:
                    if v == "001_baseline" and baseline_adoption_needed:
                        pending.append({"version": v, "action": "adopt_baseline_existing_db", "filepath": m["filepath"]})
                    else:
                        pending.append({"version": v, "action": "execute_sql", "filepath": m["filepath"]})
                else:
                    if applied[v]["checksum"] != m["checksum"]:
                        drift_warnings.append(f"Discrepancia en migración '{v}': el hash aplicado difiere del archivo en disco.")

            return {
                "database": self.database,
                "applied_count": len(applied),
                "pending_count": len(pending),
                "applied": applied,
                "pending": pending,
                "warnings": drift_warnings,
                "up_to_date": len(pending) == 0
            }
        finally:
            conn.close()

    def run_migrations(self, make_backup: bool = True, dry_run: bool = False) -> Dict[str, Any]:
        """Aplica todas las migraciones pendientes en orden garantizado"""
        status_info = self.check_status()
        pending = status_info["pending"]

        if not pending:
            return {
                "status": "up_to_date",
                "message": "La base de datos se encuentra al día. No hay migraciones pendientes.",
                "applied_migrations": [],
                "backup_path": None,
                "warnings": status_info["warnings"]
            }

        if dry_run:
            return {
                "status": "dry_run",
                "pending_migrations": pending,
                "would_backup": make_backup,
                "warnings": status_info["warnings"]
            }

        backup_file = None
        if make_backup:
            backup_file = self.create_database_snapshot()

        conn = self.get_connection()
        applied_now = []
        try:
            for item in pending:
                version = item["version"]
                action = item["action"]
                filepath = item["filepath"]
                checksum = compute_file_checksum(filepath)

                if action == "adopt_baseline_existing_db":
                    # Adopción de baseline en base preexistente sin ejecutar DDL redundantes
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO schema_migrations (version, applied_at, checksum) VALUES (%s, NOW(), %s);",
                            (version, checksum)
                        )
                    applied_now.append({"version": version, "mode": "adopted_existing_baseline"})
                else:
                    # Ejecutar script DDL
                    self.execute_migration_file(conn, filepath)
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO schema_migrations (version, applied_at, checksum) VALUES (%s, NOW(), %s);",
                            (version, checksum)
                        )
                    applied_now.append({"version": version, "mode": "executed"})

            return {
                "status": "success",
                "applied_migrations": applied_now,
                "backup_path": backup_file,
                "warnings": status_info["warnings"]
            }
        except Exception as e:
            # En caso de fallo crítico en migraciones DDL
            error_msg = f"Fallo al aplicar migración: {e}"
            if backup_file and os.path.isfile(backup_file):
                error_msg += f"\nSe recomienda restaurar el snapshot automático generado en: {backup_file}"
                error_msg += f"\nComando: python3 scripts/migrate_db.py --rollback-snapshot '{backup_file}'"
            raise RuntimeError(error_msg)
        finally:
            conn.close()


def shutil_which(cmd: str) -> Optional[str]:
    """Busca binarios en PATH de forma segura"""
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for p in path_dirs:
        candidate = os.path.join(p, cmd)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def main():
    parser = argparse.ArgumentParser(
        description="FLUXA - Gestor Idempotente de Migraciones de Base de Datos MariaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true",
                        help="Comprueba si existen migraciones pendientes (sale con 0 si está al día, 1 si hay pendientes)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Muestra las migraciones pendientes sin aplicarlas")
    parser.add_argument("--status", action="store_true",
                        help="Muestra el historial y estado detallado de todas las migraciones")
    parser.add_argument("--no-backup", action="store_true",
                        help="Omite la generación del snapshot lógico previo con mariadb-dump")
    parser.add_argument("--backup-dir", default=None,
                        help="Directorio donde almacenar el snapshot previo (default: backups/db/)")
    parser.add_argument("--rollback-snapshot", default=None,
                        help="Restaura la base de datos completa desde un snapshot previo (.sql.gz / .sql)")
    parser.add_argument("--migrations-dir", default=None,
                        help="Directorio de scripts SQL de migración (default: migrations/)")
    parser.add_argument("--json", dest="json_output", action="store_true",
                        help="Imprime el resultado en formato estructurado JSON")

    args = parser.parse_args()

    migrator = DatabaseMigrator(
        migrations_dir=args.migrations_dir,
        backup_dir=args.backup_dir
    )

    if args.rollback_snapshot:
        try:
            migrator.restore_database_snapshot(args.rollback_snapshot)
            if args.json_output:
                print(json.dumps({"status": "restored", "snapshot": args.rollback_snapshot}))
            else:
                print(f"✅ Base de datos restaurada exitosamente desde: {args.rollback_snapshot}")
            sys.exit(0)
        except Exception as e:
            if args.json_output:
                print(json.dumps({"status": "error", "message": str(e)}))
            else:
                print(f"❌ Error restaurando snapshot: {e}", file=sys.stderr)
            sys.exit(2)

    if args.status:
        try:
            status = migrator.check_status()
            if args.json_output:
                print(json.dumps(status, indent=2, ensure_ascii=False))
            else:
                print(f"📊 Estado de Base de Datos MariaDB: '{status['database']}'")
                print(f"   Migraciones aplicadas: {status['applied_count']}")
                print(f"   Migraciones pendientes: {status['pending_count']}")
                if status["pending"]:
                    print("\nMigraciones pendientes:")
                    for p in status["pending"]:
                        print(f"   + {p['version']} ({p['action']})")
                if status["warnings"]:
                    print("\nAdvertencias:")
                    for w in status["warnings"]:
                        print(f"⚠️  {w}")
            sys.exit(0)
        except Exception as e:
            if args.json_output:
                print(json.dumps({"status": "error", "message": str(e)}))
            else:
                print(f"❌ Error verificando estado: {e}", file=sys.stderr)
            sys.exit(2)

    if args.check:
        try:
            status = migrator.check_status()
            if args.json_output:
                print(json.dumps({"up_to_date": status["up_to_date"], "pending_count": status["pending_count"]}))
            else:
                if status["up_to_date"]:
                    print("✅ La base de datos está al día. No se requieren migraciones.")
                else:
                    print(f"⚠️  Se detectaron {status['pending_count']} migración(es) pendiente(s).")
            sys.exit(0 if status["up_to_date"] else 1)
        except Exception as e:
            if args.json_output:
                print(json.dumps({"status": "error", "message": str(e)}))
            else:
                print(f"❌ Error en check de base de datos: {e}", file=sys.stderr)
            sys.exit(2)

    try:
        result = migrator.run_migrations(
            make_backup=not args.no_backup,
            dry_run=args.dry_run
        )
        if args.json_output:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if result["status"] == "up_to_date":
                print("✅ La base de datos ya se encuentra actualizada.")
            elif result["status"] == "dry_run":
                print("🔍 Simulación (Dry Run) de migraciones de MariaDB:")
                for p in result["pending_migrations"]:
                    print(f"   + {p['version']} ({p['action']})")
                print(f"   Snapshot previo habilitado: {result['would_backup']}")
            elif result["status"] == "success":
                print("✅ Migraciones de MariaDB aplicadas exitosamente.")
                if result.get("backup_path"):
                    print(f"   Snapshot de seguridad generado en: {result['backup_path']}")
                for a in result["applied_migrations"]:
                    print(f"   + {a['version']} [{a['mode']}]")
            if result.get("warnings"):
                print("\nAdvertencias:")
                for w in result["warnings"]:
                    print(f"⚠️  {w}")
        sys.exit(0)
    except Exception as e:
        if args.json_output:
            print(json.dumps({"status": "error", "message": str(e)}))
        else:
            print(f"❌ Error ejecutando migraciones: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
