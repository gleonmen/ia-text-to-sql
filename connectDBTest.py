"""
Prueba aislada de conexion a Supabase usando Session Pooler.

Ejecutar en PowerShell:
    .venv/Scripts/python.exe connectDBTest.py

Variables requeridas en .env:
    DB_USER=postgres.<project-ref>
    DB_PASSWORD=<database-password>
    DB_HOST=<session-pooler-host>.pooler.supabase.com
    DB_PORT=5432
    DB_NAME=postgres
"""

import os
from urllib.parse import quote_plus, urlencode

import psycopg
from dotenv import load_dotenv


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Falta la variable de entorno requerida: {name}")
    return value


def build_session_pooler_dsn() -> str:
    user = require_env("DB_USER")
    password = require_env("DB_PASSWORD")
    host = require_env("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "postgres")

    params = {
        "sslmode": "require",
        "gssencmode": "disable",
        "connect_timeout": os.getenv("DB_CONNECT_TIMEOUT", "10"),
    }
    query = urlencode(params)
    return (
        f"postgresql://{user}:{quote_plus(password)}"
        f"@{host}:{port}/{database}?{query}"
    )


def print_config_summary() -> None:
    user = os.getenv("DB_USER", "")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "postgres")

    print("Configuracion detectada:")
    print(f"  DB_HOST: {host}")
    print(f"  DB_PORT: {port}")
    print(f"  DB_NAME: {database}")
    print(
        "  DB_USER: "
        + ("postgres.<project-ref>" if user.startswith("postgres.") else user or "<missing>")
    )
    print(f"  DB_PASSWORD: {'set' if password else 'missing'}")
    print()

    if not host.endswith(".pooler.supabase.com"):
        print("ADVERTENCIA: DB_HOST no parece ser un host de Session Pooler.")
    if port != "5432":
        print("ADVERTENCIA: Session Pooler normalmente usa DB_PORT=5432.")
    if not user.startswith("postgres."):
        print("ADVERTENCIA: Session Pooler normalmente usa DB_USER=postgres.<project-ref>.")
    print()


def scrub_error(error: Exception) -> str:
    message = str(error)
    for value in (os.getenv("DB_PASSWORD"), os.getenv("DB_USER")):
        if value:
            message = message.replace(value, "<redacted>")
    return message


def main() -> int:
    load_dotenv(".env")
    print_config_summary()

    try:
        dsn = build_session_pooler_dsn()
        print("Probando conexion...")
        with psycopg.connect(dsn, autocommit=True, prepare_threshold=0) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        current_database() as database,
                        current_user as db_user,
                        inet_server_addr()::text as server_addr,
                        inet_server_port() as server_port
                    """
                )
                row = cur.fetchone()

        print("Conexion OK.")
        print(f"  database: {row[0]}")
        print("  db_user: <redacted>")
        print(f"  server_addr: {row[2]}")
        print(f"  server_port: {row[3]}")
        return 0
    except Exception as error:
        print("Conexion FALLIDA.")
        print(f"  tipo: {type(error).__name__}")
        print(f"  detalle: {scrub_error(error)}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
