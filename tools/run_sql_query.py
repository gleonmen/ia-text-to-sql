# tools/run_sql_query.py

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from google.cloud import bigquery
from google.cloud.bigquery import dbapi
import pandas as pd
from langchain_core.tools import tool

# --- Configuración de conexión a BigQuery ---
# URI de conexión que indica a SQLAlchemy usar BigQuery y la tabla pública de CitiBike
# bigquery://<dataset>/<table>
db_uri = "bigquery://bigquery-public-data/new_york_citibike"

# Variable global para el engine (lazy loading)
_engine = None

def get_bigquery_connection():
    """
    Inicializa el cliente de BigQuery con el proyecto de facturación/quotas
    definido en la variable de entorno ``GOOGLE_CLOUD_PROJECT``.

    Soporta autenticación via:
    1. Variable de entorno GOOGLE_APPLICATION_CREDENTIALS (Service Account JSON)
    2. gcloud auth application-default login (credenciales de usuario)
    """
    gcp_project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not gcp_project_id:
        raise ValueError(
            "Falta la variable de entorno GOOGLE_CLOUD_PROJECT. "
            "Definela en el .env con el ID del proyecto de GCP que paga las queries."
        )

    # Si hay un archivo de credenciales especificado
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if credentials_path:
        # Si es ruta relativa, convertirla a absoluta basada en la raíz del proyecto
        if not os.path.isabs(credentials_path):
            project_root = Path(__file__).parent.parent
            credentials_path = str((project_root / credentials_path).resolve())
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"Archivo de credenciales no encontrado: {credentials_path}\n"
                f"Verifica que GOOGLE_APPLICATION_CREDENTIALS apunte a un archivo válido."
            )

    # Crear cliente de BigQuery (usará las credenciales configuradas)
    client = bigquery.Client(project=gcp_project_id)

    # Creamos y devolvemos la conexión DB-API compatible con SQLAlchemy
    connection = dbapi.connect(client=client)
    return connection

def get_engine():
    """
    Obtiene el engine de SQLAlchemy, creándolo solo si es necesario (lazy loading).
    Esto evita errores de credenciales durante la importación del módulo.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(db_uri, creator=get_bigquery_connection)
    return _engine
# -----------------------------------------------------------


# Tool para LangChain - Ejecuta consultas SQL en BigQuery
@tool
def run_sql_query_langchain(query: str) -> str:
    """
    Ejecuta una consulta SQL en una base de datos de BigQuery que contiene datos de viajes de CitiBike en Nueva York
    y devuelve el resultado como una tabla formateada. La consulta debe ser compatible
    con el dialecto SQL de Google BigQuery.

    Args:
        query: La consulta SQL completa a ejecutar en BigQuery.

    Returns:
        El resultado de la consulta como una tabla de texto (Markdown) o un mensaje de error.
    """
    try:
        # Obtener el engine (lazy loading)
        engine = get_engine()
        with engine.connect() as connection:
            # Usamos text() para asegurar que SQLAlchemy trate el string como SQL literal
            result_proxy = connection.execute(text(query))
            
            # Convertimos el resultado a un DataFrame de Pandas para un formato bonito
            df = pd.DataFrame(result_proxy.fetchall(), columns=result_proxy.keys())
            
            # Si el DataFrame está vacío, devuelve un mensaje
            if df.empty:
                return "La consulta se ejecutó correctamente, pero no devolvió resultados."
            
            # Convertimos el DataFrame a un string (Markdown) para que el LLM lo pueda leer
            return df.to_markdown(index=False)

    except Exception as e:
        # Si hay un error de SQL, devuélvelo para que el agente pueda intentar corregirlo.
        return f"Error al ejecutar la consulta: {e}"