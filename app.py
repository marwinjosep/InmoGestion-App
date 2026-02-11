import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import hashlib
import random
import string
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="InmoGestión Pro", page_icon="🏢", layout="wide")

# --- 2. CONEXIÓN INTELIGENTE A GOOGLE SHEETS (NUBE + LOCAL) ---
def conectar_google_sheets():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Primero intentamos leer desde los Secrets de la Nube (Streamlit Cloud)
        if "project_id" in st.secrets:
            creds_dict = {
                "type": st.secrets["type"],
                "project_id": st.secrets["project_id"],
                "private_key_id": st.secrets["private_key_id"],
                "private_key": st.secrets["private_key"],
                "client_email": st.secrets["client_email"],
                "client_id": st.secrets["client_id"],
                "auth_uri": st.secrets["auth_uri"],
                "token_uri": st.secrets["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["client_x509_cert_url"],
            }
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        # Si no hay secrets (estamos en VS Code local), buscamos el archivo físico
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('secrets.json', scope)
            
        client = gspread.authorize(creds)
        sheet = client.open("Base_Datos_InmoGestion")
        return sheet
    except Exception as e:
        st.error(f"❌ Error conectando a Google Sheets: {e}")
        return None

# --- 3. FUNCIONES DE CORREO Y SEGURIDAD ---
def obtener_credenciales_correo():
    """Busca el correo emisor en Secrets o en archivo local"""
    if "correo_emisor" in st.secrets:
        return st.secrets["correo_emisor"], st.secrets["clave_emisor"]
    try:
        with open('secrets.json') as f:
            data = json.load(f)
            return data.get('correo_emisor'), data.get('clave_emisor')
    except: return None, None

def enviar_correo_recuperacion(destinatario, nueva_clave):
    remitente, clave_app = obtener_credenciales_correo()
    if not remitente: return False, "Faltan credenciales"
    
    msg = MIMEMultipart()
    msg['From'], msg['To'], msg['Subject'] = remitente, destinatario, "🔐 Nueva Clave - InmoGestión"
    msg.attach(MIMEText(f"Tu clave temporal es: {nueva_clave}", 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, clave_app)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
        return True, "Enviado"
    except Exception as e: return False, str(e)

# --- 4. FUNCIONES DE DATOS ---
def cargar_datos(pestana):
    sheet = conectar_google_sheets()
    if sheet:
        try:
            worksheet = sheet.worksheet(pestana)
            return pd.DataFrame(worksheet.get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

def guardar_registro_sheet(pestana, datos_lista):
    sheet = conectar_google_sheets()
    if sheet:
        try:
            sheet.worksheet(pestana).append_row(datos_lista)
            return True
        except: return False
    return False

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

# --- 5. INTERFAZ DE USUARIO (ESTILOS) ---
st.markdown("""<style>
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1A2980 0%, #26D0CE 100%); }
    .stApp { background-color: #F8F9FA; }
    .stButton>button { background: linear-gradient(45deg, #FFD700, #FDB931); font-weight: bold; border: none; }
</style>""", unsafe_allow_html=True)

# --- 6. LOGICA DE SESIÓN Y LOGIN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    tab1, tab2, tab3 = st.tabs(["🔑 LOGIN", "📝 REGISTRO", "❓ RECUPERAR"])
    
    with tab1:
        with st.form("login"):
            u, p = st.text_input("Usuario"), st.text_input("Clave", type="password")
            if st.form_submit_button("INGRESAR"):
                df_u = cargar_datos("Usuarios")
                if not df_u.empty and u in df_u["Usuario"].values:
                    row = df_u[df_u["Usuario"] == u].iloc[0]
                    if check_hashes(p, str(row["Password"])):
                        st.session_state.logged_in, st.session_state.user_name, st.session_state.user_role = True, row["Nombre"], row["Rol"]
                        st.rerun()
                st.error("Datos incorrectos")

    with tab2:
        with st.form("reg"):
            nu, np, nn, ne = st.text_input("Usuario"), st.text_input("Clave", type="password"), st.text_input("Nombre"), st.text_input("Email")
            nr = st.selectbox("Rol", ["Agente", "Administrador"])
            if st.form_submit_button("REGISTRAR"):
                if nu and np and nn and ne:
                    if guardar_registro_sheet("Usuarios", [nu, make_hashes(np), nn, nr, ne]): st.success("¡Creado!")
                    else: st.error("Error al guardar")

    with tab3:
        ru = st.text_input("Usuario para recuperar")
        if st.button("Enviar correo"):
            df_u = cargar_datos("Usuarios")
            if not df_u.empty and ru in df_u["Usuario"].values:
                email = df_u[df_u["Usuario"] == ru].iloc[0]["Email"]
                n_key = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
                # Aquí iría la lógica de actualizar en Sheets (actualizar_clave_usuario)
                exito, msg = enviar_correo_recuperacion(email, n_key)
                if exito: st.success(f"Enviado a {email}")
                else: st.error(msg)

# --- 7. SISTEMA PRINCIPAL ---
else:
    with st.sidebar:
        st.title("InmoGestión Pro")
        menu = st.radio("Menú", ["📂 Inventario", "➕ Nuevo Registro", "📊 Estadísticas"])
        if st.button("Salir"): 
            st.session_state.logged_in = False
            st.rerun()

    if menu == "📂 Inventario":
        st.header("Propiedades en la Nube")
        df = cargar_datos("Propiedades")
        if not df.empty: st.dataframe(df)
        else: st.info("Sin datos.")

    elif menu == "➕ Nuevo Registro":
        st.header("Nueva Propiedad")
        with st.form("prop"):
            tit = st.text_input("Título")
            pre = st.number_input("Precio", min_value=0.0)
            if st.form_submit_button("Guardar"):
                if guardar_registro_sheet("Propiedades", [str(pd.Timestamp.now()), tit, pre]): st.success("Guardado")

    elif menu == "📊 Estadísticas":
        st.header("Panel de Control")
        df = cargar_datos("Propiedades")
        if not df.empty:
            st.metric("Total Propiedades", len(df))
            st.metric("Cartera Total", f"$ {df['Precio Final'].sum():,.2f}")