"""
Instrucciones del agente (system prompt).

Aísla el prompt del resto del código para que pueda evolucionar de forma
independiente al grafo. Si en el futuro se quiere versionar, A/B-testear
o cargar desde un archivo externo, este es el único lugar a tocar.
"""

from system_prompt.prompt import TABLE_SCHEMA, SYSTEM_INSTRUCTION

__all__ = ["TABLE_SCHEMA", "SYSTEM_INSTRUCTION"]
