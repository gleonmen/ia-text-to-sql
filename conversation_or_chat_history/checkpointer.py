"""
Configuracion del checkpointer de LangGraph sobre PostgreSQL/Supabase.

Las tablas que crea ``PostgresSaver.setup()`` viven en el schema indicado
por ``DB_SCHEMA`` para mantener el historico aislado del resto del proyecto.
"""

import os
from urllib.parse import quote_plus, urlencode

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import sql
from psycopg.rows import dict_row


def build_database_url() -> str:
    """
    Construye el connection string de Postgres a partir de DB_USER,
    DB_PASSWORD, DB_HOST, DB_PORT y DB_NAME.

    El search_path se configura despues de abrir la conexion. Asi evitamos
    pasar ``options`` como parametro de arranque al pooler de Supabase.
    """
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "postgres")

    missing = [
        key
        for key, value in {
            "DB_USER": user,
            "DB_PASSWORD": password,
            "DB_HOST": host,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(
            "Faltan variables de entorno requeridas para el historico: "
            + ", ".join(missing)
        )

    params = {
        "sslmode": "require",
        "gssencmode": "disable",
        "connect_timeout": os.getenv("DB_CONNECT_TIMEOUT", "10"),
    }
    query = urlencode(params)
    return (
        f"postgresql://{user}:{quote_plus(password)}"
        f"@{host}:{port}/{name}?{query}"
    )


def get_schema_name() -> str:
    """Schema de Postgres donde viven las tablas del checkpointer."""
    return os.getenv("DB_SCHEMA", "public")


def _set_search_path(conn: psycopg.Connection) -> None:
    """Apunta la conexion al schema del checkpointer."""
    schema = get_schema_name()
    if schema and schema != "public":
        conn.execute(
            sql.SQL("SET search_path TO {}, public").format(
                sql.Identifier(schema)
            )
        )


# Estado interno: conexion y checkpointer vivos por todo el proceso.
_checkpointer: PostgresSaver | None = None
_TABLES_READY = False


def get_checkpointer() -> PostgresSaver:
    """Devuelve un ``PostgresSaver`` con conexion psycopg persistente.

    No se usa ``PostgresSaver.from_conn_string(...)`` porque al cachearlo
    en Streamlit la referencia al context manager puede cerrarse por GC.
    Abrimos la conexion directamente y la mantenemos viva como variable de
    modulo durante la vida del proceso.

    Flags importantes:
    - ``autocommit=True``: cada operacion del saver queda en su propia
      transaccion.
    - ``prepare_threshold=0`` y ``row_factory=dict_row``: mismos flags que
      usa ``PostgresSaver.from_conn_string(...)``.
    """
    global _checkpointer
    if _checkpointer is None:
        conn = psycopg.connect(
            build_database_url(),
            autocommit=True,
            prepare_threshold=0,
            row_factory=dict_row,
        )
        _set_search_path(conn)
        _checkpointer = PostgresSaver(conn)
    return _checkpointer


def ensure_checkpointer_tables() -> None:
    """
    Garantiza que el schema exista y que las tablas del checkpointer esten
    creadas. Es idempotente por proceso.
    """
    global _TABLES_READY
    if _TABLES_READY:
        return

    schema = get_schema_name()

    if schema != "public":
        with psycopg.connect(
            build_database_url(),
            autocommit=True,
            prepare_threshold=0,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                        sql.Identifier(schema)
                    )
                )

    get_checkpointer().setup()
    _TABLES_READY = True
