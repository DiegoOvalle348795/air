# Air Risk Monitor

Dashboard de vuelos y clima con:

- Semáforo de riesgo por aeropuerto
- Mapa interactivo con Plotly
- Predicciones operativas por reglas
- Carpeta `funciones/` para organizar procesamiento, predicciones, visualizaciones y estilos

## Instalación

```sh
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run dashboard.py
```

Crea un archivo `.env` junto a `dashboard.py`:

```env
API_KEY=tu_key_openweather
AIRLABS_API_KEY=tu_key_airlabs
```
