import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
import hashlib

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="OptiQuant - Quantitative Crypto Optimizer", page_icon="⚡", layout="wide")

# --- SISTEMA DE IDIOMAS (DICCIONARIO i18n) ---
TEXTS = {
    "Español": {
        "title": "⚡ OptiQuant",
        "subtitle": "Gestión de riesgo avanzada y motor cuantitativo impulsado por datos en vivo de Binance y Binance Pay.",
        "sidebar_header": "⚙️ Panel de Control",
        "free_queries": "Consultas gratuitas restantes:",
        "vip_welcome": "👑 Bienvenido VIP:",
        "logout": "Cerrar Sesión",
        "vip_access": "💎 Acceso VIP (Consultas Ilimitadas)",
        "tab_login": "Iniciar Sesión",
        "tab_register": "Crear Cuenta",
        "user_lbl": "Usuario",
        "pass_lbl": "Contraseña",
        "btn_login": "Entrar",
        "msg_login_ok": "¡Login exitoso!",
        "msg_login_err": "Credenciales incorrectas",
        "step1": "### 1️⃣ Realiza el pago (10 USDT)",
        "step1_desc": "Escanea el QR o envía el pago a mi Binance Pay ID:",
        "qr_warn": "⚠️ Imagen 'qr_binance.jpg' no encontrada.",
        "pay_id_lbl": "**Binance Pay ID (Cópialo aquí):**",
        "step2": "### 2️⃣ Registra tu acceso VIP",
        "reg_user": "Crea un Usuario",
        "reg_pass": "Crea una Contraseña",
        "reg_order": "Order ID de Binance Pay (Para verificar pago)",
        "btn_reg": "Crear Cuenta VIP",
        "msg_reg_ok": "✅ ¡Cuenta creada! Ve a 'Iniciar Sesión'.",
        "msg_reg_err": "❌ Ese usuario ya existe. Elige otro.",
        "msg_reg_warn": "⚠️ Llena todos los campos.",
        "input_crypto": "Ingresa la cripto (ej: SOL, SUI):",
        "risk_lbl": "Nivel de Riesgo:",
        "risk_opt": ["Alto (1.0x ATR)", "Medio (1.5x ATR)", "Bajo (2.0x ATR)"],
        "btn_calc": "🔍 Calcular Estrategia",
        "support_lbl": "### 💰 Apoya este proyecto",
        "affiliate_lbl": "🟡 Crear cuenta en Binance con descuento",
        "limit_title": "🛑 **LÍMITE GRATUITO ALCANZADO**",
        "limit_desc": "Has utilizado tus 3 cálculos gratuitos. Para seguir operando con precisión institucional, crea tu cuenta VIP en la barra lateral.",
        "analyzing": "Analizando",
        "err_pair": "❌ No se encontró el par",
        "price_lbl": "💵 Precio Actual",
        "sl_lbl": "🎯 Stop-Loss",
        "tp_lbl": "🚀 Take-Profit (1:2)",
        "chart_x": "Fecha",
        "chart_y": "Precio (USDT)",
        "history_lbl": "📂 Ver historial de tu diario de trading local",
        "saved_msg": "📝 Guardado en tu diario de trading."
    },
    "English": {
        "title": "⚡ OptiQuant",
        "subtitle": "Advanced Risk Management & Quantitative Engine powered by Binance Real-Time Data & Binance Pay.",
        "sidebar_header": "⚙️ Control Panel",
        "free_queries": "Free queries remaining:",
        "vip_welcome": "👑 Welcome VIP:",
        "logout": "Log Out",
        "vip_access": "💎 VIP Access (Unlimited Queries)",
        "tab_login": "Log In",
        "tab_register": "Create Account",
        "user_lbl": "Username",
        "pass_lbl": "Password",
        "btn_login": "Enter",
        "msg_login_ok": "Login successful!",
        "msg_login_err": "Invalid credentials",
        "step1": "### 1️⃣ Make the payment (10 USDT)",
        "step1_desc": "Scan the QR or send the payment to my Binance Pay ID:",
        "qr_warn": "⚠️ Image 'qr_binance.jpg' not found.",
        "pay_id_lbl": "**Binance Pay ID (Copy here):**",
        "step2": "### 2️⃣ Register your VIP access",
        "reg_user": "Create a Username",
        "reg_pass": "Create a Password",
        "reg_order": "Binance Pay Order ID (For verification)",
        "btn_reg": "Create VIP Account",
        "msg_reg_ok": "✅ Account created! Go to 'Log In'.",
        "msg_reg_err": "❌ Username already exists. Choose another.",
        "msg_reg_warn": "⚠️ Please fill all fields.",
        "input_crypto": "Enter crypto (e.g., SOL, SUI):",
        "risk_lbl": "Risk Level:",
        "risk_opt": ["High (1.0x ATR)", "Medium (1.5x ATR)", "Low (2.0x ATR)"],
        "btn_calc": "🔍 Calculate Strategy",
        "support_lbl": "### 💰 Support this project",
        "affiliate_lbl": "🟡 Create a Binance account with a discount",
        "limit_title": "🛑 **FREE LIMIT REACHED**",
        "limit_desc": "You have used your 3 free calculations. To continue trading with institutional precision, create your VIP account in the sidebar.",
        "analyzing": "Analyzing",
        "err_pair": "❌ Pair not found",
        "price_lbl": "💵 Current Price",
        "sl_lbl": "🎯 Stop-Loss",
        "tp_lbl": "🚀 Take-Profit (1:2)",
        "chart_x": "Date",
        "chart_y": "Price (USDT)",
        "history_lbl": "📂 View local trading journal history",
        "saved_msg": "📝 Saved to your trading journal."
    }
}

# --- INICIALIZACIÓN DE VARIABLES DE SESIÓN ---
if 'consultas' not in st.session_state: st.session_state.consultas = 0
if 'vip' not in st.session_state: st.session_state.vip = False
if 'usuario_actual' not in st.session_state: st.session_state.usuario_actual = None

# --- SELECTOR DE IDIOMA GLOBAL ---
idioma_seleccionado = st.sidebar.selectbox("🌐 Idioma / Language", ["Español", "English"])
t = TEXTS[idioma_seleccionado]

# --- FUNCIONES DE BASE DE DATOS VIP ---
ARCHIVO_USUARIOS = "usuarios_vip.csv"

def encriptar_clave(clave):
    return hashlib.sha256(clave.encode()).hexdigest()

if not os.path.exists(ARCHIVO_USUARIOS):
    pd.DataFrame(columns=["Usuario", "Clave_Hash"]).to_csv(ARCHIVO_USUARIOS, index=False)

def registrar_usuario(usuario, clave):
    df_users = pd.read_csv(ARCHIVO_USUARIOS)
    if usuario in df_users['Usuario'].values: return False
    nuevo_user = pd.DataFrame([{"Usuario": usuario, "Clave_Hash": encriptar_clave(clave)}])
    nuevo_user.to_csv(ARCHIVO_USUARIOS, mode='a', header=False, index=False)
    return True

def verificar_login(usuario, clave):
    df_users = pd.read_csv(ARCHIVO_USUARIOS)
    clave_hash = encriptar_clave(clave)
    match = df_users[(df_users['Usuario'] == usuario) & (df_users['Clave_Hash'] == clave_hash)]
    return not match.empty

# --- INTERFAZ PRINCIPAL ---
st.title(t["title"])
st.markdown(t["subtitle"])

# --- BARRA LATERAL (MONETIZACIÓN Y CONTROL) ---
st.sidebar.header(t["sidebar_header"])

if st.session_state.vip:
    st.sidebar.success(f"{t['vip_welcome']} {st.session_state.usuario_actual}")
    if st.sidebar.button(t["logout"]):
        st.session_state.vip = False
        st.session_state.usuario_actual = None
        st.rerun()
else:
    st.sidebar.info(f"{t['free_queries']} {3 - st.session_state.consultas}/3")
    
    with st.sidebar.expander(t["vip_access"]):
        tab_login, tab_registro = st.tabs([t["tab_login"], t["tab_register"]])
        
        with tab_login:
            log_user = st.text_input(t["user_lbl"], key="log_user")
            log_pass = st.text_input(t["pass_lbl"], type="password", key="log_pass")
            if st.button(t["btn_login"]):
                if verificar_login(log_user, log_pass):
                    st.session_state.vip = True
                    st.session_state.usuario_actual = log_user
                    st.success(t["msg_login_ok"])
                    st.rerun()
                else:
                    st.error(t["msg_login_err"])
                    
        with tab_registro:
            st.markdown(t["step1"])
            st.markdown(t["step1_desc"])
            
            try:
                st.image("qr_binance.jpg", width=200)
            except:
                st.warning(t["qr_warn"])
            
            st.markdown(t["pay_id_lbl"])
            st.code("35813872", language="text") 
            
            st.markdown("---")
            st.markdown(t["step2"])
            reg_user = st.text_input(t["reg_user"], key="reg_user")
            reg_pass = st.text_input(t["reg_pass"], type="password", key="reg_pass")
            reg_pay_id = st.text_input(t["reg_order"])
            
            if st.button(t["btn_reg"]):
                if reg_user and reg_pass and reg_pay_id:
                    if registrar_usuario(reg_user, reg_pass):
                        st.success(t["msg_reg_ok"])
                    else:
                        st.error(t["msg_reg_err"])
                else:
                    st.warning(t["msg_reg_warn"])

st.sidebar.markdown("---")
input_crypto = st.sidebar.text_input(t["input_crypto"], "SOL")
opcion_riesgo = st.sidebar.selectbox(t["risk_lbl"], t["risk_opt"])

multiplicador = 1.0 if "1.0" in opcion_riesgo else 1.5 if "1.5" in opcion_riesgo else 2.0
btn_analizar = st.sidebar.button(t["btn_calc"])

st.sidebar.markdown("---")
st.sidebar.markdown(t["support_lbl"])
# ENLACE DE AFILIADO OFICIAL DE BINANCE
st.sidebar.markdown(f"[{t['affiliate_lbl']}](https://www.binance.com/referral/earn-together/refer2earn-usdc/claim?hl=es&ref=GRO_28502_RL2T6&utm_source=referral_entrance)")

# --- FUNCIÓN DE DATOS ---
@st.cache_data(ttl=60)
def obtener_datos(simbolo):
    if not simbolo.endswith("USDT"): simbolo += "USDT"
    url = f"https://api.binance.com/api/v3/klines?symbol={simbolo.upper()}&interval=1d&limit=30"
    try:
        req = requests.get(url).json()
        df = pd.DataFrame(req, columns=['tiempo_apertura', 'apertura', 'maximo', 'minimo', 'cierre', 'volumen', 'tiempo_cierre', 'vol_cotizado', 'num_operaciones', 'vol_compra_base', 'vol_compra_cotizado', 'ignorar'])
        df['fecha'] = pd.to_datetime(df['tiempo_apertura'], unit='ms')
        df[['apertura', 'maximo', 'minimo', 'cierre']] = df[['apertura', 'maximo', 'minimo', 'cierre']].astype(float)
        return df, simbolo.upper()
    except: return None, simbolo.upper()

# --- LÓGICA PRINCIPAL Y PAYWALL ---
if btn_analizar:
    if not st.session_state.vip and st.session_state.consultas >= 3:
        st.error(t["limit_title"])
        st.warning(t["limit_desc"])
    else:
        with st.spinner(f"{t['analyzing']} {input_crypto}..."):
            df, par = obtener_datos(input_crypto)
            
        if df is None:
            st.error(f"{t['err_pair']} '{input_crypto}'.")
        else:
            if not st.session_state.vip:
                st.session_state.consultas += 1
                
            df['rango'] = df['maximo'] - df['minimo']
            precio_actual = df['cierre'].iloc[-1]
            dist_sl = df['rango'].mean() * multiplicador
            precio_sl = precio_actual - dist_sl
            precio_tp = precio_actual + (dist_sl * 2)
            
            c1, c2, c3 = st.columns(3)
            c1.metric(t["price_lbl"], f"${precio_actual:,.4f}")
            c2.metric(t["sl_lbl"], f"${precio_sl:,.4f}", f"-{(dist_sl/precio_actual)*100:.2f}%", delta_color="inverse")
            c3.metric(t["tp_lbl"], f"${precio_tp:,.4f}", f"+{((dist_sl*2)/precio_actual)*100:.2f}%")
            
            fig = go.Figure(data=[go.Candlestick(x=df['fecha'], open=df['apertura'], high=df['maximo'], low=df['minimo'], close=df['cierre'], name="Precio")])
            fig.add_hline(y=precio_tp, line_dash="dash", line_color="green", annotation_text="TP")
            fig.add_hline(y=precio_actual, line_dash="dot", line_color="blue", annotation_text="Actual")
            fig.add_hline(y=precio_sl, line_dash="dash", line_color="red", annotation_text="SL")
            fig.update_layout(xaxis_title=t["chart_x"], yaxis_title=t["chart_y"], template="plotly_dark", height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            nuevo_registro = pd.DataFrame([{"Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Simbolo": par, "Precio": precio_actual, "StopLoss": precio_sl, "TakeProfit": precio_tp}])
            nuevo_registro.to_csv("diario_trading.csv", mode='a', header=not os.path.exists("diario_trading.csv"), index=False)
            
            st.success(t["saved_msg"])
            
if st.checkbox(t["history_lbl"]):
    try:
        st.dataframe(pd.read_csv("diario_trading.csv"))
    except:
        pass