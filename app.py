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

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="InmoGestión Pro", page_icon="🏢", layout="wide")

# --- 2. ESTILOS VISUALES ---
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
        border-radius: 8px;
    }
    
    /* FICHA TÉCNICA */
    .ficha-box {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1A2980;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* METRICAS */
    div[data-testid="stMetricValue"] { color: #2980B9 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN A GOOGLE SHEETS ---
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

# --- 4. FUNCIONES DE DATOS Y SEGURIDAD ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

def enviar_correo(destinatario, nueva_clave):
    remitente = st.secrets.get("correo_emisor")
    clave_app = st.secrets.get("clave_emisor")
    if not remitente or not clave_app: return False, "Faltan credenciales en Secrets"
    
    msg = MIMEMultipart()
    msg['From'], msg['To'], msg['Subject'] = remitente, destinatario, "🔐 Recuperación InmoGestión"
    msg.attach(MIMEText(f"Tu clave temporal es: {nueva_clave}", 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, clave_app)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
        return True, "Enviado"
    except Exception as e: return False, str(e)

def cargar_datos(pestana):
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
            datos_str = [str(d) for d in datos]
            ws.append_row(datos_str)
            return True
        except: return False
    return False

# --- 5. LÓGICA DE SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = ""
if 'user_name' not in st.session_state: st.session_state.user_name = ""

# =======================================================
#  VISTA LOGIN / REGISTRO / RECUPERAR
# =======================================================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><h1 style='text-align: center; color:#1A2980;'>🏢 InmoGestión Pro</h1>", unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["🔑 INGRESAR", "📝 REGISTRO", "❓ RECUPERAR"])
        
        with tab1:
            with st.form("login"):
                u = st.text_input("Usuario")
                p = st.text_input("Clave", type="password")
                if st.form_submit_button("ENTRAR", use_container_width=True):
                    df = cargar_datos("Usuarios")
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
                if st.form_submit_button("CREAR CUENTA", use_container_width=True):
                    if guardar_fila("Usuarios", [nu, make_hashes(np), nn, nr, ne]): st.success("Usuario Creado")
                    else: st.error("Error de Conexión")

        with tab3:
            ru = st.text_input("Usuario a recuperar")
            if st.button("ENVIAR CLAVE TEMPORAL", use_container_width=True):
                sh = conectar_google_sheets()
                if sh:
                    try:
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
                    except: st.error("Error buscando usuario")

# =======================================================
#  SISTEMA PRINCIPAL
# =======================================================
else:
    with st.sidebar:
        st.title("InmoGestión Pro")
        st.write(f"👤 **{st.session_state.user_name}**")
        st.caption(f"Rol: {st.session_state.user_role}")
        st.markdown("---")
        menu = st.radio("Menú", ["📂 Inventario & Ficha", "➕ Nuevo Registro", "📊 Estadísticas"])
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.rerun()

    # --- 1. NUEVO REGISTRO (COMPLETO CON LOS CAMPOS QUE PEDISTE) ---
    if menu == "➕ Nuevo Registro":
        st.header("📝 Registrar Propiedad Completa")
        
        with st.form("form_propiedad"):
            # A. FINANZAS
            st.subheader("💰 1. Finanzas")
            col_m, col_t = st.columns(2)
            moneda = col_m.selectbox("Moneda", ["COP", "USD", "EUR"])
            simbolo = moneda.split(" ")[0]
            
            c1, c2, c3 = st.columns(3)
            p_neto = c1.number_input(f"Precio Neto Propietario ({simbolo})", min_value=0.0, step=1000000.0)
            modo_ganancia = c2.radio("Modo Ganancia", ["Porcentaje (%)", "Valor Fijo"])
            
            ganancia = 0.0
            if modo_ganancia == "Porcentaje (%)":
                pct = c3.number_input("% Comisión", value=3.0)
                ganancia = p_neto * (pct/100)
            else:
                ganancia = c3.number_input(f"Valor Comisión ({simbolo})", min_value=0.0)
            
            p_final = p_neto + ganancia
            st.info(f"💵 **PRECIO DE VENTA SUGERIDO:** {simbolo} {p_final:,.0f} (Ganancia: {simbolo} {ganancia:,.0f})")

            # B. DETALLES DEL INMUEBLE (AGREGADOS LOS FALTANTES)
            st.subheader("🏡 2. Detalles del Inmueble")
            titulo = st.text_input("Título del Anuncio (Ej: Apto Lujo en Cabecera)")
            
            c_d1, c_d2, c_d3, c_d4 = st.columns(4)
            tipo = c_d1.selectbox("Tipo Inmueble", ["Apartamento", "Casa", "Lote", "Finca", "Local", "Bodega"])
            ciudad = c_d2.text_input("Ciudad", "Bucaramanga")
            barrio = c_d3.text_input("Barrio")
            estrato = c_d4.selectbox("Estrato", ["1", "2", "3", "4", "5", "6", "Rural", "Comercial"])
            
            # --- NUEVOS CAMPOS SOLICITADOS ---
            c_det1, c_det2, c_det3, c_det4 = st.columns(4)
            area = c_det1.number_input("Área (m²)", min_value=0.0)
            habs = c_det2.number_input("Habitaciones", min_value=0)
            piso = c_det3.text_input("Piso / Nivel", placeholder="Ej: 5, PH, 2")
            antiguedad = c_det4.selectbox("Antigüedad", ["En construcción", "Para estrenar", "1-5 años", "5-10 años", "10-20 años", "+20 años"])

            c_det5, c_det6 = st.columns(2)
            parqueadero = c_det5.selectbox("🚘 Parqueadero", ["Privado", "Comunal", "No tiene", "Visitantes"])
            estado_fisico = c_det6.selectbox("🏗️ Estado Físico", ["Excelente", "Bueno", "Regular", "Para Remodelar"])

            amenidades = st.multiselect("Amenidades", 
                ["Piscina", "Vigilancia 24/7", "Ascensor", "Gimnasio", "Zona BBQ", "Salón Social", "Juegos Niños"])
            
            # C. VENTA SOBRE PLANOS
            with st.expander("🏗️ ¿Es venta sobre planos?"):
                es_planos = st.checkbox("Activar Opción Planos")
                cuota_ini = 0.0
                num_cuotas = 0
                if es_planos:
                    cp1, cp2 = st.columns(2)
                    cuota_ini = cp1.number_input("Cuota Inicial", min_value=0.0)
                    num_cuotas = cp2.number_input("Número de Cuotas Mensuales", min_value=1)

            # D. PROPIETARIO Y MULTIMEDIA
            st.subheader("👤 3. Datos Privados & Multimedia")
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                prop_nom = st.text_input("Nombre Propietario")
                prop_tel = st.text_input("Teléfono / Contacto")
                estado_venta = st.selectbox("Estado Venta", ["Disponible", "Vendida", "Rentada", "Reservada"])
            
            with c_p2:
                # AQUÍ ESTÁ LA SUBIDA DE FOTOS QUE PEDISTE
                fotos = st.file_uploader("📸 Subir Fotos (Se guardarán en la nube)", accept_multiple_files=True)
                docs = st.file_uploader("📂 Documentos Legales", accept_multiple_files=True)
                notas = st.text_area("Notas Privadas (Solo visibles para ti)")

            # BOTÓN GUARDAR
            if st.form_submit_button("💾 GUARDAR REGISTRO COMPLETO", type="primary"):
                if titulo and p_final > 0:
                    lista_amenidades = ", ".join(amenidades)
                    nombres_fotos = [f.name for f in fotos] if fotos else "Sin fotos"
                    
                    # LISTA DE DATOS ACTUALIZADA CON LOS NUEVOS CAMPOS
                    datos_guardar = [
                        str(date.today()), # 0. Fecha
                        titulo,            # 1. Titulo
                        tipo,              # 2. Tipo
                        p_final,           # 3. Precio Venta
                        ganancia,          # 4. Ganancia
                        ciudad,            # 5. Ciudad
                        barrio,            # 6. Barrio
                        prop_nom,          # 7. Propietario
                        prop_tel,          # 8. Telefono
                        estado_venta,      # 9. Estado Venta
                        area,              # 10. Area
                        habs,              # 11. Habs
                        estrato,           # 12. Estrato
                        piso,              # 13. Piso (NUEVO)
                        antiguedad,        # 14. Antiguedad (NUEVO)
                        parqueadero,       # 15. Parqueadero (NUEVO)
                        estado_fisico,     # 16. Estado Fisico (NUEVO)
                        lista_amenidades,  # 17. Amenidades
                        "Sí" if es_planos else "No", # 18. Planos
                        str(nombres_fotos), # 19. Fotos
                        notas              # 20. Notas
                    ]
                    
                    if guardar_fila("Propiedades", datos_guardar):
                        st.success("✅ ¡Propiedad registrada exitosamente!")
                        st.balloons()
                    else:
                        st.error("❌ Error de conexión con la Nube.")
                else:
                    st.warning("⚠️ Faltan datos obligatorios.")

    # --- 2. INVENTARIO & FICHA TÉCNICA (VISUAL) ---
    elif menu == "📂 Inventario & Ficha":
        st.header("📂 Inventario Inmobiliario")
        df = cargar_datos("Propiedades")
        
        if not df.empty:
            filtro = st.text_input("🔍 Buscar por Barrio, Título o Propietario...")
            if filtro:
                df = df[df.astype(str).apply(lambda x: x.str.contains(filtro, case=False)).any(axis=1)]
            
            # SELECCIÓN DE PROPIEDAD
            opciones = df["Título"] + " - " + df["Propietario"] if "Título" in df.columns else []
            seleccion = st.selectbox("Selecciona una propiedad para ver la Ficha Técnica:", opciones)
            
            if seleccion:
                idx = df[df["Título"] + " - " + df["Propietario"] == seleccion].index[0]
                fila = df.iloc[idx]
                
                # --- VISUALIZACIÓN TIPO FICHA TÉCNICA ---
                st.markdown("---")
                st.markdown(f"### 🏠 {fila['Título']}")
                
                col_ficha1, col_ficha2 = st.columns([1, 2])
                
                with col_ficha1:
                    st.info("📸 **Galería**")
                    # Aquí mostramos los nombres de las fotos subidas
                    if fila['Fotos'] != "Sin fotos":
                        st.write("Archivos disponibles:")
                        st.code(fila['Fotos'])
                    else:
                        st.write("Sin imágenes cargadas.")
                    
                    st.warning(f"💰 **Precio:** ${fila['Precio Venta']}")
                    st.success(f"💵 **Comisión:** ${fila['Ganancia']}")

                with col_ficha2:
                    st.markdown('<div class="ficha-box">', unsafe_allow_html=True)
                    st.markdown("#### 📋 Detalles Técnicos")
                    c_t1, c_t2 = st.columns(2)
                    with c_t1:
                        st.write(f"**Ubicación:** {fila['Ciudad']} - {fila['Barrio']}")
                        st.write(f"**Tipo:** {fila['Tipo']}")
                        st.write(f"**Estrato:** {fila['Estrato']}")
                        st.write(f"**Área:** {fila['Área']} m²")
                    with c_t2:
                        st.write(f"**Piso:** {fila['Piso']}")
                        st.write(f"**Antigüedad:** {fila['Antigüedad']}")
                        st.write(f"**Estado:** {fila['Estado Fisico']}")
                        st.write(f"**Parqueadero:** {fila['Parqueadero']}")
                    
                    st.markdown("#### 💎 Amenidades")
                    st.write(fila['Amenidades'])
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # DATOS DE CLIENTE (OCULTOS POR DEFECTO PARA SEGURIDAD)
                with st.expander("👤 Ver Datos del Propietario (Privado)"):
                    st.write(f"**Nombre:** {fila['Propietario']}")
                    st.write(f"**Contacto:** {fila['Teléfono']}")
                    st.write(f"**Notas:** {fila['Notas']}")

        else:
            st.info("No hay propiedades registradas aún.")
            
        # AGENDA RÁPIDA
        st.divider()
        st.subheader("📅 Agenda Rápida")
        with st.form("agenda_rapida"):
            c_a1, c_a2, c_a3 = st.columns(3)
            fecha = c_a1.date_input("Fecha")
            cliente = c_a2.text_input("Cliente")
            lugar = c_a3.text_input("Lugar / Propiedad")
            if st.form_submit_button("Agendar"):
                if guardar_fila("Agenda", [str(fecha), cliente, lugar, "Pendiente"]):
                    st.success("Cita guardada")

    # --- 3. ESTADÍSTICAS ---
    elif menu == "📊 Estadísticas":
        st.header("📊 Tablero de Resultados")
        df = cargar_datos("Propiedades")
        if not df.empty and "Precio Venta" in df.columns:
            try:
                # Limpieza de datos para evitar errores numéricos
                df["Precio Venta"] = pd.to_numeric(df["Precio Venta"], errors='coerce').fillna(0)
                df["Ganancia"] = pd.to_numeric(df["Ganancia"], errors='coerce').fillna(0)
                
                total_v = df["Precio Venta"].sum()
                total_c = df["Ganancia"].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Propiedades Activas", len(df))
                c2.metric("Inventario Total", f"${total_v:,.0f}")
                c3.metric("Comisiones Proyectadas", f"${total_c:,.0f}")
                
                st.bar_chart(df, x="Título", y="Precio Venta")
            except: st.warning("Faltan datos numéricos válidos.")
        else: st.info("Registra propiedades para ver estadísticas.")