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
from datetime import date, datetime, time

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="InmoGestión Pro", page_icon="🏢", layout="wide")

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
def conectar_google_sheets():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # Busca el archivo secrets.json
        creds = ServiceAccountCredentials.from_json_keyfile_name('secrets.json', scope)
        client = gspread.authorize(creds)
        # Abre la hoja de cálculo
        sheet = client.open("Base_Datos_InmoGestion")
        return sheet
    except Exception as e:
        st.error(f"❌ Error conectando a Google Sheets: {e}")
        return None

# --- 3. FUNCIONES DE CORREO (RECUPERACIÓN) ---
def obtener_credenciales_correo():
    """Lee el correo y la clave del archivo secrets.json"""
    try:
        with open('secrets.json') as f:
            data = json.load(f)
            return data.get('correo_emisor'), data.get('clave_emisor')
    except: return None, None

def enviar_correo_recuperacion(destinatario, nueva_clave):
    remitente, clave_app = obtener_credenciales_correo()
    
    if not remitente or not clave_app:
        return False, "⚠️ Falta configurar correo_emisor y clave_emisor en secrets.json"

    asunto = "🔐 Recuperación de Clave - InmoGestión Pro"
    cuerpo = f"""
    Hola,
    
    Se ha solicitado restablecer tu contraseña en InmoGestión Pro.
    
    🔑 Tu nueva contraseña temporal es: {nueva_clave}
    
    Por favor, ingresa con esta clave y cámbiala si lo deseas.
    
    Saludos,
    Tu Sistema Inmobiliario 🤖
    """

    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = asunto
    msg.attach(MIMEText(cuerpo, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, clave_app)
        text = msg.as_string()
        server.sendmail(remitente, destinatario, text)
        server.quit()
        return True, "Correo enviado"
    except Exception as e:
        return False, str(e)

# --- 4. FUNCIONES DE BASE DE DATOS ---

def cargar_datos(pestana):
    """Descarga los datos de una pestaña específica de Google Sheets"""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            worksheet = sheet.worksheet(pestana)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except gspread.WorksheetNotFound:
            st.warning(f"⚠️ La pestaña '{pestana}' no existe en la hoja de cálculo.")
            return pd.DataFrame()
    return pd.DataFrame()

def guardar_registro_sheet(pestana, datos_lista):
    """Guarda una fila nueva en Google Sheets"""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            worksheet = sheet.worksheet(pestana)
            worksheet.append_row(datos_lista)
            return True
        except Exception as e:
            st.error(f"Error guardando: {e}")
            return False
    return False

def actualizar_clave_usuario(usuario, nueva_clave_texto):
    """Busca al usuario y actualiza su contraseña en Sheets"""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            ws = sheet.worksheet("Usuarios")
            cell = ws.find(usuario)
            if cell:
                # La columna de Password es la 2 (B)
                nueva_hash = make_hashes(nueva_clave_texto)
                ws.update_cell(cell.row, 2, nueva_hash)
                return True
        except: return False
    return False

# --- 5. FUNCIONES DE SEGURIDAD Y UTILIDAD ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

def crear_usuario(username, password, nombre, rol, email):
    df = cargar_datos("Usuarios")
    if not df.empty and username in df["Usuario"].values:
        return False
    # Guardamos: Usuario, Password, Nombre, Rol, Email
    datos = [username, make_hashes(password), nombre, rol, email]
    return guardar_registro_sheet("Usuarios", datos)

def verificar_login(username, password):
    df = cargar_datos("Usuarios")
    if not df.empty:
        if username in df["Usuario"].values:
            user_data = df[df["Usuario"] == username].iloc[0]
            if check_hashes(password, str(user_data["Password"])):
                return user_data["Nombre"], user_data["Rol"]
    return None, None

# --- FUNCIONES DE ARCHIVOS Y AGENDA ---
def guardar_fotos_local(fotos, id_propiedad):
    carpeta = "fotos_guardadas"
    if not os.path.exists(carpeta): os.makedirs(carpeta)
    rutas = []
    for foto in fotos:
        nombre = f"{id_propiedad}_{foto.name}"
        ruta = os.path.join(carpeta, nombre)
        with open(ruta, "wb") as f: f.write(foto.getbuffer())
        rutas.append(ruta)
    return ",".join(rutas)

def guardar_documentos_local(docs, id_propiedad):
    carpeta = "documentos_legales"
    if not os.path.exists(carpeta): os.makedirs(carpeta)
    rutas = []
    for doc in docs:
        nombre_limpio = doc.name.replace(" ", "_")
        nombre = f"{id_propiedad}_DOC_{nombre_limpio}"
        ruta = os.path.join(carpeta, nombre)
        with open(ruta, "wb") as f: f.write(doc.getbuffer())
        rutas.append(ruta)
    return ",".join(rutas)

def agendar_cita(id_propiedad, titulo_prop, fecha, hora, cliente, notas, usuario_responsable):
    datos = [str(id_propiedad), titulo_prop, str(fecha), str(hora), cliente, notas, usuario_responsable, "Pendiente"]
    return guardar_registro_sheet("Agenda", datos)

# --- MOTOR DE MARKETING ---
def generar_marketing(d):
    fire = ["🔥", "🚀", "💎", "🌟", "🏠"]
    check = ["✅", "✔", "🔸", "🔹"]
    
    titulo = str(d.get('Título', 'Inmueble Increíble'))
    ciudad = str(d.get('Ciudad', 'La Ciudad'))
    barrio = str(d.get('Barrio', ''))
    try: precio = float(str(d.get('Precio Final', 0)).replace(',', ''))
    except: precio = 0
    
    txt_insta = f"""{random.choice(fire)} ¡OPORTUNIDAD ÚNICA EN {ciudad.upper()}! {random.choice(fire)}

🏠 **{titulo}**
📍 Ubicación: {barrio}, {ciudad}

✨ **Lo que te encantará:**
{random.choice(check)} Área: {d.get('Área', 0)}m²
{random.choice(check)} Habitaciones: {d.get('Habitaciones', 0)} | Baños: {d.get('Baños', 0)}
{random.choice(check)} Piso: {d.get('Piso', 'N/A')}
{random.choice(check)} Estrato: {d.get('Estrato', 'N/A')}

💎 **Amenidades Top:**
{d.get('Amenidades', 'Todo lo que necesitas')}

💰 **Valor de Inversión:** {d.get('Moneda', '$')} {precio:,.0f}

📲 ¡Agenda tu visita HOY mismo! Link en la bio.
#{ciudad.replace(' ','')} #BienesRaices #{d.get('Tipo','Propiedad')} #TuHogarIdeal
"""
    txt_ws = f"""Hola! 👋 Te comparto esta propiedad nueva:
*{titulo}* en *{barrio}*
📐 {d.get('Área', 0)}m² | 🛏️ {d.get('Habitaciones', 0)} Habs
💰 Precio: {d.get('Moneda', '$')} {precio:,.0f}

¿Te interesa ver más? Avísame! 🚀"""
    return txt_insta, txt_ws

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1A2980 0%, #26D0CE 100%); }
    [data-testid="stSidebar"] .block-container h1 {
        color: #FFD700 !important; font-family: 'Arial Black', sans-serif !important;
        font-size: 3.5rem !important; white-space: nowrap !important;
        overflow: visible !important; margin-left: -10px !important; margin-bottom: 30px !important;
        text-shadow: 2px 2px 5px rgba(0,0,0,0.5); padding-top: 10px;
    }
    @media (max-width: 768px) {
        [data-testid="stSidebar"] .block-container h1 { font-size: 2.5rem !important; white-space: normal !important; }
    }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div.stMarkdown p {
        color: #dddfdf !important; font-weight: 500 !important; font-size: 16px !important;
    }
    .stRadio label { font-size: 18px !important; font-weight: bold !important; color: #dddfdf !important; }
    div[role="radiogroup"] > label > div:first-child { border-color: #FFD700 !important; }
    div[role="radiogroup"] > label > div:first-child > div { background-color: #FFD700 !important; }
    [data-testid="stSidebar"] hr { border-color: #dddfdf !important; opacity: 0.3; }
    .stApp { background-color: #F8F9FA; color: #2c3e50; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, 
    .stDateInput>div>div>input, .stTextArea>div>div>textarea, .stTimeInput>div>div>input {
        background-color: white !important; color: #1D1C1D !important; border: 1px solid #BDC3C7; border-radius: 6px; min-height: 45px;
    }
    div.stContainer { border: 1px solid #E0E0E0; border-radius: 8px; padding: 22px; background-color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.03); }
    .stButton>button { background: linear-gradient(45deg, #FFD700, #FDB931); color: #2c3e50 !important; border: none; border-radius: 6px; font-weight: 800; text-transform: uppercase; min-height: 50px; }
    .login-box { padding: 30px; background: white; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); text-align: center; }
    div[data-testid="stMetricValue"] { color: #2980B9 !important; font-weight: bold !important; font-size: 1.2rem !important; }
    div[data-testid="stMetricLabel"] { color: #546E7A !important; font-size: 1rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 6. SESIÓN Y CONTROL ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'user_role' not in st.session_state: st.session_state.user_role = ""

# =======================================================
#  SISTEMA DE LOGIN / REGISTRO / RECUPERACIÓN
# =======================================================
if not st.session_state.logged_in:
    col_izq, col_centro, col_der = st.columns([1, 1.5, 1])
    with col_centro:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""<div class="login-box"><h1 style='color: #2c3e50 !important; margin-bottom: 0;'>🏢 InmoGestión Pro</h1><p style='color: #7f8c8d !important;'>Cloud Edition v9.0</p></div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        tab_ingreso, tab_registro, tab_recuperar = st.tabs(["🔑 LOGIN", "📝 REGISTRO", "❓ RECUPERAR CLAVE"])
        
        with tab_ingreso:
            with st.form("form_login"):
                usuario = st.text_input("Usuario")
                contra = st.text_input("Contraseña", type="password")
                if st.form_submit_button("INGRESAR", use_container_width=True):
                    nombre_ok, rol_ok = verificar_login(usuario, contra)
                    if nombre_ok:
                        st.session_state.logged_in = True
                        st.session_state.user_name = nombre_ok
                        st.session_state.user_role = rol_ok
                        st.rerun()
                    else: st.error("❌ Datos incorrectos (Verifica tu usuario en Sheets)")

        with tab_registro:
            with st.form("form_registro"):
                n_user = st.text_input("Usuario Nuevo")
                n_pass = st.text_input("Contraseña", type="password")
                n_name = st.text_input("Nombre Completo")
                n_email = st.text_input("Email (Para recuperación)")
                n_rol = st.selectbox("Rol", ["Agente Inmobiliario", "Administrador"])
                n_key = st.text_input("Clave Maestra (Solo Admin)", type="password")
                if st.form_submit_button("CREAR CUENTA", use_container_width=True):
                    if n_rol == "Administrador" and n_key != "PRO2026": st.error("⛔ Clave Maestra Incorrecta")
                    elif n_user and n_pass and n_name and n_email:
                        if crear_usuario(n_user, n_pass, n_name, n_rol, n_email): st.success("✅ Creado. ¡Logueate!")
                        else: st.error("⚠️ Error (Usuario existe o falla conexión)")
                    else: st.warning("Faltan datos")

        with tab_recuperar:
            st.info("Ingresa tu usuario. Te enviaremos una clave temporal a tu correo.")
            with st.form("form_recuperar"):
                rec_user = st.text_input("Tu Usuario")
                if st.form_submit_button("ENVIAR NUEVA CLAVE", use_container_width=True):
                    df_u = cargar_datos("Usuarios")
                    if not df_u.empty and rec_user in df_u["Usuario"].values:
                        user_row = df_u[df_u["Usuario"] == rec_user].iloc[0]
                        user_email = str(user_row.get("Email", ""))
                        
                        if "@" in user_email:
                            nueva_clave = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
                            if actualizar_clave_usuario(rec_user, nueva_clave):
                                exito, msg = enviar_correo_recuperacion(user_email, nueva_clave)
                                if exito: st.success(f"✅ ¡Listo! Revisa tu correo {user_email}.")
                                else: st.error(f"❌ Error enviando correo: {msg}")
                            else: st.error("❌ Error actualizando base de datos.")
                        else: st.warning("Este usuario no tiene un email válido registrado.")
                    else: st.error("Usuario no encontrado.")

# =======================================================
#  SISTEMA PRINCIPAL (DENTRO)
# =======================================================
else:
    with st.sidebar:
        st.title("InmoGestión Pro")
        st.markdown("---")
        menu_items = ["➕ Nuevo Registro", "📂 Inventario & CRM", "📊 Estadísticas"]
        if st.session_state.user_role == "Administrador": menu_items.append("⚙️ Administración")
        menu_sel = st.radio("MENÚ PRINCIPAL", menu_items, label_visibility="visible")
        st.markdown("---")
        with st.container():
            st.markdown(f"**Usuario:** {st.session_state.user_name}")
            rol_color = ":orange[Admin]" if st.session_state.user_role == "Administrador" else ":blue[Agente]"
            st.markdown(f"**Rol:** {rol_color}")
            if st.button("Cerrar Sesión"):
                st.session_state.logged_in = False
                st.rerun()

    # --- PESTAÑA 1: NUEVO REGISTRO ---
    if menu_sel == "➕ Nuevo Registro":
        st.header("📝 Registrar Propiedad")
        with st.container():
            st.subheader("💰 Finanzas del Negocio")
            col_mon, col_tas = st.columns(2)
            with col_mon:
                moneda = st.selectbox("Moneda", ["COP - Peso Colombiano", "USD - Dólar", "EUR - Euros"])
                simbolo = moneda.split(" - ")[0]
            with col_tas: tasa = st.number_input("Tasa de Cambio (Ref)", value=1.0)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**1. Datos Propietario**")
                fecha = st.date_input("Fecha Captación", date.today())
                estado = st.selectbox("Estado Actual", ["Disponible", "Vendida", "Rentada"])
                prop_nom = st.text_input("Nombre Propietario")
                c_ced, c_tel = st.columns(2)
                prop_ced = c_ced.text_input("Cédula/NIT")
                prop_tel = c_tel.text_input("Teléfono / Contacto")
                prop_mail = st.text_input("Correo Electrónico")
            with c2:
                st.markdown("**2. Precios Base**")
                p_neto = st.number_input(f"Neto Propietario ({simbolo})", min_value=0.0, format="%.2f", step=1000000.0)
                p_min = st.number_input(f"Precio Mínimo ({simbolo})", min_value=0.0)
            with c3:
                st.markdown("**3. Rentabilidad**")
                modo_ganancia = st.radio("Modalidad", ["Porcentaje (%)", "Sobreprecio"])
                ganancia = 0; p_final = 0
                if modo_ganancia == "Porcentaje (%)":
                    pct = st.number_input("Comisión (%)", value=3.0)
                    ganancia = p_neto * (pct/100); p_final = p_neto
                else:
                    sobre = st.number_input(f"Valor Agregado ({simbolo})", min_value=0.0)
                    ganancia = sobre; p_final = p_neto + sobre
                st.metric("💵 Tu Ganancia", f"{simbolo} {ganancia:,.2f}")
                st.metric("🏷️ Precio Venta", f"{simbolo} {p_final:,.2f}")

        st.markdown("<br>", unsafe_allow_html=True)
        with st.container():
            st.subheader("🏡 Ficha Técnica")
            tit_anuncio = st.text_input("Título del Anuncio")
            tipo_inm = st.selectbox("Tipo Inmueble", ["Apartamento", "Casa", "Lote", "Local", "Finca", "Bodega"])
            st.markdown("---")
            col_izq, col_der = st.columns(2)
            with col_izq:
                st.markdown("📍 **Ubicación**")
                c_ciu, c_bar = st.columns(2)
                ciudad = c_ciu.text_input("Ciudad", "Piedecuesta")
                barrio = c_bar.text_input("Barrio")
                c_dep, c_pai = st.columns(2)
                depto = c_dep.text_input("Departamento", "Santander")
                pais = c_pai.text_input("País", "Colombia")
                st.markdown("📋 **Administrativo**")
                c_est, c_parq, c_adm = st.columns(3) 
                estrato = c_est.selectbox("Estrato", ["1", "2", "3", "4", "5", "6", "Rural", "Comercial"])
                parqueadero = c_parq.selectbox("Parqueadero", ["Privado", "Comunal", "No tiene"])
                admin_val = c_adm.number_input(f"Administración ({simbolo})", min_value=0.0)
            with col_der:
                st.markdown("📐 **Dimensiones**")
                c_hab, c_ban = st.columns(2)
                habs = c_hab.number_input("Habs", 0); bans = c_ban.number_input("Baños", 0)
                c_are, c_pis = st.columns(2)
                area = c_are.number_input("Área (m²)", 0.0); piso = c_pis.text_input("Piso")
                st.markdown("🏗️ **Estado**")
                c_ant, c_fis = st.columns(2)
                antig = c_ant.selectbox("Antigüedad", ["A estrenar", "1-5 años", "5-10 años", "10-20 años", "+20 años", "En Obra"])
                fisico = c_fis.selectbox("Estado", ["Excelente", "Bueno", "Regular", "Para Remodelar"])

        with st.expander("🏗️ Sobre Planos"):
            es_planos = st.checkbox("Activar", value=False)
            ini = 0.0; cuotas = 0; alarma = None
            if es_planos:
                cp1, cp2, cp3 = st.columns(3)
                ini = cp1.number_input("Inicial", 0.0); cuotas = cp2.number_input("Cuotas", 0); alarma = cp3.date_input("Cobro")

        st.markdown("<br>", unsafe_allow_html=True)
        with st.container():
            col_docs, col_checklist = st.columns([1, 1])
            with col_docs:
                st.markdown("**📂 Documentos Legales**")
                docs_subidos = st.file_uploader("Subir PDFs", accept_multiple_files=True, type=['pdf', 'png', 'jpg'], key="u_docs")
            with col_checklist:
                st.info("ℹ️ Checklist:"); c1, c2 = st.columns(2)
                with c1: st.checkbox("Tradición"); st.checkbox("Escritura")
                with c2: st.checkbox("Paz y Salvo"); st.checkbox("Cédula")

        st.markdown("<br>", unsafe_allow_html=True)
        with st.container():
            cf, ca = st.columns([1, 1])
            with cf: st.markdown("📸 **Fotos**"); fotos = st.file_uploader("Subir Fotos", accept_multiple_files=True, type=['png', 'jpg'], key="u_fotos")
            with ca: st.markdown("💎 **Amenidades**"); amen = st.multiselect("Seleccionar:", ["Vigilancia", "Ascensor", "Piscina", "BBQ", "Parque", "Gym"]); desc = st.text_area("Notas")

        if st.button("💾 GUARDAR EN LA NUBE", type="primary"):
            if p_final == 0: st.error("Precio en 0")
            else:
                id_u = str(pd.Timestamp.now().timestamp())
                r_fotos = guardar_fotos_local(fotos, id_u) if fotos else ""
                r_docs = guardar_documentos_local(docs_subidos, id_u) if docs_subidos else ""
                am_str = ", ".join(amen) if amen else "Ninguna"
                datos_nuevos = [
                    id_u, str(fecha), estado, prop_nom, prop_ced, prop_tel, prop_mail,
                    p_final, ganancia, tit_anuncio, ciudad, barrio, depto, pais,
                    estrato, parqueadero, admin_val, tipo_inm, habs, bans, area, piso, antig, fisico,
                    "Sí" if es_planos else "No", ini, cuotas, str(alarma) if alarma else "", am_str, desc,
                    r_fotos, r_docs
                ]
                if guardar_registro_sheet("Propiedades", datos_nuevos): st.success("✅ ¡Propiedad guardada en Google Sheets!")
                else: st.error("❌ Error al guardar en la nube.")

    # --- PESTAÑA 2: CRM & AGENDA ---
    elif menu_sel == "📂 Inventario & CRM":
        st.header("📂 Base de Datos (Nube)")
        df = cargar_datos("Propiedades")
        c_alert, c_agenda = st.columns(2)
        with c_agenda:
            st.markdown("##### 📅 Agenda (Nube)")
            df_citas = cargar_datos("Agenda")
            if not df_citas.empty: st.dataframe(df_citas, hide_index=True, height=150)
            else: st.info("Agenda vacía.")
        st.divider()

        if not df.empty:
            cols_busqueda = [c for c in df.columns if c in ["Título", "Propietario", "Ciudad"]]
            q = st.text_input("🔍 Buscar...")
            if q:
                mask = df.apply(lambda row: row.astype(str).str.contains(q, case=False).any(), axis=1)
                df = df[mask]

            cols_mostrar = [c for c in ["Fecha", "Título", "Precio Final", "Propietario"] if c in df.columns]
            st.dataframe(df[cols_mostrar], hide_index=True, use_container_width=True)
            
            if "Título" in df.columns and "Propietario" in df.columns:
                opc = df["Título"].astype(str) + " | " + df["Propietario"].astype(str)
                sel = st.selectbox("Ver Ficha:", opc)
                if sel:
                    idx = df[df["Título"].astype(str) + " | " + df["Propietario"].astype(str) == sel].index[0]
                    d = df.iloc[idx]
                    with st.container():
                        st.markdown(f"### 🏠 {d['Título']}")
                        t1, t2, t3, t4 = st.tabs(["📋 Info", "📂 Docs", "📅 Cita", "📢 Marketing"])
                        with t1:
                            c1, c2 = st.columns(2)
                            with c1:
                                st.write(f"📍 {d.get('Ciudad','')} - {d.get('Barrio','')}")
                                st.write(f"👤 {d.get('Propietario','')} (Tel: {d.get('Teléfono','')})")
                            with c2:
                                try: p_val = float(str(d.get('Precio Final', 0)).replace(',',''))
                                except: p_val = 0
                                st.markdown(f"💰 **${p_val:,.0f}**")
                            if pd.notna(d.get("Rutas Fotos")) and str(d.get("Rutas Fotos")) != "":
                                st.markdown("📸 **Fotos (En PC Servidor)**")
                        with t3:
                            with st.form("cita"):
                                f = st.date_input("Fecha"); h = st.time_input("Hora"); c = st.text_input("Cliente"); n = st.text_area("Nota")
                                if st.form_submit_button("Agendar"):
                                    agendar_cita(d.get('ID','0'), d.get('Título',''), f, h, c, n, st.session_state.user_name)
                                    st.success("Agendado en Nube")
                        with t4:
                            st.write("Generando textos...")
                            t_ig, t_wa = generar_marketing(d)
                            c_ig, c_wa = st.columns(2)
                            with c_ig: st.text_area("Instagram", t_ig, height=250)
                            with c_wa: st.text_area("WhatsApp", t_wa, height=250)
        else: st.info("Base de datos vacía.")

    elif menu_sel == "📊 Estadísticas":
        st.header("📊 Tablero de Métricas")
        st.info("Próximamente")

    elif menu_sel == "⚙️ Administración":
        st.header("⚙️ Usuarios en la Nube")
        df_u = cargar_datos("Usuarios")
        if not df_u.empty: st.dataframe(df_u)
        else: st.warning("No hay usuarios.")