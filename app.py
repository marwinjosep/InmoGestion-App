import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import hashlib
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="InmoGestión Pro", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1A2980 0%, #26D0CE 100%); }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton>button { background: linear-gradient(45deg, #FFD700, #FDB931); color: #2c3e50; font-weight: bold; border: none; }
    .login-box { padding: 2rem; border-radius: 10px; background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ROBUSTA A GOOGLE SHEETS ---
def conectar_google_sheets():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # Detectar si estamos en la Nube (Secrets) o Local
        if "type" in st.secrets:
            creds_dict = dict(st.secrets)
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('secrets.json', scope)
        
        client = gspread.authorize(creds)
        sheet = client.open("Base_Datos_InmoGestion")
        return sheet
    except Exception as e:
        return None

# --- 3. FUNCIONES DE CORREO Y SEGURIDAD ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

def enviar_correo(destinatario, nueva_clave):
    # Intenta leer credenciales de correo desde Secrets
    remitente = st.secrets.get("correo_emisor")
    clave_app = st.secrets.get("clave_emisor")
    
    if not remitente or not clave_app:
        return False, "Faltan configurar correo_emisor en Secrets."

    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = "🔐 Recuperación de Clave - InmoGestión Pro"
    body = f"Hola,\n\nTu nueva contraseña temporal es: {nueva_clave}\n\nIngresa y cámbiala lo antes posible."
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, clave_app)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
        return True, "Correo enviado"
    except Exception as e:
        return False, str(e)

# --- 4. GESTIÓN DE DATOS ---
def cargar_tabla(pestana):
    sh = conectar_google_sheets()
    if sh:
        try:
            return pd.DataFrame(sh.worksheet(pestana).get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

def guardar_fila(pestana, datos):
    sh = conectar_google_sheets()
    if sh:
        try:
            try: ws = sh.worksheet(pestana)
            except: ws = sh.add_worksheet(pestana, 100, 20)
            ws.append_row(datos)
            return True
        except: return False
    return False

# --- 5. LÓGICA DE SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = ""
if 'user_name' not in st.session_state: st.session_state.user_name = ""

# =======================================================
#  VISTA DE LOGIN (CON RECUPERAR)
# =======================================================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><div style='text-align: center;'><h1>🏢 InmoGestión Pro</h1></div>", unsafe_allow_html=True)
        
        # AQUI ESTAN LAS 3 PESTAÑAS
        tab1, tab2, tab3 = st.tabs(["🔑 INGRESAR", "📝 REGISTRO", "❓ RECUPERAR"])
        
        # 1. INGRESAR
        with tab1:
            with st.form("login"):
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                if st.form_submit_button("ENTRAR", use_container_width=True):
                    df = cargar_tabla("Usuarios")
                    if not df.empty and u in df["Usuario"].values:
                        user = df[df["Usuario"] == u].iloc[0]
                        if check_hashes(p, str(user["Password"])):
                            st.session_state.logged_in = True
                            st.session_state.user_name = user["Nombre"]
                            st.session_state.user_role = user["Rol"]
                            st.rerun()
                        else: st.error("Contraseña incorrecta")
                    else: st.error("Usuario no encontrado")

        # 2. REGISTRO
        with tab2:
            with st.form("reg"):
                nu = st.text_input("Usuario Nuevo")
                np = st.text_input("Contraseña", type="password")
                nn = st.text_input("Nombre")
                ne = st.text_input("Email (Para recuperación)")
                nr = st.selectbox("Rol", ["Agente", "Administrador"])
                if st.form_submit_button("CREAR CUENTA", use_container_width=True):
                    if guardar_fila("Usuarios", [nu, make_hashes(np), nn, nr, ne]):
                        st.success("Usuario creado exitosamente.")
                    else: st.error("Error conectando a la base de datos.")

        # 3. RECUPERAR (LA QUE FALTABA)
        with tab3:
            st.write("¿Olvidaste tu contraseña? Te enviaremos una temporal.")
            ru = st.text_input("Escribe tu Usuario")
            if st.button("ENVIAR CORREO DE RECUPERACIÓN", use_container_width=True):
                sh = conectar_google_sheets()
                if sh:
                    try:
                        ws = sh.worksheet("Usuarios")
                        df = pd.DataFrame(ws.get_all_records())
                        if not df.empty and ru in df["Usuario"].values:
                            # Encontrar email
                            fila = df[df["Usuario"] == ru].iloc[0]
                            email_dest = fila["Email"]
                            # Generar clave y hash
                            nueva_clave = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
                            nuevo_hash = make_hashes(nueva_clave)
                            
                            # Actualizar en Sheets (Busca la celda del usuario y actualiza la pass)
                            cell = ws.find(ru)
                            ws.update_cell(cell.row, 2, nuevo_hash) # Asume col 2 es Password
                            
                            # Enviar correo
                            ok, msg = enviar_correo(email_dest, nueva_clave)
                            if ok: st.success(f"Correo enviado a {email_dest}")
                            else: st.error(f"Error enviando correo: {msg}")
                        else: st.error("Usuario no existe.")
                    except Exception as e: st.error(f"Error: {e}")

# =======================================================
#  SISTEMA PRINCIPAL
# =======================================================
else:
    with st.sidebar:
        st.title("InmoGestión Pro")
        st.write(f"👤 **{st.session_state.user_name}**")
        st.caption(f"Rol: {st.session_state.user_role}")
        menu = st.radio("Menú", ["📂 Inventario", "➕ Nuevo Registro", "📊 Estadísticas"])
        if st.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.rerun()

    if menu == "➕ Nuevo Registro":
        st.header("📝 Nueva Propiedad")
        with st.form("new_p"):
            c1, c2 = st.columns(2)
            tit = c1.text_input("Título")
            pre = c2.number_input("Precio", min_value=0.0)
            ubi = c1.text_input("Ubicación")
            prop = c2.text_input("Propietario")
            est = st.selectbox("Estado", ["Disponible", "Vendida", "Rentada"])
            if st.form_submit_button("GUARDAR"):
                datos = [str(date.today()), tit, pre, ubi, prop, est]
                if guardar_fila("Propiedades", datos): st.success("Guardado en la Nube ☁️")
                else: st.error("Error guardando")

    elif menu == "📂 Inventario":
        st.header("📂 Inventario")
        df = cargar_tabla("Propiedades")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else: st.info("No hay propiedades aún.")

    elif menu == "📊 Estadísticas":
        st.header("📊 Estadísticas")
        df = cargar_tabla("Propiedades")
        if not df.empty and "Precio" in df.columns:
            st.metric("Total Inventario", f"${df['Precio'].sum():,.0f}")
            st.bar_chart(df, x="Título", y="Precio")
        else: st.warning("Faltan datos.")