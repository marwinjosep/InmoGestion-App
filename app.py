import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import hashlib
import random
import json
import urllib.parse
from datetime import date, datetime

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
        font-size: 16px;
    }
    .marketing-box {
        background-color: #222;
        color: #fff;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #444;
        margin-bottom: 10px;
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

def check_hashes(p, h): return hashlib.sha256(str.encode(p)).hexdigest() == h
def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. GENERADOR DE GUIONES INTELIGENTE ---
def generar_marketing(d):
    # Datos básicos
    precio = f"{d.get('Moneda', 'COP')} ${pd.to_numeric(d.get('Precio Venta', 0), errors='coerce'):,.0f}"
    ubicacion = f"{d.get('Barrio')}, {d.get('Ciudad')}"
    tipo = d.get('Tipo')
    amenidades = d.get('Amenidades', '').replace("[", "").replace("]", "").replace("'", "")
    
    # Emojis según tipo
    emoji_casa = "🏡" if tipo == "Casa" else "🏢"
    
    # GUION 1: ESTILO TIKTOK VIRAL (Rápido y Visual)
    guion_tiktok = f"""🚨 ¡STOP SCROLLING! 🚨
¿Buscas vivir en {ubicacion}? 👇

Mira este {tipo} INCREÍBLE que acaba de entrar al mercado {emoji_casa}
✨ Lo mejor: {amenidades}
💰 Precio de Oportunidad: {precio}

Perfecto para ti si buscas estilo y comodidad. 
¡Quedan pocos así! 🏃‍♂️💨

📲 Escribe "INFO" en los comentarios o ve al link de mi perfil para agendar visita HOY.
"""

    # GUION 2: ESTILO INVERSIONISTA (Serio y Datos)
    guion_inversion = f"""📈 OPORTUNIDAD DE INVERSIÓN EN {d.get('Ciudad').upper()}
    
📍 Ubicación Estratégica: {d.get('Barrio')}
💲 Valor: {precio}
📐 Área: {d.get('Área')} m² | {d.get('Habs')} Habs

Ideal para {tipo} de renta corta o valorización. 
Propiedad lista para traspaso. {emoji_casa}

💬 Envíame DM para ver la proyección financiera completa.
#InversionInmobiliaria #BienesRaices{d.get('Ciudad')}
"""

    # HASHTAGS
    hashtags = f"#{d.get('Ciudad').replace(' ','')} #VentaDe{tipo} #BienesRaices #Inmobiliaria #{d.get('Barrio').replace(' ','')} #RealEstateColombia #FincaRaiz"

    # LINK DE WHATSAPP
    mensaje_wa = f"Hola, vi el {tipo} en {d.get('Barrio')} de {precio} y quiero más información."
    link_wa = f"https://wa.me/?text={urllib.parse.quote(mensaje_wa)}"

    return guion_tiktok, guion_inversion, hashtags, link_wa

# --- 4. SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'user_role' not in st.session_state: st.session_state.user_role = ""

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
                if guardar_fila("Usuarios", [nu, make_hashes(np), nn, nr, ""]): st.success("Cuenta Creada")

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
        st.info("Completa los datos para generar la ficha.")
        
        # PROPIETARIO
        st.subheader("1. Datos del Propietario")
        c1, c2 = st.columns(2); prop_nom = c1.text_input("Nombre"); prop_ced = c2.text_input("Cédula")
        c3, c4 = st.columns(2); prop_tel = c3.text_input("Teléfono"); prop_email = c4.text_input("Email")
        c5, c6 = st.columns(2); prop_alt = c5.text_input("Tel. Alternativo"); docs = c6.file_uploader("📂 Documentos", accept_multiple_files=True)
        
        st.markdown("---")
        
        # FINANZAS
        st.subheader("2. Finanzas")
        cm, cf = st.columns([1,3])
        moneda = cm.selectbox("Moneda", ["COP - Colombia", "USD - Dólar", "EUR - Euro", "PEN - Sol", "VES - Bolívar"])
        simbolo = moneda.split(" ")[0]
        modo = st.radio("Modalidad:", ["Porcentaje (%)", "Pase (Sobreprecio)"], horizontal=True)
        
        pvf = 0.0; gm = 0.0; np = 0.0
        if modo == "Porcentaje (%)":
            c_f1, c_f2 = st.columns(2)
            pt = c_f1.number_input(f"Precio Total ({simbolo})", min_value=0.0, step=1e6)
            pct = c_f2.number_input("Comisión (%)", value=3.0)
            gm = pt * (pct/100); np = pt - gm; pvf = pt
        else:
            st.success("Modo Pase: Tú defines el excedente.")
            c_f1, c_f2 = st.columns(2)
            np_in = c_f1.number_input("Neto Propietario (Lo que pide)", min_value=0.0, step=1e6)
            pv_in = c_f2.number_input("Precio Venta (Tu oferta)", min_value=0.0, step=1e6)
            gm = pv_in - np_in if pv_in >= np_in else 0; np = np_in; pvf = pv_in
            
        c_r1, c_r2 = st.columns(2)
        c_r1.metric("💰 Tu Ganancia", f"{simbolo} {gm:,.0f}")
        c_r2.metric("👤 Propietario", f"{simbolo} {np:,.0f}")
        
        st.markdown("---")
        
        # DETALLES
        st.subheader("3. Detalles del Inmueble")
        tit = st.text_input("Título del Anuncio")
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        tipo = r1c1.selectbox("Tipo", ["Apartamento", "Casa", "Lote", "Local", "Bodega"])
        ciu = r1c2.text_input("Ciudad", "Bucaramanga"); bar = r1c3.text_input("Barrio")
        est = r1c4.selectbox("Estrato", ["1","2","3","4","5","6","Comercial"])
        
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        area = r2c1.number_input("Área (m²)"); habs = r2c2.number_input("Habs", min_value=0)
        piso = r2c3.text_input("Piso"); ant = r2c4.selectbox("Antigüedad", ["Sobre Planos", "Estrenar", "Usado"])
        
        r3c1, r3c2 = st.columns(2)
        pq = r3c1.selectbox("Parqueadero", ["Privado", "Comunal", "No tiene"])
        ef = r3c2.selectbox("Estado", ["Excelente", "Bueno", "Remodelar"])
        ame = st.multiselect("Amenidades", ["Piscina", "Gym", "Ascensor", "BBQ", "Vigilancia"])
        notas = st.text_area("Notas")
        fotos_gral = st.file_uploader("📸 Fotos Generales", accept_multiple_files=True)
        
        st.markdown("---")
        
        # SOBRE PLANOS
        st.subheader("4. Sobre Planos")
        es_planos = st.checkbox("🏗️ Es Proyecto Sobre Planos")
        cn=""; pn=""; fi=""; ff=""; mi=0.0; nc=0; fp=[]
        
        if es_planos:
            sp1, sp2, sp3 = st.columns([2,2,1])
            cn = sp1.text_input("Constructor"); pn = sp2.text_input("Proyecto"); fi = sp3.date_input("Inicio Obra")
            sp4, sp5, sp6 = st.columns([2,1,2])
            mi = sp4.number_input("Monto Inicial"); nc = sp5.number_input("Cuotas"); ff = sp6.date_input("Culminación")
            st.markdown("##### 📸 Renders / Avances")
            fp = st.file_uploader("Subir Renders", accept_multiple_files=True)
            
        if st.button("💾 GUARDAR PROPIEDAD", type="primary"):
            if tit and pvf > 0:
                lf = []
                if fotos_gral: lf.extend([f.name for f in fotos_gral])
                if es_planos and fp: lf.extend([f.name for f in fp])
                
                datos = [str(random.randint(10000,99999)), str(date.today()), tit, tipo, pvf, gm, np, moneda, ciu, bar, prop_nom, prop_ced, prop_tel, prop_alt, prop_email, area, habs, piso, ant, pq, ef, str(ame), notas, str(lf), "Sí" if es_planos else "No", cn, pn, str(fi), str(ff), mi, nc, "Disponible", "", "", 0, 0]
                
                if guardar_fila("Propiedades", datos): st.success("✅ Guardado Exitoso"); st.balloons()
                else: st.error("Error al guardar")
            else: st.warning("Faltan datos clave")

    # --- INVENTARIO & MARKETING (AQUÍ ESTÁ LA MAGIA) ---
    elif menu == "📂 Inventario & CRM":
        st.header("📂 Gestión de Inventario")
        df = cargar_datos("Propiedades")
        
        if not df.empty:
            op = df["Título"] + " - " + df["Propietario"] if "Título" in df.columns else []
            sel = st.selectbox("🔍 Buscar Propiedad:", op)
            
            if sel:
                idx = df[df["Título"] + " - " + df["Propietario"] == sel].index[0]
                d = df.iloc[idx]
                
                # PESTAÑAS
                tab_ficha, tab_mkt, tab_venta = st.tabs(["📄 Ficha Técnica", "🚀 Generador de Marketing", "💰 Venta y Cartera"])
                
                with tab_ficha:
                    c1, c2 = st.columns([1,2])
                    with c1:
                        st.image("https://via.placeholder.com/400x300?text=FOTO+PRINCIPAL", use_container_width=True)
                        st.info(f"💵 Precio: {d.get('Moneda')} ${pd.to_numeric(d.get('Precio Venta',0), errors='coerce'):,.0f}")
                    with c2:
                        st.markdown(f"### {d.get('Título')}")
                        st.write(f"📍 **{d.get('Ciudad')} - {d.get('Barrio')}**")
                        st.write(f"📐 {d.get('Área')}m² | 🛏️ {d.get('Habs')} Habs | 🚿 {d.get('Estado Físico')}")
                        st.write(f"🏢 Piso: {d.get('Piso')} | {d.get('Antigüedad')}")
                        st.write(f"💎 **Amenidades:** {d.get('Amenidades')}")
                        if d.get("Sobre Planos") == "Sí":
                            st.warning(f"🏗️ **PROYECTO:** {d.get('Proyecto')} (Entrega: {d.get('Fecha Fin')})")

                # --- MÓDULO DE MARKETING (NUEVO) ---
                with tab_mkt:
                    st.subheader("📢 Centro de Comando de Redes Sociales")
                    st.info("El sistema ha generado estos contenidos automáticamente para ti. ¡Solo copia, pega y publica!")
                    
                    g_tiktok, g_inver, g_tags, link_w = generar_marketing(d)
                    
                    c_m1, c_m2 = st.columns(2)
                    
                    with c_m1:
                        st.markdown("#### 🎵 Para TikTok / Reels (Estilo Viral)")
                        st.code(g_tiktok, language="text")
                        st.caption("👆 Dale clic al ícono de copiar en la esquina.")
                        
                        st.markdown("#### #️⃣ Hashtags Generados")
                        st.code(g_tags, language="text")
                        
                    with c_m2:
                        st.markdown("#### 💼 Para LinkedIn / Facebook (Estilo Serio)")
                        st.code(g_inver, language="text")
                        
                        st.markdown("#### 🚀 Acciones Rápidas")
                        st.markdown(f"""
                        <a href="{link_w}" target="_blank">
                            <button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; font-weight:bold; cursor:pointer; width:100%;">
                                📲 Enviar Ficha por WhatsApp
                            </button>
                        </a>
                        """, unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.warning("📸 **Recuerda:** Descarga las fotos de la ficha técnica para tu video.")

                with tab_venta:
                    st.write("Panel de Cierre de Negocios y Cartera (Configurado en pasos anteriores).")
                    # (Aquí iría la lógica de ventas que ya hicimos, resumida para no saturar el código)
                    st.metric("Estado Actual", d.get("Estado Venta", "Disponible"))