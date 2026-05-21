#!/usr/bin/env python3
# main.py - Interfaz web con Streamlit para el agente LangGraph

import os
import uuid

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

from agent_runner import build_app, run_agent
from conversation_or_chat_history import (
    ensure_checkpointer_tables,
    get_checkpointer,
    get_schema_name,
)

load_dotenv()

# ============================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================

st.set_page_config(
    page_title="Agente SQL CitiBike - Kevin Inofuente Colque",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# ESTILOS PERSONALIZADOS
# ============================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stChatMessage {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        background-color: #d1ecf1;
        border-left: 5px solid #17a2b8;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# CHECKPOINTER + GRAFO (vivos por sesión del servidor)
# ============================================

@st.cache_resource(show_spinner="🔌 Conectando al histórico (Supabase)…")
def _get_checkpointer():
    """Abre el PostgresSaver una sola vez por proceso de Streamlit.

    Internamente mantiene la conexión psycopg viva como variable de
    módulo (ver ``conversation_or_chat_history.checkpointer``). El
    ``st.cache_resource`` solo evita reejecutar ``setup()`` en cada
    rerun de Streamlit.
    """
    ensure_checkpointer_tables()  # crea schema + tablas si faltan
    return get_checkpointer()


@st.cache_resource(show_spinner="⚙️ Compilando agente…")
def _get_compiled_app():
    """Compila el grafo con el checkpointer (una vez por proceso)."""
    return build_app(_get_checkpointer())


app = _get_compiled_app()


# ============================================
# SESSION STATE (thread_id + historial visual)
# ============================================

WELCOME_MESSAGE = """¡Hola! 👋 Soy tu asistente para analizar datos de CitiBike NYC.

Puedo responder preguntas sobre:
- 📊 Estadísticas de viajes
- 🗺️ Rutas y estaciones populares
- ⏱️ Duraciones y patrones temporales
- 👥 Tipos de usuarios

**¿Qué te gustaría saber?**"""


if "thread_id" not in st.session_state:
    # Una conversación nueva por cada sesión de navegador.
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME_MESSAGE}]

if "ejemplo_seleccionado" not in st.session_state:
    st.session_state.ejemplo_seleccionado = None


def _load_thread_into_view(thread_id: str) -> bool:
    """Lee el histórico de un thread desde Postgres y lo pinta en el chat.

    Devuelve True si encontró mensajes, False si el thread está vacío o
    no existe en el checkpointer.
    """
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = app.get_state(config)
    persisted = snapshot.values.get("messages", []) if snapshot.values else []
    if not persisted:
        return False

    view = []
    for m in persisted:
        if isinstance(m, HumanMessage):
            view.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage) and m.content:
            view.append({"role": "assistant", "content": m.content})

    st.session_state.messages = view or [{"role": "assistant", "content": WELCOME_MESSAGE}]
    return True


def _start_new_thread() -> None:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = [{"role": "assistant", "content": WELCOME_MESSAGE}]


# ============================================
# SIDEBAR - INFORMACIÓN Y EJEMPLOS
# ============================================

with st.sidebar:
    # Mostrar logo si existe
    if os.path.exists("images/datapath-logo.png"):
        st.image("images/datapath-logo.png", width=200)

    st.markdown("## 🚴 Agente SQL CitiBike")
    st.markdown("---")

    st.markdown("### 📊 Sobre este proyecto")
    st.info("""
    Este agente inteligente utiliza **LangGraph** y **OpenAI** para responder
    preguntas en lenguaje natural sobre los datos de CitiBike NYC almacenados en BigQuery.
    """)

    st.markdown("### 💡 Ejemplos de preguntas:")
    ejemplos = [
        "¿Cuántos viajes en total hay?",
        "¿Cuál es la ruta más popular?",
        "¿Cuál es la duración promedio?",
        "¿Cuántos usuarios son subscribers?",
        "Dame las 5 estaciones más usadas",
        "¿En qué año hay más viajes?"
    ]

    for ejemplo in ejemplos:
        if st.button(f"📝 {ejemplo}", key=ejemplo, use_container_width=True):
            st.session_state.ejemplo_seleccionado = ejemplo

    st.markdown("---")

    # =====================
    # Sesión / thread_id
    # =====================
    st.markdown("### 💬 Conversación actual")
    st.code(st.session_state.thread_id, language=None)
    st.caption("Copia este ID si quieres retomar esta charla más tarde.")

    with st.expander("🔁 Continuar conversación existente"):
        thread_input = st.text_input(
            "UUID de la conversación",
            placeholder="ej: 550e8400-e29b-41d4-a716-446655440000",
            label_visibility="collapsed",
            key="resume_thread_input",
        )
        if st.button("Cargar conversación", use_container_width=True):
            try:
                uuid.UUID(thread_input)
            except (ValueError, TypeError):
                st.error("UUID inválido.")
            else:
                st.session_state.thread_id = thread_input
                if _load_thread_into_view(thread_input):
                    st.success("Conversación cargada.")
                    st.rerun()
                else:
                    st.warning("Ese thread no tiene mensajes guardados todavía.")

    if st.button("🆕 Nueva conversación", use_container_width=True):
        _start_new_thread()
        st.rerun()

    st.markdown("---")
    st.markdown("### 🛠️ Tecnologías")
    st.markdown("""
    - **LangGraph 1.0** - Orquestación de agentes
    - **OpenAI GPT-4o** - Modelo de lenguaje
    - **BigQuery** - Base de datos
    - **Supabase (Postgres)** - Persistencia del histórico
    - **Streamlit** - Interface web
    """)

    st.markdown("---")
    st.markdown("### ℹ️ Estado del sistema")

    # Verificar configuración
    openai_ok = bool(os.getenv("OPENAI_API_KEY"))
    bigquery_ok = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    history_ok = bool(os.getenv("DB_USER") and os.getenv("DB_PASSWORD") and os.getenv("DB_HOST"))

    st.markdown(f"**OpenAI:** {'✅' if openai_ok else '❌'}")
    st.markdown(f"**BigQuery:** {'✅' if bigquery_ok else '❌'}")
    st.markdown(f"**Histórico (schema `{get_schema_name()}`):** {'✅' if history_ok else '❌'}")

    if not (openai_ok and bigquery_ok and history_ok):
        st.error("⚠️ Faltan configuraciones. Revisa el archivo .env")

# ============================================
# HEADER PRINCIPAL
# ============================================

st.markdown('<p class="main-header">🚴 Agente Analista de CitiBike NYC</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Pregúntame cualquier cosa sobre los datos de viajes de CitiBike</p>', unsafe_allow_html=True)

# ============================================
# MOSTRAR HISTORIAL DE CHAT
# ============================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ============================================
# INPUT DEL USUARIO
# ============================================

# El chat_input SIEMPRE se renderiza (Streamlit lo posiciona al final
# de la página). Si no lo llamáramos en cada run, Streamlit no lo pinta.
typed_prompt = st.chat_input("Escribe tu pregunta aquí...")

# El ejemplo del sidebar tiene prioridad cuando está seteado.
if st.session_state.ejemplo_seleccionado:
    prompt = st.session_state.ejemplo_seleccionado
    st.session_state.ejemplo_seleccionado = None
else:
    prompt = typed_prompt

# ============================================
# PROCESAR PREGUNTA
# ============================================

if prompt:
    # Agregar mensaje del usuario al historial visual
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)

    # Mostrar indicador de que está pensando
    with st.chat_message("assistant"):
        with st.spinner("🤔 Analizando tu pregunta y consultando BigQuery..."):
            try:
                # Invocar el agente con el thread_id de esta sesión.
                # El checkpointer carga turnos previos automáticamente.
                respuesta = run_agent(app, prompt, st.session_state.thread_id)

                st.markdown(respuesta)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": respuesta,
                })

            except Exception as e:
                error_msg = f"❌ **Error:** {str(e)}\n\nPor favor, intenta reformular tu pregunta o contacta al administrador."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                })

# ============================================
# FOOTER
# ============================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <p>Desarrollado con ❤️ usando LangGraph 1.0 + OpenAI GPT-4o + BigQuery + Supabase</p>
    <p>👨‍💻 Desarrollado por <strong>Ing. Kevin Inofuente Colque</strong> — AI Engineer</p>
    <p>
        <a href="https://github.com/KevinInoCol" target="_blank" style="text-decoration: none; color: #333;">🐙 GitHub</a>
        &nbsp;|&nbsp;
        <a href="https://www.linkedin.com/in/kevin-inofuente-colque" target="_blank" style="text-decoration: none; color: #0077b5;">💼 LinkedIn</a>
    </p>
    <p>📚 Proyecto educativo para enseñanza de agentes con LangGraph</p>
</div>
""", unsafe_allow_html=True)
