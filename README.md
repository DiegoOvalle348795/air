# Air Risk Monitor

Dashboard de tráfico aéreo y condiciones ambientales con:

- AirLabs: vuelos, horarios, retrasos, estados y aeronaves.
- OpenWeather: clima por ciudad/aeropuerto.
- OpenAQ: calidad del aire por estación cercana al aeropuerto.
- ThingSpeak: sensores ambientales propios o canales públicos.
- Asyncio: lectura concurrente de APIs.
- MPI4Py: distribución del procesamiento por subconjuntos de ciudades.
- Numba: aceleración de cálculos estadísticos en CPU.
- CuPy/CUDA: aceleración opcional en GPU NVIDIA, con fallback a NumPy si no hay GPU.
- Pandas: limpieza y cruce tabular.
- Streamlit + Plotly: visualización interactiva.

## Instalación básica

```sh
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run dashboard.py
```

## Archivo `.env`

Crea un archivo `.env` junto a `dashboard.py`:

```env
API_KEY=tu_key_openweather
AIRLABS_API_KEY=tu_key_airlabs
OPENAQ_API_KEY=tu_key_openaq

# Opcionales para ThingSpeak
THINGSPEAK_CHANNEL_ID=9
THINGSPEAK_READ_API_KEY=
THINGSPEAK_RESULTS=25

# Opcional para OpenAQ
OPENAQ_RADIUS_M=25000
```

- `OPENAQ_API_KEY` es necesaria para consultar OpenAQ v3.
- Si no tienes canal propio de ThingSpeak, el proyecto usa el canal público `9` como ejemplo.
- Si tu canal de ThingSpeak es privado, agrega `THINGSPEAK_READ_API_KEY`.

## Instalar CuPy/CUDA opcional

Solo si tu computadora tiene GPU NVIDIA compatible:

```sh
pip install -r requirements-gpu.txt
```

Para revisar si CuPy detecta CUDA:

```sh
python -c "import cupy; cupy.show_config()"
```

Si no tienes GPU, el dashboard sigue funcionando con NumPy.

## Ejecutar MPI4Py

```sh
mpiexec -n 4 python main.py
```

## Cómo funcionan las predicciones

No usa IA. El sistema calcula un índice de riesgo de 0 a 100 por reglas:

```text
riesgo = clima + visibilidad + viento + tráfico + retrasos + calidad del aire
```

Después clasifica:

```text
0 - 39   = Normal
40 - 69  = Precaución
70 - 100 = Crítico
```
