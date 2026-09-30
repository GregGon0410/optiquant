import datetime
import os
import uuid
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="OptiQuant - Quantitative Crypto Risk",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="expanded"
)
# --- CONEXIÓN A GOOGLE SHEETS (Caché para optimizar rendimiento) ---
@st.cache_resource
def conectar_base_datos():
    try:
        # Definir los permisos necesarios para la API
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        # Cargar el archivo JSON local
        credenciales = Credentials.from_service_account_file("credenciales.json", scopes=scopes)
        cliente = gspread.authorize(credenciales)
        
        # Abrir la hoja de cálculo por su nombre exacto
        db = cliente.open("OptiQuant_DB")
        hoja_vip = db.worksheet("usuarios_vip")
        
        return hoja_vip
    except Exception as e:
        st.error(f"Error conectando a la base de datos Google Sheets. Verifica credenciales.json. Error: {e}")
        return None

# Inicializar la conexión
hoja_vip = conectar_base_datos()
# --- FUNCIONES DE BASE DE DATOS EN LA NUBE ---
def es_usuario_vip_gs(email_consulta):
    """Verifica si el correo está en Google Sheets y está Activo"""
    if hoja_vip is None:
        return False
        
    try:
        registros = hoja_vip.get_all_records()
        for fila in registros:
            if str(fila.get("email", "")).strip().lower() == email_consulta.strip().lower():
                if str(fila.get("estado", "")) == "Activo":
                    return True
    except Exception as e:
        st.error(f"Error al leer la base de datos: {e}")
    return False

def registrar_nuevo_vip_gs(email, wallet="N/A"):
    """Guarda un nuevo usuario VIP directamente en Google Sheets"""
    if hoja_vip is None:
        st.error("No hay conexión a la base de datos para registrar.")
        return False
        
    try:
        import datetime
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hoja_vip.append_row([email, wallet, fecha_actual, "Activo"])
        return True
    except Exception as e:
        st.error(f"Error al escribir en la base de datos: {e}")
        return False
# --- ARCHIVOS DE BASE DE DATOS LOCALES ---
USUARIOS_DB = "usuarios_vip.csv"
DIARIO_DB = "diario_trading.csv"
VISITAS_DB = "visitas.csv"

def inicializar_archivos():
    if not os.path.exists(USUARIOS_DB):
        pd.DataFrame(columns=["email", "wallet", "fecha", "estado"]).to_csv(USUARIOS_DB, index=False)
    if not os.path.exists(DIARIO_DB):
        pd.DataFrame(columns=["fecha", "activo", "tipo", "entrada", "stop_loss", "take_profit", "resultado"]).to_csv(DIARIO_DB, index=False)
    if not os.path.exists(VISITAS_DB):
        pd.DataFrame(columns=["uid", "consultas"]).to_csv(VISITAS_DB, index=False)

inicializar_archivos()

# --- SISTEMA DE RASTREO ANTI-REFRESH (HUELLA DIGITAL) ---
# Le asigna un ID único a cada visitante en la URL para que no puedan engañar al contador recargando la página
if "uid" not in st.query_params:
    nuevo_uid = str(uuid.uuid4())
    st.query_params["uid"] = nuevo_uid
    df_v = pd.read_csv(VISITAS_DB)
    nuevo_registro = pd.DataFrame([{"uid": nuevo_uid, "consultas": 3}])
    df_v = pd.concat([df_v, nuevo_registro], ignore_index=True)
    df_v.to_csv(VISITAS_DB, index=False)

uid_actual = st.query_params["uid"]

# Cargar las consultas reales del usuario actual desde la base de datos
df_visitas = pd.read_csv(VISITAS_DB)
if uid_actual not in df_visitas['uid'].values:
    # Por si acaso el registro se borró, lo recreamos
    nuevo_registro = pd.DataFrame([{"uid": uid_actual, "consultas": 3}])
    df_visitas = pd.concat([df_visitas, nuevo_registro], ignore_index=True)
    df_visitas.to_csv(VISITAS_DB, index=False)
    consultas_restantes = 3
else:
    consultas_restantes = int(df_visitas.loc[df_visitas['uid'] == uid_actual, 'consultas'].values[0])

# Estado VIP de la sesión actual
if 'es_vip' not in st.session_state:
    st.session_state['es_vip'] = False

# --- FUNCIÓN INTELIGENTE DE FORMATO DE PRECIOS ---
def formatear_precio(valor):
    if valor < 0.00001: return f"${valor:,.10f}"
    elif valor < 0.001: return f"${valor:,.8f}"
    elif valor < 1: return f"${valor:,.6f}"
    else: return f"${valor:,.4f}"

# --- FUNCIONES DE DATOS EN VIVO (BINANCE API - ANTI GEO-BLOQUEO) ---
@st.cache_data(ttl=60)
def obtener_datos_binance(symbol="SOLUSDT", interval="1h", limit=100):
    symbol = symbol.upper().strip()
    endpoints = [
        "https://api.binance.us", "https://data-api.binance.vision",   
        "https://api.binance.com", "https://api1.binance.com",          
        "https://api2.binance.com", "https://api3.binance.com"           
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    for base_url in endpoints:
        url = f"{base_url}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            response = requests.get(url, headers=headers, timeout=4)
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume", "close_time", "qav", "num_trades", "taker_base_vol", "taker_quote_vol", "ignore"])
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    df["cierre"] = df["close"].astype(float)
                    df["high"] = df["high"].astype(float)
                    df["low"] = df["low"].astype(float)
                    df["open"] = df["open"].astype(float)
                    return df
        except Exception:
            continue
    return None

# --- DICCIONARIO DE IDIOMAS ---
st.sidebar.title("Idioma / Language")
idioma = st.sidebar.selectbox("", ["Español", "English"])

if idioma == "Español":
    t = {
        "ctrl_panel": "Panel de Control",
        "vip_buy": "💎 Adquirir Acceso VIP (10 USDT)",
        "vip_desc": "Obtén acceso ilimitado de por vida transfiriendo **10 USDT**.",
        "qr_cap": "Escanea para pagar con Binance Pay",
        "email_ph": "Tu Correo / Binance Pay ID",
        "btn_notify": "Notificar Pago",
        "vip_login": "🔑 Ya soy VIP (Ingresar)",
        "login_ph": "Ingresa el correo con el que pagaste:",
        "btn_login": "Verificar y Entrar",
        "desc": "Gestión de riesgo avanzada y motor cuantitativo impulsado por datos en vivo.",
        "hist": "📁 Ver historial de tu diario de trading local",
        "no_hist": "Aún no hay registros en el diario.",
        "input": "Ingresa la cripto (ej: BTTC, SOL, SHIB):",
        "risk": "Nivel de Riesgo:",
        "r_high": "Alto (1.0x ATR)", "r_med": "Medio (0.7x ATR)", "r_low": "Conservador (0.5x ATR)",
        "btn_calc": "🚀 Calcular Parámetros Cuantitativos",
        "err_limit": "🔒 **Has agotado tus 3 consultas gratuitas.** ¡Adquiere el pase VIP en el panel izquierdo para tener acceso ilimitado!",
        "success": "¡Datos en vivo obtenidos con éxito para",
        "p_cur": "Precio Actual", "p_sl": "Stop Loss Sugerido", "p_tp": "Take Profit (1:2)",
        "err_data": "⚠️ No se pudieron obtener datos para",
        "err_math": "Error matemático procesando los indicadores.",
        "vip_active": "👑 **Modo VIP Activo:** Consultas Ilimitadas",
        "free_left": "🟢 Consultas gratuitas restantes:",
        "free_out": "🔴 **Consultas agotadas (0/3).** ¡Adquiere VIP!"
    }
else:
    t = {
        "ctrl_panel": "Control Panel",
        "vip_buy": "💎 Get VIP Access (10 USDT)",
        "vip_desc": "Get unlimited lifetime access by transferring **10 USDT**.",
        "qr_cap": "Scan to pay with Binance Pay",
        "email_ph": "Your Email / Binance Pay ID",
        "btn_notify": "Notify Payment",
        "vip_login": "🔑 I am already VIP (Login)",
        "login_ph": "Enter the email you paid with:",
        "btn_login": "Verify and Enter",
        "desc": "Advanced risk management and quantitative engine powered by live data.",
        "hist": "📁 View your local trading diary history",
        "no_hist": "No records in the diary yet.",
        "input": "Enter crypto (e.g., BTTC, SOL, SHIB):",
        "risk": "Risk Level:",
        "r_high": "High (1.0x ATR)", "r_med": "Medium (0.7x ATR)", "r_low": "Conservative (0.5x ATR)",
        "btn_calc": "🚀 Calculate Quantitative Parameters",
        "err_limit": "🔒 **You have exhausted your 3 free queries.** Get the VIP pass on the left panel for unlimited access!",
        "success": "Live data successfully obtained for",
        "p_cur": "Current Price", "p_sl": "Suggested Stop Loss", "p_tp": "Take Profit (1:2)",
        "err_data": "⚠️ Could not get data for",
        "err_math": "Mathematical error processing indicators.",
        "vip_active": "👑 **VIP Mode Active:** Unlimited Queries",
        "free_left": "🟢 Free queries remaining:",
        "free_out": "🔴 **Queries exhausted (0/3).** Get VIP!"
    }

# --- INTERFAZ / SIDEBAR ---
st.sidebar.title(t["ctrl_panel"])
panel_status = st.sidebar.empty()

vip_menu = st.sidebar.expander(t["vip_buy"])
with vip_menu:
    st.write(t["vip_desc"])
    if os.path.exists("qr_binance.jpg"):
        st.image("qr_binance.jpg", caption=t["qr_cap"], use_container_width=True)
    st.info("ID Binance Pay: **35813872**")
    with st.form("form_vip"):
        email_user = st.text_input(t["email_ph"])
        submitted_vip = st.form_submit_button(t["btn_notify"])
        if submitted_vip and email_user:
                    # Usamos la nueva función de Google Sheets
                    if registrar_nuevo_vip_gs(email_user, "BinancePay"):
                        st.session_state['es_vip'] = True
                        st.success("OK!")
                        st.rerun() 

login_menu = st.sidebar.expander(t["vip_login"])
with login_menu:
    email_login = st.text_input(t["login_ph"])
    if st.button(t["btn_login"]):
                # Verificamos directamente en Google Sheets
                if es_usuario_vip_gs(email_login):
                    st.session_state['es_vip'] = True
                    st.success("OK!")
                    st.rerun()
                else:
                    st.error("Error / Not found")   

# --- ACTUALIZACIÓN VISUAL DEL CONTADOR ---
if st.session_state['es_vip']:
    panel_status.success(t["vip_active"])
else:
    if consultas_restantes > 0:
        panel_status.info(f"{t['free_left']} **{consultas_restantes}/3**")
    else:
        panel_status.error(t["free_out"])

# --- CUERPO PRINCIPAL DE LA APP ---
st.title("⚡ OptiQuant")
st.markdown(t["desc"])

ver_diario = st.checkbox(t["hist"])
if ver_diario:
    if os.path.exists(DIARIO_DB):
        st.dataframe(pd.read_csv(DIARIO_DB), use_container_width=True)
    else:
        st.info(t["no_hist"])

st.markdown("---")
simbolo_input = st.text_input(t["input"], value="BTTC").upper().strip()
par_binance = f"{simbolo_input}USDT"
nivel_riesgo = st.selectbox(t["risk"], [t["r_high"], t["r_med"], t["r_low"]])

if st.button(t["btn_calc"]):
    if not st.session_state['es_vip'] and consultas_restantes <= 0:
        st.error(t["err_limit"])
    else:
        with st.spinner(f"Conectando / Connecting {par_binance}..."):
            df = obtener_datos_binance(par_binance)

        if df is not None and not df.empty and "cierre" in df.columns:
            try:
                # Restar la consulta y guardar en base de datos al instante
                if not st.session_state['es_vip']:
                    consultas_restantes -= 1
                    df_visitas.loc[df_visitas['uid'] == uid_actual, 'consultas'] = consultas_restantes
                    df_visitas.to_csv(VISITAS_DB, index=False)
                    # Forzar recarga ligera para que el panel lateral actualice el número
                    if consultas_restantes == 0:
                         st.rerun()

                precio_actual = df["cierre"].iloc[-1]
                atr = (df["high"] - df["low"]).mean()

                factor = 1.0 if t["r_high"] in nivel_riesgo else (0.7 if t["r_med"] in nivel_riesgo else 0.5)
                stop_loss = precio_actual - (atr * factor)
                take_profit = precio_actual + (atr * factor * 2)

                st.success(f"{t['success']} {par_binance}!")

                col1, col2, col3 = st.columns(3)
                col1.metric(t["p_cur"], formatear_precio(precio_actual))
                col2.metric(t["p_sl"], formatear_precio(stop_loss))
                col3.metric(t["p_tp"], formatear_precio(take_profit))

                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=df["timestamp"], open=df["open"], high=df["high"], low=df["low"], close=df["cierre"], name="Price"))
                fig.add_hline(y=take_profit, line_dash="dash", line_color="#00ff00", annotation_text="TP", annotation_position="top left", annotation_font_color="#00ff00")
                fig.add_hline(y=stop_loss, line_dash="dash", line_color="#ff0000", annotation_text="SL", annotation_position="bottom left", annotation_font_color="#ff0000")
                fig.add_hline(y=precio_actual, line_dash="dot", line_color="#ffffff", annotation_text="Entry", annotation_position="top left", annotation_font_color="#ffffff")
                fig.update_layout(title=f"{par_binance}", xaxis_title="Time", yaxis_title="Price USDT", template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
                fig.update_yaxes(exponentformat="none")
                st.plotly_chart(fig, use_container_width=True)

                nuevo_trade = pd.DataFrame([[datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), par_binance, "Long", precio_actual, stop_loss, take_profit, "Pending"]], columns=["fecha", "activo", "tipo", "entrada", "stop_loss", "take_profit", "resultado"])
                df_d = pd.read_csv(DIARIO_DB)
                pd.concat([df_d, nuevo_trade], ignore_index=True).to_csv(DIARIO_DB, index=False)
                
                # Refrescar la pantalla si el usuario cambió de número para que el panel lo detecte
                st.rerun()

            except Exception as e:
                st.error(t["err_math"])
        else:
            st.error(f"{t['err_data']} **{par_binance}**.")