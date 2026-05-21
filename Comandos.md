# Este comando solo se instala si tienes python 3.11
pip install -U "langgraph-cli[inmem]"

# Corre el siguiente comando para lanzar LangGraph Studio
langgraph dev --allow-blocking

# Crear su Virtual Environment:
LangGraph-Agente-Texto-SQL

# Activa tu Virtual Environment:
conda activate LangGraph-Agente-Texto-SQL

# Comandos para desplegar en DigitalOcean
- docker login

- docker buildx build --platform linux/amd64 -t kevininofuentecolque/app-langgraph-agent-big-query-v1:latest --push .

# Preguntas que le puedes hacer al agente:
- hola
- ¿Cuáles son las 10 rutas de bicicleta más populares, agrupando por estación de inicio y fin? Devuelve el nombre de la estación de inicio, el nombre de la estación de fin, un conteo de cuántos viajes se hicieron en esa ruta y la duración típica de esos viajes
- cuantos datos tienes, es decir cuantas filas.
- Cuantas de estos viajes inician y terminan en el mismo lugar

# Notas

## Como ejecutar la GUI

En Windows/PowerShell, si `streamlit run main.py` muestra
`The term 'streamlit' is not recognized`, ejecuta Streamlit desde el Python
del entorno virtual del proyecto:

```powershell
.\.venv\Scripts\python.exe -m streamlit run main.py
```

Alternativamente, primero activa el entorno virtual y luego usa el comando
normal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run main.py
```
