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
from datetime import date, time

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS ---
st.set_page_config(page_title="InmoGestión Pro", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    /* BARRA LATERAL */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1A2980 0%, #26D0CE 100%); }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    
    /* BOTONES */
    .stButton>button {
        background: linear-gradient(45deg, #FFD700, #FDB931);
        color: #2c3e50 !important;
        border: none;
        font-weight: bold;
    }
    
    /* LOGIN BOX */
    .login-box { 
        padding: 30px; 
        background: white; 
        border-radius: 10px; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.1); 
        text-align: center; 
        border: 1px solid #e0e0e0;
    }
    
    /* TITULOS */
    h1, h2, h3 { color: #1A2980; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN INTELIGENTE A GOOGLE SHEETS ---
def conectar_google_sheets():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Intenta leer desde los Secrets de la Nube (Streamlit Cloud)
        if "type" in st.secrets:
            creds_dict = dict(st.secrets)
            # Limpieza de claves privadas para evitar errores de formato
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # Si estamos en local y existe el archivo json
            creds = ServiceAccountCredentials.from_json_keyfile_name('secrets.json', scope)
            
        client = gspread.authorize(creds)
        sheet = client.open("Base_Datos_InmoGestion")
        return sheet
    except Exception as e:
        # Si falla, devolvemos None pero no rompemos la app visualmente
        return None

# --- 3. FUNCIONES DE DATOS ---
def cargar_datos(pestana):
    sheet = conectar_google_sheets()
    if sheet:
        try:
            worksheet = sheet.worksheet(pestana)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except gspread.exceptions.WorksheetNotFound:
            return pd.DataFrame()
    return pd.DataFrame() # Retorna vacío si no hay conexión para no romper

def guardar_registro_sheet(pestana, datos_lista):
    sheet = conectar_google_sheets()
    if sheet:
        try:
            # Verifica si la hoja existe, si no, la crea (opcional)
            try:
                worksheet = sheet.worksheet(pestana)
            except:
                worksheet = sheet.add_worksheet(title=pestana, rows="100", cols="20")
                # Agregar encabezados si es nueva (simplificado)
            
            worksheet.append_row(datos_lista)
            return True
        except Exception as e:
            st.error(f"Error guardando: {e}")
            return False
    return False

# --- 4. SEGURIDAD ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

# --- 5. LOGICA DE SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = ""
if 'user_name' not in st.session_state: st.session_state.user_name = ""

# =======================================================
#  VISTA DE LOGIN (SI NO ESTÁ LOGUEADO)
# =======================================================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""<div class="login-box"><h1>🏢 InmoGestión Pro</h1><p>Acceso Corporativo Seguro</p></div>""", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔑 INGRESAR", "📝 REGISTRARSE"])
        
        with tab1:
            with st.form("login_form"):
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                if st.form_submit_button("ENTRAR", use_container_width=True):
                    df_users = cargar_datos("Usuarios")
                    if not df_users.empty and u in df_users["Usuario"].values:
                        user_data = df_users[df_users["Usuario"] == u].iloc[0]
                        if check_hashes(p, str(user_data["Password"])):
                            st.session_state.logged_in = True
                            st.session_state.user_name = user_data["Nombre"]
                            st.session_state.user_role = user_data["Rol"]
                            st.rerun()
                        else: st.error("Contraseña incorrecta")
                    else: st.error("Usuario no encontrado o error de conexión")

        with tab2:
            with st.form("register_form"):
                nu = st.text_input("Nuevo Usuario")
                np = st.text_input("Contraseña", type="password")
                nn = st.text_input("Nombre Completo")
                ne = st.text_input("Email")
                nr = st.selectbox("Rol", ["Agente", "Administrador"])
                if st.form_submit_button("CREAR CUENTA", use_container_width=True):
                    if nu and np and nn:
                        # Guardamos: Usuario, PasswordHash, Nombre, Rol, Email
                        if guardar_registro_sheet("Usuarios", [nu, make_hashes(np), nn, nr, ne]):
                            st.success("¡Usuario creado! Ahora puedes ingresar.")
                        else:
                            st.error("No se pudo conectar con la base de datos.")

# =======================================================
#  SISTEMA PRINCIPAL (YA LOGUEADO)
# =======================================================
else:
    with st.sidebar:
        st.title("InmoGestión Pro")
        st.write(f"Hola, **{st.session_state.user_name}**")
        st.caption(f"Perfil: {st.session_state.user_role}")
        st.markdown("---")
        menu = st.radio("Navegación", ["📂 Inventario", "➕ Nuevo Registro", "📊 Estadísticas", "⚙️ Configuración"])
        st.markdown("---")
        if st.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.rerun()

    # --- PESTAÑA: INVENTARIO ---
    if menu == "📂 Inventario":
        st.header("Propiedades en Cartera")
        df = cargar_datos("Propiedades")
        if not df.empty:
            # Filtros rápidos
            filtro = st.text_input("🔍 Buscar por título, barrio o propietario...")
            if filtro:
                df = df[df.astype(str).apply(lambda x: x.str.contains(filtro, case=False)).any(axis=1)]
            
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay propiedades registradas o no hay conexión a la nube.")

    # --- PESTAÑA: NUEVO REGISTRO ---
    elif menu == "➕ Nuevo Registro":
        st.header("📝 Registrar Nueva Propiedad")
        st.info("Los datos se guardarán directamente en Google Sheets.")
        
        with st.form("new_prop_form"):
            col1, col2 = st.columns(2)
            with col1:
                titulo = st.text_input("Título del Anuncio")
                precio = st.number_input("Precio Final", min_value=0.0, step=1000000.0)
                ubicacion = st.text_input("Ciudad / Barrio")
            with col2:
                propietario = st.text_input("Nombre Propietario")
                telefono = st.text_input("Teléfono Contacto")
                estado = st.selectbox("Estado", ["Disponible", "Vendida", "Rentada"])
            
            desc = st.text_area("Descripción / Notas")
            
            # Cálculo automático de ganancia (Ej: 3%)
            ganancia_estimada = precio * 0.03
            st.caption(f"💰 Comisión estimada (3%): ${ganancia_estimada:,.0f}")

            if st.form_submit_button("GUARDAR EN LA NUBE", type="primary"):
                fecha_hoy = str(date.today())
                datos = [fecha_hoy, titulo, precio, ubicacion, propietario, telefono, estado, desc, ganancia_estimada]
                
                if guardar_registro_sheet("Propiedades", datos):
                    st.success("✅ Propiedad guardada exitosamente en Google Sheets")
                else:
                    st.error("❌ Error de conexión. Verifica los Secrets.")

    # --- PESTAÑA: ESTADÍSTICAS ---
    elif menu == "📊 Estadísticas":
        st.header("Tablero de Control")
        df = cargar_datos("Propiedades")
        if not df.empty and "Precio Final" in df.columns:
            total_valor = df["Precio Final"].sum()
            total_props = len(df)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Propiedades", total_props)
            col2.metric("Valor del Inventario", f"${total_valor:,.0f}")
            if "Ganancia" in df.columns:
                col3.metric("Comisiones Proyectadas", f"${df['Ganancia'].sum():,.0f}")
            
            st.bar_chart(df, x="Titulo", y="Precio Final")
        else:
            st.warning("No hay suficientes datos para generar estadísticas.")

    elif menu == "⚙️ Configuración":
        st.header("Configuración")
        st.write("Conexión a Google Sheets:")
        sheet = conectar_google_sheets()
        if sheet:
            st.success("✅ Conectado exitosamente a: Base_Datos_InmoGestion")
        else:
            st.error("❌ No se pudo conectar. Revisa la configuración de Secrets.")