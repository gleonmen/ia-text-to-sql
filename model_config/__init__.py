"""
Configuración del modelo de lenguaje y sus herramientas.

Aísla la elección del modelo, sus parámetros, y la lista de tools del
resto del grafo. Cambiar de OpenAI a Anthropic, ajustar la temperatura,
o agregar/quitar tools no debería requerir tocar ``agent_langgraph.py``.
"""

from langchain.chat_models import init_chat_model

from tools.run_sql_query import run_sql_query_langchain as run_sql_query


# Lista de herramientas disponibles para el agente.
# Se usa tanto en bind_tools (para que el LLM las "conozca") como en el
# ToolNode del grafo (para que el grafo las ejecute cuando el LLM las
# invoque).
tools = [run_sql_query]


# Modelo base. ``init_chat_model`` es el factory provider-agnostic
# recomendado por LangChain 1.0: cambiar de proveedor (Claude, Gemini,
# Bedrock, etc.) es solo cambiar el string del modelo.
#   - OpenAI:    "gpt-4.1", "gpt-4o", "gpt-4o-mini"
#   - Anthropic: "claude-sonnet-4-6", "claude-opus-4-6"
#   - Google:    "gemini-2.5-pro", "gemini-2.5-flash"
llm = init_chat_model(
    "gpt-4o-mini",
    temperature=0,
)


# Modelo con tools enlazadas, listo para invocar desde el nodo del grafo.
llm_with_tools = llm.bind_tools(tools)


__all__ = ["llm", "llm_with_tools", "tools"]
