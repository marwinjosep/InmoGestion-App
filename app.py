import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import hashlib
import random
import string
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="InmoGestión Pro", page_icon="🏢", layout="wide")

# --- ESTILOS ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1A2980 0%, #26D0CE 100%); }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton>button {
        background: linear-gradient(45deg, #FFD700, #FDB931);
        color: #2c3e50 !important;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        height: 50px;
        font-size: 18px;
    }
    .ficha-tecnica {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid #1A2980;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
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
    except: return None

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
            datos_procesados = []
            for d in datos:
                if isinstance(d, (list, dict)): datos_procesados.append(json.dumps(d))
                else: datos_procesados.append(str(d))
            ws.append_row(datos_procesados)
            return True
        except: return False
    return False

# --- 3. SEGURIDAD ---
def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h

# --- 4. SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = ""
if 'user_name' not in st.session_state: st.session_state.user_name = ""

# =======================================================
#  LOGIN
# =======================================================
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color:#1A2980;'>🏢 InmoGestión Pro</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["INGRESAR", "REGISTRO"])
        with t1:
            u = st.text_input("Usuario")
            p = st.text_input("Clave", type="password")
            if st.button("ENTRAR", use_container_width=True):
                df = cargar_datos("Usuarios")
                if not df.empty and u in df["Usuario"].values:
                    user = df[df["Usuario"] == u].iloc[0]
                    if check_hashes(p, str(user["Password"])):
                        st.session_state.logged_in = True
                        st.session_state.user_name = user["Nombre"]
                        st.session_state.user_role = user["Rol"]
                        st.rerun()
                    else: st.error("Clave incorrecta")
                else: st.error("Usuario no existe")
        with t2:
            nu = st.text_input("Nuevo Usuario")
            np = st.text_input("Nueva Clave", type="password")
            nn = st.text_input("Nombre Completo")
            nr = st.selectbox("Rol", ["Agente", "Administrador"])
            if st.button("CREAR CUENTA", use_container_width=True):
                if guardar_fila("Usuarios", [nu, make_hashes(np), nn, nr, ""]): st.success("Creado")

# =======================================================
#  APP PRINCIPAL
# =======================================================
else:
    with st.sidebar:
        st.title("InmoGestión Pro")
        st.write(f"👤 {st.session_state.user_name}")
        st.markdown("---")
        menu = st.radio("Menú", ["📂 Inventario & CRM", "➕ Nuevo Registro", "📊 Estadísticas"])
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.rerun()

    # --- NUEVO REGISTRO ---
    if menu == "➕ Nuevo Registro":
        st.header("📝 Nuevo Registro de Propiedad")
        st.info("Completa los datos. La vista se actualizará al seleccionar las opciones.")
        
        # --- SECCIÓN 1: PROPIETARIO ---
        st.subheader("1. Datos del Propietario")
        c_p1, c_p2 = st.columns(2)
        prop_nom = c_p1.text_input("Nombre y Apellido")
        prop_ced = c_p2.text_input("Cédula / NIT")
        
        c_p3, c_p4 = st.columns(2)
        prop_tel = c_p3.text_input("Teléfono Principal")
        prop_email = c_p4.text_input("Email")
        
        c_p5, c_p6 = st.columns(2)
        prop_alt = c_p5.text_input("Teléfono Alternativo")
        docs = c_p6.file_uploader("📂 Subir Documentos Legales", accept_multiple_files=True)
        
        st.markdown("---")

        # --- SECCIÓN 2: FINANCIERA ---
        st.subheader("2. Finanzas")
        col_mon, col_fin = st.columns([1, 3])
        moneda = col_mon.selectbox("Moneda", ["COP - Colombia", "USD - Dólar", "EUR - Euro", "PEN - Sol Perú", "VES - Bolívar", "CLP - Chile", "ARS - Argentina"])
        simbolo = moneda.split(" ")[0]
        
        modo_fin = st.radio("Modalidad de Negocio:", ["Porcentaje (%)", "Pase (Sobreprecio)"], horizontal=True)
        
        precio_venta_final = 0.0
        ganancia_mia = 0.0
        neto_propietario = 0.0
        
        if modo_fin == "Porcentaje (%)":
            c_f1, c_f2 = st.columns(2)
            precio_total_input = c_f1.number_input(f"Precio Total de Venta ({simbolo})", min_value=0.0, step=1000000.0)
            pct_comision = c_f2.number_input("Porcentaje Comisión (%)", value=3.0)
            
            ganancia_mia = precio_total_input * (pct_comision / 100)
            neto_propietario = precio_total_input - ganancia_mia
            precio_venta_final = precio_total_input
            
        else: # MODO PASE
            st.success("Modo Pase Activo: Ingresa lo que pide el dueño y tu precio de venta.")
            c_f1, c_f2 = st.columns(2)
            neto_propietario_input = c_f1.number_input(f"Neto Propietario (Lo que pide el dueño)", min_value=0.0, step=1000000.0)
            precio_venta_input = c_f2.number_input(f"Precio Venta (En cuánto lo ofreces)", min_value=0.0, step=1000000.0)
            
            if precio_venta_input >= neto_propietario_input:
                ganancia_mia = precio_venta_input - neto_propietario_input
            else:
                ganancia_mia = 0
            
            neto_propietario = neto_propietario_input
            precio_venta_final = precio_venta_input

        # RESULTADOS
        c_res1, c_res2 = st.columns(2)
        c_res1.metric("💰 Ganancia Mía", f"{simbolo} {ganancia_mia:,.0f}")
        c_res2.metric("👤 Para Propietario", f"{simbolo} {neto_propietario:,.0f}")
        
        st.markdown("---")

        # --- SECCIÓN 3: DETALLES ---
        st.subheader("3. Detalles del Inmueble")
        titulo = st.text_input("Título del Anuncio (Ej: Apto Lujo Cabecera)")
        
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        tipo = r1c1.selectbox("Tipo", ["Apartamento", "Casa", "Lote", "Local", "Bodega", "Finca"])
        ciudad = r1c2.text_input("Ciudad", "Bucaramanga")
        barrio = r1c3.text_input("Barrio")
        estrato = r1c4.selectbox("Estrato", ["1","2","3","4","5","6","Comercial","Rural"])
        
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        area = r2c1.number_input("Área (m²)")
        habs = r2c2.number_input("Habitaciones", min_value=0)
        piso = r2c3.text_input("Piso / Nivel")
        antig = r2c4.selectbox("Antigüedad", ["Sobre Planos", "Estrenar", "1-5 años", "5-10 años", "+10 años"])
        
        r3c1, r3c2 = st.columns(2)
        parqueadero = r3c1.selectbox("🚘 Parqueadero", ["Privado", "Comunal", "Visitantes", "No tiene"])
        estado_fisico = r3c2.selectbox("🏗️ Estado Físico", ["Excelente", "Bueno", "Regular", "Remodelar"])
        
        amenidades = st.multiselect("💎 Amenidades", ["Piscina", "Vigilancia", "Ascensor", "Gym", "BBQ", "Salón Social", "Canchas"])
        notas_obs = st.text_area("📝 Notas u Observaciones (General)")
        
        # Fotos Sección Normal
        st.caption("Fotos Generales del Inmueble:")
        fotos_gral = st.file_uploader("📸 Subir Fotos (Clic aquí)", accept_multiple_files=True, key="fotos_gral")

        st.markdown("---")

        # --- SECCIÓN 4: SOBRE PLANOS (CORREGIDA CON FOTOS) ---
        st.subheader("4. Apartamentos Sobre Planos")
        es_planos = st.checkbox("🏗️ ¿Es un proyecto Sobre Planos?")
        
        const_nom = ""; proy_nom = ""; fecha_ini = ""; fecha_fin = ""
        monto_ini = 0.0; num_cuotas = 0; fotos_planos = []
        
        if es_planos:
            st.markdown("##### 🏗️ Detalles del Proyecto")
            sp_f1_c1, sp_f1_c2, sp_f1_c3 = st.columns([2, 2, 1])
            const_nom = sp_f1_c1.text_input("Nombre Constructor")
            proy_nom = sp_f1_c2.text_input("Nombre Proyecto")
            fecha_ini = sp_f1_c3.date_input("Fecha Inicio Obra")
            
            sp_f2_c1, sp_f2_c2, sp_f2_c3 = st.columns([2, 1, 2])
            monto_ini = sp_f2_c1.number_input("Monto Inicial", min_value=0.0)
            num_cuotas = sp_f2_c2.number_input("N° de Cuotas", min_value=1)
            fecha_fin = sp_f2_c3.date_input("Fecha Posible Culminación")
            
            # --- AQUÍ ESTÁ EL CAMBIO SOLICITADO ---
            st.markdown("##### 📸 Multimedia del Proyecto")
            fotos_planos = st.file_uploader("📂 Subir Renders / Avances de Obra (Específico Planos)", accept_multiple_files=True, key="fotos_planos")
            # -------------------------------------

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- BOTÓN GUARDAR ---
        if st.button("💾 GUARDAR TODO EN LA NUBE", type="primary"):
            if titulo and precio_venta_final > 0:
                # Recopilar Fotos de ambas secciones
                lista_fotos = []
                if fotos_gral: lista_fotos.extend([f.name for f in fotos_gral])
                if es_planos and fotos_planos: lista_fotos.extend([f.name for f in fotos_planos])
                
                n_fotos_str = str(lista_fotos) if lista_fotos else "Sin fotos"
                id_prop = str(random.randint(10000, 99999))
                
                datos = [
                    id_prop, str(date.today()), titulo, tipo, precio_venta_final, 
                    ganancia_mia, neto_propietario, moneda, ciudad, barrio, 
                    prop_nom, prop_ced, prop_tel, prop_alt, prop_email,
                    area, habs, piso, antig, parqueadero, estado_fisico, 
                    ", ".join(amenidades), notas_obs, n_fotos_str,
                    "Sí" if es_planos else "No",
                    const_nom, proy_nom, str(fecha_ini), str(fecha_fin), monto_ini, num_cuotas,
                    "Disponible", "", "", 0, 0
                ]
                
                if guardar_fila("Propiedades", datos):
                    st.success("✅ ¡Propiedad Guardada Correctamente!")
                    st.balloons()
                else: st.error("Error al guardar en Google Sheets")
            else: st.warning("⚠️ Faltan datos obligatorios (Título o Precio)")

    # --- INVENTARIO & CRM ---
    elif menu == "📂 Inventario & CRM":
        st.header("📂 Inventario y Gestión")
        df = cargar_datos("Propiedades")
        
        if not df.empty:
            opciones = df["Título"] + " - " + df["Propietario"] if "Título" in df.columns else []
            seleccion = st.selectbox("🔍 Buscar Propiedad:", opciones)
            
            if seleccion:
                idx = df[df["Título"] + " - " + df["Propietario"] == seleccion].index[0]
                d = df.iloc[idx]
                
                st.markdown(f"### {d.get('Título')}")
                col_i1, col_i2 = st.columns([1, 2])
                with col_i1:
                    st.info(f"💰 Precio: {d.get('Moneda')} ${pd.to_numeric(d.get('Precio Venta',0), errors='coerce'):,.0f}")
                    if d.get('Fotos') != "Sin fotos": 
                        st.write("📷 Archivos cargados:")
                        st.code(d.get('Fotos'))
                    else: st.write("Sin fotos")
                with col_i2:
                    st.markdown('<div class="ficha-tecnica">', unsafe_allow_html=True)
                    st.write(f"📍 **Ubicación:** {d.get('Ciudad')} - {d.get('Barrio')}")
                    st.write(f"📐 **Detalles:** {d.get('Tipo')} | {d.get('Área')} m² | {d.get('Habs')} Habs")
                    st.write(f"🏗️ **Estado:** {d.get('Estado Físico')} | Antigüedad: {d.get('Antigüedad')}")
                    
                    if d.get("Sobre Planos") == "Sí":
                        st.warning(f"🚧 **PROYECTO:** {d.get('Proyecto')} por {d.get('Constructor')}")
                        st.write(f"📅 **Entrega:** {d.get('Fecha Fin')} | **Cuotas:** {d.get('Cuotas')}")
                    st.markdown("</div>", unsafe_allow_html=True)

    elif menu == "📊 Estadísticas":
        st.info("Próximamente métricas avanzadas.")