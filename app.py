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

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="InmoGestión Pro", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    /* BARRA LATERAL */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1A2980 0%, #26D0CE 100%); }
    [data-testid="stSidebar"] * { color: white !important; }
    
    /* BOTONES */
    .stButton>button {
        background: linear-gradient(45deg, #FFD700, #FDB931);
        color: #2c3e50 !important;
        border: none;
        font-weight: bold;
        text-transform: uppercase;
    }
    
    /* METRICAS */
    div[data-testid="stMetricValue"] { color: #2980B9 !important; }
    
    /* INPUTS */
    .stTextInput>div>div>input { border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN A GOOGLE SHEETS (NUBE) ---
def conectar_google_sheets():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
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
    remitente = st.secrets.get("correo_emisor")
    clave_app = st.secrets.get("clave_emisor")
    
    if not remitente or not clave_app: return False, "Faltan credenciales en Secrets"

    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = "🔐 Recuperación InmoGestión"
    msg.attach(MIMEText(f"Tu nueva clave temporal es: {nueva_clave}", 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, clave_app)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
        return True, "Enviado"
    except Exception as e: return False, str(e)

# --- 4. GESTIÓN DE DATOS ---
def cargar_tabla(pestana):
    sh = conectar_google_sheets()
    if sh:
        try: return pd.DataFrame(sh.worksheet(pestana).get_all_records())
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

# --- 5. LOGICA DE SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = ""
if 'user_name' not in st.session_state: st.session_state.user_name = ""

# =======================================================
#  LOGIN
# =======================================================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #1A2980;'>🏢 InmoGestión Pro</h1>", unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["🔑 INGRESAR", "📝 REGISTRO", "❓ RECUPERAR"])
        
        with tab1:
            with st.form("login"):
                u = st.text_input("Usuario")
                p = st.text_input("Clave", type="password")
                if st.form_submit_button("ENTRAR", use_container_width=True):
                    df = cargar_tabla("Usuarios")
                    if not df.empty and u in df["Usuario"].values:
                        user = df[df["Usuario"] == u].iloc[0]
                        if check_hashes(p, str(user["Password"])):
                            st.session_state.logged_in = True
                            st.session_state.user_name = user["Nombre"]
                            st.session_state.user_role = user["Rol"]
                            st.rerun()
                        else: st.error("Clave incorrecta")
                    else: st.error("Usuario no encontrado")

        with tab2:
            with st.form("reg"):
                nu = st.text_input("Usuario")
                np = st.text_input("Clave", type="password")
                nn = st.text_input("Nombre")
                ne = st.text_input("Email")
                nr = st.selectbox("Rol", ["Agente", "Administrador"])
                if st.form_submit_button("CREAR"):
                    if guardar_fila("Usuarios", [nu, make_hashes(np), nn, nr, ne]): st.success("Creado")
                    else: st.error("Error conexión")

        with tab3:
            ru = st.text_input("Tu Usuario")
            if st.button("Recuperar Clave"):
                sh = conectar_google_sheets()
                if sh:
                    ws = sh.worksheet("Usuarios")
                    df = pd.DataFrame(ws.get_all_records())
                    if not df.empty and ru in df["Usuario"].values:
                        fila = df[df["Usuario"] == ru].iloc[0]
                        nueva = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
                        cell = ws.find(ru)
                        ws.update_cell(cell.row, 2, make_hashes(nueva))
                        ok, msg = enviar_correo(fila["Email"], nueva)
                        if ok: st.success("Revisa tu correo")
                        else: st.error(msg)

# =======================================================
#  SISTEMA COMPLETO (RECUPERADO)
# =======================================================
else:
    with st.sidebar:
        st.title("InmoGestión Pro")
        st.caption(f"Hola, {st.session_state.user_name}")
        menu = st.radio("Menú", ["📂 Inventario", "➕ Nuevo Registro", "📊 Estadísticas"])
        if st.button("Salir"):
            st.session_state.logged_in = False
            st.rerun()

    # --- PESTAÑA: NUEVO REGISTRO (FORMULARIO COMPLETO) ---
    if menu == "➕ Nuevo Registro":
        st.header("📝 Registrar Propiedad Completa")
        
        with st.form("prop_form"):
            # 1. FINANZAS
            st.subheader("💰 Finanzas")
            c1, c2, c3 = st.columns(3)
            with c1: moneda = st.selectbox("Moneda", ["COP", "USD", "EUR"])
            with c2: tasa = st.number_input("Tasa Cambio", value=1.0)
            
            c_p1, c_p2, c_p3 = st.columns(3)
            p_neto = c_p1.number_input("Precio Neto Propietario", min_value=0.0, step=1000000.0)
            modo = c_p2.radio("Ganancia", ["Porcentaje (%)", "Valor Fijo"])
            
            ganancia = 0.0
            p_final = p_neto
            
            if modo == "Porcentaje (%)":
                pct = c_p3.number_input("% Comisión", value=3.0)
                ganancia = p_neto * (pct/100)
            else:
                ganancia = c_p3.number_input("Valor Comisión", min_value=0.0)
            
            p_final = p_neto + ganancia
            st.metric("💵 PRECIO FINAL VENTA", f"${p_final:,.0f}")
            st.caption(f"Tu ganancia proyectada: ${ganancia:,.0f}")

            st.markdown("---")

            # 2. DATOS GENERALES
            st.subheader("🏡 Ficha Técnica")
            titulo = st.text_input("Título del Anuncio (Ej: Apto Lujo Cabecera)")
            c_d1, c_d2, c_d3 = st.columns(3)
            tipo = c_d1.selectbox("Tipo", ["Apartamento", "Casa", "Lote", "Finca", "Local"])
            ciudad = c_d2.text_input("Ciudad", "Bucaramanga")
            barrio = c_d3.text_input("Barrio")
            
            c_e1, c_e2, c_e3 = st.columns(3)
            estrato = c_e1.selectbox("Estrato", ["1","2","3","4","5","6","Rural"])
            area = c_e2.number_input("Área (m²)", min_value=0.0)
            habs = c_e3.number_input("Habitaciones", min_value=0)
            
            amenidades = st.multiselect("Amenidades", ["Piscina", "Vigilancia", "Ascensor", "Gym", "BBQ", "Parqueadero"])
            
            st.markdown("---")
            
            # 3. PROPIETARIO
            st.subheader("👤 Propietario")
            c_pr1, c_pr2, c_pr3 = st.columns(3)
            prop_nom = c_pr1.text_input("Nombre Completo")
            prop_tel = c_pr2.text_input("Teléfono")
            estado = c_pr3.selectbox("Estado", ["Disponible", "Vendida", "Rentada"])
            
            # 4. EXTRAS
            desc = st.text_area("Descripción detallada")
            
            # GUARDAR
            if st.form_submit_button("💾 GUARDAR EN LA NUBE"):
                if titulo and p_final > 0:
                    datos = [
                        str(date.today()), # Fecha
                        titulo,            # Titulo
                        tipo,              # Tipo
                        p_final,           # Precio Venta
                        ganancia,          # Ganancia
                        ciudad,            # Ciudad
                        barrio,            # Barrio
                        prop_nom,          # Propietario
                        prop_tel,          # Telefono
                        estado,            # Estado
                        ", ".join(amenidades), # Amenidades
                        desc               # Notas
                    ]
                    if guardar_fila("Propiedades", datos):
                        st.success("✅ ¡Propiedad Guardada Exitosamente!")
                    else:
                        st.error("❌ Error conectando a Google Sheets.")
                else:
                    st.warning("⚠️ Faltan datos obligatorios (Título o Precio).")

    # --- PESTAÑA: INVENTARIO ---
    elif menu == "📂 Inventario":
        st.header("📂 Tu Cartera de Propiedades")
        df = cargar_tabla("Propiedades")
        if not df.empty:
            busqueda = st.text_input("🔍 Buscar inmueble...")
            if busqueda:
                df = df[df.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)]
            
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay propiedades registradas aún.")

    # --- PESTAÑA: ESTADÍSTICAS ---
    elif menu == "📊 Estadísticas":
        st.header("📊 Tablero de Control")
        df = cargar_tabla("Propiedades")
        if not df.empty:
            # Asegurar que las columnas sean numéricas para sumar
            try:
                # Asumiendo que Precio Venta es la columna 3 (índice 3 en Sheet, nombre variable)
                # Google Sheets devuelve strings a veces, limpiamos:
                # Esto es una simplificación visual
                total_props = len(df)
                st.metric("Total Propiedades", total_props)
                # Aquí podrías agregar más métricas si los datos numéricos están limpios
            except:
                st.warning("Datos insuficientes para gráficas.")
        else:
            st.info("Registra propiedades para ver estadísticas.")