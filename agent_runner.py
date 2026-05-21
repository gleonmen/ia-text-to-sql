"""
Runtime helpers para invocar el grafo del agente.

Separados del archivo del grafo para que ``agent_langgraph.py`` describa
únicamente la definición (state + nodos + edges) y este módulo describa
cómo se ejecuta en producción con persistencia (checkpointer + thread_id).
"""

from langchain_core.messages import HumanMessage

from agent_langgraph import workflow


def build_app(checkpointer):
    """Compila el grafo con un checkpointer (PostgresSaver) para producción.

    Llamado desde ``main.py`` con el checkpointer abierto durante la vida
    de la sesión de Streamlit (vía ``st.cache_resource``).
    """
    return workflow.compile(checkpointer=checkpointer)


def run_agent(compiled_app, query: str, thread_id: str) -> str:
    """Ejecuta el agente con histórico persistido por ``thread_id``.

    Solo se manda el nuevo ``HumanMessage``: el checkpointer carga los
    turnos previos del thread automáticamente y los fusiona vía el
    reducer ``add_messages`` del estado.

    Args:
        compiled_app: grafo compilado con checkpointer (ver ``build_app``).
        query: pregunta del usuario en lenguaje natural.
        thread_id: identificador estable de la conversación.

    Returns:
        Contenido textual del último mensaje del agente.
    """
    config = {"configurable": {"thread_id": thread_id}}
    result = compiled_app.invoke(
        {"messages": [HumanMessage(content=query)]},
        config=config,
    )
    return result["messages"][-1].content
