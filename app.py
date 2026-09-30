import datetime
import os
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="OptiQuant - Quantitative Crypto Risk",
    page_icon="⚡",
    layout="centered",
)

# --- ARCHIVOS DE BASE DE DATOS LOCALES ---
USUARIOS_DB = "usuarios_vip.csv"
DIARIO_DB = "diario_trading.csv"

def inicializar_archivos():
    if not os.path.exists(USUARIOS_DB):
        df_u = pd.DataFrame(columns=["email", "wallet", "fecha", "estado"])
        df_u.to_csv(USUARIOS_DB, index=False)

    if not os.path.exists(DIARIO_DB):
        df_d = pd.DataFrame(
            columns=[
                "fecha", "activo", "tipo", "entrada",
                "stop_loss", "take_profit", "resultado",
            ]
        )
        df_d.to_csv(DIARIO_DB, index=False)

inicializar_archivos()

# --- FUNCIONES DE DATOS EN VIVO (BINANCE API - ANTI GEO-BLOQUEO) ---
@st.cache_data(ttl=60)
def obtener_datos_binance(symbol="SOLUSDT", interval="1h", limit=100):
    symbol = symbol.upper().strip()
    
    # Múltiples endpoints para evadir el geo-bloqueo a los servidores de Streamlit
    endpoints = [
        "https://api.binance.us",            
        "https://data-api.binance.vision",   
        "https://api.binance.com",           
        "https://api1.binance.com",          
        "https://api2.binance.com",          
        "https://api3.binance.com"           
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for base_url in endpoints:
        url = f"{base_url}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(
                        data,
                        columns=[
                            "timestamp", "open", "high", "low", "close", "volume",
                            "close_time", "qav", "num_trades", "taker_base_vol",
                            "taker_quote_vol", "ignore",
                        ],
                    )
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    df["cierre"] = df["close"].astype(float)
                    df["high"] = df["high"].astype(float)
                    df["low"] = df["low"].astype(float)
                    df["open"] = df["open"].astype(float)
                    return df
        except Exception:
            continue
            
    return None

# --- INTERFAZ / SIDEBAR ---
st.sidebar.title("Idioma / Language")
idioma = st.sidebar.selectbox("", ["Español", "English"])

st.sidebar.title("Panel de Control")
consultas_restantes = st.sidebar.selectbox(
    "Consultas gratuitas restantes: 3/3", ["Usar plan Gratuito"]
)

vip_menu = st.sidebar.expander("💎 Acceso VIP (Consultas Ilimitadas)")
with vip_menu:
    st.write("Obtén acceso ilimitado de por vida transfiriendo **10 USDT** vía Binance Pay.")
    
    if os.path.exists("qr_binance.jpg"):
        st.image("qr_binance.jpg", caption="Escanea para pagar con Binance Pay", use_container_width=True)
    
    st.info("ID Binance Pay: **35813872**")

    with st.form("form_vip"):
        email_user = st.text_input("Tu Correo / Binance Pay ID")
        submitted_vip = st.form_submit_button("Registrar Pago VIP")
        if submitted_vip and email_user:
            df_u = pd.read_csv(USUARIOS_DB)
            nuevo_registro = pd.DataFrame(
                [[
                    email_user,
                    "BinancePay",
                    datetime.datetime.now().strftime("%Y-%m-%d"),
                    "Activo",
                ]],
                columns=["email", "wallet", "fecha", "estado"],
            )
            df_u = pd.concat([df_u, nuevo_registro], ignore_index=True)
            df_u.to_csv(USUARIOS_DB, index=False)
            st.success("¡Solicitud enviada! Tu cuenta VIP será activada en minutos.")

# --- CUERPO PRINCIPAL DE LA APP ---
st.title("⚡ OptiQuant")
st.markdown("Gestión de riesgo avanzada y motor cuantitativo impulsado por datos en vivo de Binance y Binance Pay.")

ver_diario = st.checkbox("📁 Ver historial de tu diario de trading local")
if ver_diario:
    if os.path.exists(DIARIO_DB):
        df_diario = pd.read_csv(DIARIO_DB)
        st.dataframe(df_diario)
    else:
        st.info("Aún no hay registros en el diario.")

st.markdown("---")
simbolo_input = st.text_input("Ingresa la cripto (ej: SOL, SUI, BTC):", value="SOL").upper().strip()
par_binance = f"{simbolo_input}USDT"

nivel_riesgo = st.selectbox(
    "Nivel de Riesgo:", ["Alto (1.0x ATR)", "Medio (0.7x ATR)", "Conservador (0.5x ATR)"]
)

if st.button("🚀 Calcular Parámetros Cuantitativos"):
    with st.spinner(f"Conectando con servidores globales para {par_binance}..."):
        df = obtener_datos_binance(par_binance)

    if df is not None and not df.empty and "cierre" in df.columns:
        try:
            precio_actual = df["cierre"].iloc[-1]
            atr = (df["high"] - df["low"]).mean()

            factor = 1.0 if "Alto" in nivel_riesgo else (0.7 if "Medio" in nivel_riesgo else 0.5)
            stop_loss = precio_actual - (atr * factor)
            take_profit = precio_actual + (atr * factor * 2)

            st.success(f"¡Datos en vivo obtenidos con éxito para {par_binance}!")

            col1, col2, col3 = st.columns(3)
            col1.metric("Precio Actual", f"${precio_actual:,.4f}")
            col2.metric("Stop Loss Sugerido", f"${stop_loss:,.4f}")
            col3.metric("Take Profit (1:2)", f"${take_profit:,.4f}")

            # Construcción del gráfico de velas japonesas
            fig = go.Figure()
            
            fig.add_trace(
                go.Candlestick(
                    x=df["timestamp"],
                    open=df["open"],
                    high=df["high"],
                    low=df["low"],
                    close=df["cierre"],
                    name="Precio"
                )
            )

            # Línea de Take Profit (Verde)
            fig.add_hline(
                y=take_profit, 
                line_dash="dash", 
                line_color="#00ff00", 
                annotation_text=f"Take Profit", 
                annotation_position="top left",
                annotation_font_color="#00ff00"
            )

            # Línea de Stop Loss (Roja)
            fig.add_hline(
                y=stop_loss, 
                line_dash="dash", 
                line_color="#ff0000", 
                annotation_text=f"Stop Loss", 
                annotation_position="bottom left",
                annotation_font_color="#ff0000"
            )

            # Línea de Entrada (Gris/Blanca)
            fig.add_hline(
                y=precio_actual, 
                line_dash="dot", 
                line_color="#ffffff", 
                annotation_text=f"Entrada", 
                annotation_position="top left",
                annotation_font_color="#ffffff"
            )

            fig.update_layout(
                title=f"Gráfico de Velas y Niveles Operativos - {par_binance}",
                xaxis_title="Tiempo",
                yaxis_title="Precio USDT",
                template="plotly_dark",
                xaxis_rangeslider_visible=False, # Oculta el slider inferior para mejor visualización en móviles
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)

            # Guardar en diario
            nuevo_trade = pd.DataFrame(
                [[
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    par_binance,
                    "Compra Long",
                    precio_actual,
                    stop_loss,
                    take_profit,
                    "Pendiente",
                ]],
                columns=[
                    "fecha", "activo", "tipo", "entrada",
                    "stop_loss", "take_profit", "resultado",
                ],
            )
            df_d = pd.read_csv(DIARIO_DB)
            df_d = pd.concat([df_d, nuevo_trade], ignore_index=True)
            df_d.to_csv(DIARIO_DB, index=False)

        except Exception as e:
            st.error(f"Error procesando los indicadores cuantitativos: {e}")
    else:
        st.error(f"⚠️ No se pudieron obtener datos para **{par_binance}**. Es posible que la moneda no exista o haya bloqueos de red.")