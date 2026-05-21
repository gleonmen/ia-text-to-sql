# agent_langgraph.py

from typing import TypedDict, Annotated, Sequence

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv()  # carga variables de entorno desde .env

# ============================================
# 1. CONFIGURACIÓN DEL MODELO Y TOOLS
# ============================================

from model_config import llm_with_tools, tools

# ============================================
# 2. INSTRUCCIONES DEL AGENTE (system prompt)
# ============================================

from system_prompt import SYSTEM_INSTRUCTION

# ============================================
# 3. DEFINICIÓN DEL ESTADO DEL GRAFO
# ============================================

class AgentState(TypedDict):
    """Estado que se pasa entre los nodos del grafo"""
    messages: Annotated[Sequence[BaseMessage], add_messages]

# ============================================
# 4. FUNCIONES DE LOS NODOS DEL GRAFO
# ============================================

def should_continue(state: AgentState):
    """Decide si continuar ejecutando tools o terminar"""
    messages = state["messages"]
    last_message = messages[-1]

    # Si el último mensaje tiene tool_calls, continuamos a ejecutar tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    # Si no, terminamos
    return "end"


def call_model(state: AgentState):
    """Nodo que llama al modelo de lenguaje.

    El SystemMessage se inyecta solo si aún no está en el estado. No se
    persiste a state (no se retorna en el dict), así no se duplica turno
    tras turno cuando el checkpointer acumula histórico.
    """
    messages = list(state["messages"])
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_INSTRUCTION)] + messages

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# ============================================
# 5. CONSTRUCCIÓN DEL GRAFO DE LANGGRAPH
# ============================================

# Crear el grafo con el estado definido
workflow = StateGraph(AgentState)

# Crear el nodo de tools
tool_node = ToolNode(tools)

# Agregar nodos al grafo
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Definir el punto de entrada
workflow.set_entry_point("agent")

# Agregar edges condicionales
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "end": END,
    },
)

# Después de ejecutar tools, volver al agente
workflow.add_edge("tools", "agent")

# Compilar el grafo SIN checkpointer — EXPORTADO PARA LANGGRAPH STUDIO
# (Studio gestiona su propia persistencia; no le inyectamos PostgresSaver).
# Para uso con persistencia en Streamlit, ver ``agent_runner.build_app``.
app = workflow.compile()
