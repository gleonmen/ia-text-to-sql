"""
Módulo de persistencia del histórico de conversación.

Aísla toda la lógica de checkpointing (PostgresSaver de LangGraph 1.0
sobre PostgreSQL / Supabase) del resto del proyecto. El agente y la UI
solo importan las funciones públicas expuestas aquí.
"""

from conversation_or_chat_history.checkpointer import (
    build_database_url,
    ensure_checkpointer_tables,
    get_checkpointer,
    get_schema_name,
)

__all__ = [
    "build_database_url",
    "ensure_checkpointer_tables",
    "get_checkpointer",
    "get_schema_name",
]
