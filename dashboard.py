"""
Dashboard Climático Interactivo
Fuente de datos: Open-Meteo API (https://open-meteo.com/) - gratuita, sin API key
Módulo: Sistemas de Big Data - UD5 Práctica 1
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Climático",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CIUDADES DISPONIBLES CON SUS COORDENADAS
# ─────────────────────────────────────────────
CIUDADES = {
    "Madrid":        {"lat": 40.4168, "lon": -3.7038},
    "Barcelona":     {"lat": 41.3851, "lon":  2.1734},
    "Sevilla":       {"lat": 37.3891, "lon": -5.9845},
    "Valencia":      {"lat": 39.4699, "lon": -0.3763},
    "Bilbao":        {"lat": 43.2627, "lon": -2.9253},
    "Palma de Mallorca": {"lat": 39.5696, "lon":  2.6502},
    "Zaragoza":      {"lat": 41.6561, "lon": -0.8773},
    "Málaga":        {"lat": 36.7213, "lon": -4.4214},
    "Córdoba":       {"lat": 37.8882, "lon": -4.7794},
    "Palma del Río": {"lat": 37.7000, "lon": -5.2833},
}

# ─────────────────────────────────────────────
# FUNCIÓN DE CARGA DE DATOS (encapsulada)
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)  # Cache de 5 minutos para no saturar la API
def cargar_datos_clima(ciudades_seleccionadas: list, dias: int = 7) -> dict:
    """
    Descarga datos climáticos históricos y actuales desde Open-Meteo API.
    Devuelve un diccionario con DataFrames por ciudad.
    """
    fecha_fin = datetime.today().strftime("%Y-%m-%d")
    fecha_inicio = (datetime.today() - timedelta(days=dias)).strftime("%Y-%m-%d")

    resultados = {}

    for ciudad in ciudades_seleccionadas:
        coords = CIUDADES[ciudad]
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={coords['lat']}&longitude={coords['lon']}"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
            "windspeed_10m_max,weathercode"
            "&timezone=Europe%2FMadrid"
            f"&start_date={fecha_inicio}&end_date={fecha_fin}"
        )
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json().get("daily", {})
            df = pd.DataFrame(data)
            df["ciudad"] = ciudad
            df["date"] = pd.to_datetime(df["time"])
            df.drop(columns=["time"], inplace=True)
            resultados[ciudad] = df
        except Exception as e:
            st.warning(f"No se pudo obtener datos de {ciudad}: {e}")

    return resultados


def combinar_datos(resultados: dict) -> pd.DataFrame:
    """Une los DataFrames de todas las ciudades en uno solo."""
    if not resultados:
        return pd.DataFrame()
    return pd.concat(resultados.values(), ignore_index=True)


# ─────────────────────────────────────────────
# SIDEBAR – CONTROLES DE INTERACTIVIDAD
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuración")
    st.markdown("---")

    # Multiselect: permite elegir varias ciudades simultáneamente
    ciudades_sel = st.multiselect(
        "🏙️ Ciudades",
        options=list(CIUDADES.keys()),
        default=["Madrid", "Sevilla", "Barcelona"]
    )

    # Slider: rango de días a visualizar
    dias_sel = st.slider(
        "📅 Días hacia atrás",
        min_value=3,
        max_value=14,
        value=7,
        step=1,
        help="Número de días de historial a mostrar"
    )

    # Radio buttons: métrica principal de temperatura
    metrica_temp = st.radio(
        "🌡️ Temperatura a mostrar",
        options=["Máxima", "Mínima", "Ambas"],
        index=2
    )

    # Selector de fechas para filtrar el rango
    fecha_desde = st.date_input(
        "📆 Mostrar desde",
        value=datetime.today() - timedelta(days=dias_sel),
        max_value=datetime.today()
    )

    st.markdown("---")
    # Automatización: intervalo de refresco
    auto_refresh = st.toggle("🔄 Auto-refresco (5 min)", value=False)
    st.caption("Actualiza los datos automáticamente cada 5 minutos.")

    st.markdown("---")
    st.caption("Datos: [Open-Meteo API](https://open-meteo.com/)")
    st.caption("© 2025/26 · Práctica UD5")


# ─────────────────────────────────────────────
# CARGA Y PREPARACIÓN DE DATOS
# ─────────────────────────────────────────────
if not ciudades_sel:
    st.warning("⚠️ Selecciona al menos una ciudad en el panel lateral.")
    st.stop()

datos_raw = cargar_datos_clima(ciudades_sel, dias_sel)
df = combinar_datos(datos_raw)

if df.empty:
    st.error("No se pudieron obtener datos. Comprueba tu conexión a internet.")
    st.stop()

# Filtrar por fecha de inicio seleccionada
df = df[df["date"] >= pd.to_datetime(fecha_desde)]

# ─────────────────────────────────────────────
# ENCABEZADO PRINCIPAL
# ─────────────────────────────────────────────
st.title("🌤️ Dashboard Climático – España")
st.markdown(
    f"Mostrando datos de **{', '.join(ciudades_sel)}** "
    f"desde **{fecha_desde.strftime('%d/%m/%Y')}**. "
    f"Última actualización: **{datetime.now().strftime('%H:%M:%S')}**"
)
st.markdown("---")

# ─────────────────────────────────────────────
# KPIs – Mínimo 2 indicadores calculados
# ─────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

# KPI 1: Temperatura máxima registrada en el periodo
temp_max_global = df["temperature_2m_max"].max()
ciudad_max = df.loc[df["temperature_2m_max"].idxmax(), "ciudad"]
col1.metric(
    label="🌡️ Temp. máxima del periodo",
    value=f"{temp_max_global:.1f} °C",
    delta=ciudad_max,
    delta_color="off"
)

# KPI 2: Temperatura mínima registrada
temp_min_global = df["temperature_2m_min"].min()
ciudad_min = df.loc[df["temperature_2m_min"].idxmin(), "ciudad"]
col2.metric(
    label="❄️ Temp. mínima del periodo",
    value=f"{temp_min_global:.1f} °C",
    delta=ciudad_min,
    delta_color="off"
)

# KPI 3: Precipitación total acumulada (todas las ciudades)
precip_total = df["precipitation_sum"].sum()
col3.metric(
    label="🌧️ Precipitación total acumulada",
    value=f"{precip_total:.1f} mm"
)

# KPI 4: Viento máximo registrado
viento_max = df["windspeed_10m_max"].max()
ciudad_viento = df.loc[df["windspeed_10m_max"].idxmax(), "ciudad"]
col4.metric(
    label="💨 Viento máximo",
    value=f"{viento_max:.1f} km/h",
    delta=ciudad_viento,
    delta_color="off"
)

st.markdown("---")

# ─────────────────────────────────────────────
# GRÁFICOS – Mínimo 2 tipos distintos
# ─────────────────────────────────────────────

# Usamos tabs como elemento de interactividad adicional
tab1, tab2, tab3 = st.tabs(["📈 Temperatura", "🌧️ Precipitación & Viento", "📊 Comparativa"])

# ── TAB 1: Gráfico de líneas de temperatura ──
with tab1:
    st.subheader("Evolución de la Temperatura")

    if metrica_temp == "Máxima":
        cols_temp = ["temperature_2m_max"]
        etiquetas = {"temperature_2m_max": "Temp. Máxima (°C)"}
    elif metrica_temp == "Mínima":
        cols_temp = ["temperature_2m_min"]
        etiquetas = {"temperature_2m_min": "Temp. Mínima (°C)"}
    else:
        cols_temp = ["temperature_2m_max", "temperature_2m_min"]
        etiquetas = {
            "temperature_2m_max": "Temp. Máxima (°C)",
            "temperature_2m_min": "Temp. Mínima (°C)"
        }

    df_melt = df.melt(
        id_vars=["date", "ciudad"],
        value_vars=cols_temp,
        var_name="tipo",
        value_name="temperatura"
    )
    df_melt["tipo"] = df_melt["tipo"].map(etiquetas)
    df_melt["ciudad_tipo"] = df_melt["ciudad"] + " – " + df_melt["tipo"]

    fig_lineas = px.line(
        df_melt,
        x="date",
        y="temperatura",
        color="ciudad_tipo",
        title="Temperatura diaria por ciudad",
        labels={"date": "Fecha", "temperatura": "Temperatura (°C)", "ciudad_tipo": "Ciudad / Métrica"},
        markers=True
    )
    fig_lineas.update_layout(
        legend_title_text="Ciudad / Métrica",
        hovermode="x unified",
        xaxis_title="Fecha",
        yaxis_title="Temperatura (°C)"
    )
    st.plotly_chart(fig_lineas, use_container_width=True)

# ── TAB 2: Gráfico de barras apiladas (precipitación) + scatter (viento) ──
with tab2:
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Precipitación diaria acumulada")
        fig_barras = px.bar(
            df,
            x="date",
            y="precipitation_sum",
            color="ciudad",
            title="Precipitación por día y ciudad",
            labels={
                "date": "Fecha",
                "precipitation_sum": "Precipitación (mm)",
                "ciudad": "Ciudad"
            },
            barmode="group"
        )
        fig_barras.update_layout(
            xaxis_title="Fecha",
            yaxis_title="Precipitación (mm)",
            legend_title_text="Ciudad"
        )
        st.plotly_chart(fig_barras, use_container_width=True)

    with col_b:
        st.subheader("Velocidad máxima del viento")
        fig_viento = px.scatter(
            df,
            x="date",
            y="windspeed_10m_max",
            color="ciudad",
            size="windspeed_10m_max",
            title="Viento máximo diario por ciudad",
            labels={
                "date": "Fecha",
                "windspeed_10m_max": "Viento máx. (km/h)",
                "ciudad": "Ciudad"
            }
        )
        fig_viento.update_layout(
            xaxis_title="Fecha",
            yaxis_title="Viento máx. (km/h)",
            legend_title_text="Ciudad"
        )
        st.plotly_chart(fig_viento, use_container_width=True)

# ── TAB 3: Gráfico de tarta + tabla resumen ──
with tab3:
    col_c, col_d = st.columns([1, 1])

    with col_c:
        st.subheader("Distribución de precipitación por ciudad")
        precip_por_ciudad = df.groupby("ciudad")["precipitation_sum"].sum().reset_index()
        precip_por_ciudad.columns = ["Ciudad", "Precipitación total (mm)"]

        fig_tarta = px.pie(
            precip_por_ciudad,
            names="Ciudad",
            values="Precipitación total (mm)",
            title="Precipitación acumulada por ciudad",
            hole=0.35
        )
        fig_tarta.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_tarta, use_container_width=True)

    with col_d:
        st.subheader("Resumen estadístico por ciudad")
        resumen = df.groupby("ciudad").agg(
            Temp_max_media=("temperature_2m_max", "mean"),
            Temp_min_media=("temperature_2m_min", "mean"),
            Precipitacion_total=("precipitation_sum", "sum"),
            Viento_max=("windspeed_10m_max", "max")
        ).round(1).reset_index()
        resumen.columns = [
            "Ciudad", "T.máx media (°C)", "T.mín media (°C)",
            "Precip. total (mm)", "Viento máx (km/h)"
        ]
        st.dataframe(resumen, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# AUTOMATIZACIÓN: refresco automático
# ─────────────────────────────────────────────
if auto_refresh:
    # Espera 5 minutos y relanza el script completo
    time.sleep(300)
    st.cache_data.clear()
    st.rerun()

