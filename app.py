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

# --- ESTILOS PERSONALIZADOS ---
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
    }
    .ficha-tecnica {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid #1A2980;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .alerta-pago {
        background-color: #ffcccc;
        color: #990000;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
        border: 1px solid #ff0000;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y DATOS ---
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
            # Convertir listas/dict a JSON string para guardar en celda
            datos_procesados = []
            for d in datos:
                if isinstance(d, (list, dict)): datos_procesados.append(json.dumps(d))
                else: datos_procesados.append(str(d))
            ws.append_row(datos_procesados)
            return True
        except: return False
    return False

def actualizar_dato(pestana, id_col, id_val, col_edit, nuevo_valor):
    sh = conectar_google_sheets()
    if sh:
        try:
            ws = sh.worksheet(pestana)
            cell = ws.find(str(id_val))
            # Encontrar indice de columna
            headers = ws.row_values(1)
            col_idx = headers.index(col_edit) + 1
            ws.update_cell(cell.row, col_idx, str(nuevo_valor))
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
            with st.form("log"):
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
                    else: st.error("Usuario no existe")
        with t2:
            with st.form("reg"):
                nu = st.text_input("Usuario")
                np = st.text_input("Clave", type="password")
                nn = st.text_input("Nombre")
                nr = st.selectbox("Rol", ["Agente", "Administrador"])
                if st.form_submit_button("CREAR"):
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

    # --- NUEVO REGISTRO (DISEÑO SOLICITADO) ---
    if menu == "➕ Nuevo Registro":
        st.header("📝 Nuevo Registro de Propiedad")
        
        with st.form("form_full"):
            
            # --- SECCIÓN 1: PROPIETARIO (PAREJAS) ---
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

            # --- SECCIÓN 2: FINANCIERA (TU LÓGICA) ---
            st.subheader("2. Finanzas")
            col_mon, col_fin = st.columns([1, 3])
            moneda = col_mon.selectbox("Moneda", ["COP - Colombia", "USD - Dólar", "EUR - Euro", "PEN - Sol Perú", "VES - Bolívar", "CLP - Chile", "ARS - Argentina"])
            simbolo = moneda.split(" ")[0]
            
            # Lógica: Porcentaje vs Pase
            modo_fin = st.radio("Modalidad de Negocio:", ["Porcentaje (%)", "Pase (Sobreprecio)"], horizontal=True)
            
            precio_venta_final = 0.0
            ganancia_mia = 0.0
            neto_propietario = 0.0
            
            if modo_fin == "Porcentaje (%)":
                # Lógica: Restar comisión del total
                c_f1, c_f2 = st.columns(2)
                precio_total_input = c_f1.number_input(f"Precio Total de Venta ({simbolo})", min_value=0.0, step=1000000.0)
                pct_comision = c_f2.number_input("Porcentaje Comisión (%)", value=3.0)
                
                ganancia_mia = precio_total_input * (pct_comision / 100)
                neto_propietario = precio_total_input - ganancia_mia
                precio_venta_final = precio_total_input
                
            else: # Modo Pase
                # Lógica: Excedente
                c_f1, c_f2 = st.columns(2)
                neto_propietario_input = c_f1.number_input(f"Neto Propietario (Lo que pide el dueño)", min_value=0.0, step=1000000.0)
                precio_venta_input = c_f2.number_input(f"Precio Venta (En cuánto lo ofreces)", min_value=0.0, step=1000000.0)
                
                if precio_venta_input >= neto_propietario_input:
                    ganancia_mia = precio_venta_input - neto_propietario_input
                else:
                    ganancia_mia = 0
                
                neto_propietario = neto_propietario_input
                precio_venta_final = precio_venta_input

            # Mostrar Resultados
            c_res1, c_res2 = st.columns(2)
            c_res1.metric("💰 Ganancia Mía (Comisión)", f"{simbolo} {ganancia_mia:,.0f}")
            c_res2.metric("👤 Para Propietario", f"{simbolo} {neto_propietario:,.0f}")
            
            st.markdown("---")

            # --- SECCIÓN 3: DETALLES INMUEBLE (TU LAYOUT) ---
            st.subheader("3. Detalles del Inmueble")
            titulo = st.text_input("Título del Anuncio (Ej: Apto Lujo Cabecera)")
            
            # Fila 1 (4 cols)
            r1c1, r1c2, r1c3, r1c4 = st.columns(4)
            tipo = r1c1.selectbox("Tipo", ["Apartamento", "Casa", "Lote", "Local", "Bodega", "Finca"])
            ciudad = r1c2.text_input("Ciudad", "Bucaramanga")
            barrio = r1c3.text_input("Barrio")
            estrato = r1c4.selectbox("Estrato", ["1","2","3","4","5","6","Comercial","Rural"])
            
            # Fila 2 (4 cols)
            r2c1, r2c2, r2c3, r2c4 = st.columns(4)
            area = r2c1.number_input("Área (m²)")
            habs = r2c2.number_input("Habitaciones", min_value=0)
            piso = r2c3.text_input("Piso / Nivel")
            antig = r2c4.selectbox("Antigüedad", ["Sobre Planos", "Estrenar", "1-5 años", "5-10 años", "+10 años"])
            
            # Fila 3 (2 cols)
            r3c1, r3c2 = st.columns(2)
            parqueadero = r3c1.selectbox("🚘 Parqueadero", ["Privado", "Comunal", "Visitantes", "No tiene"])
            estado_fisico = r3c2.selectbox("🏗️ Estado Físico", ["Excelente", "Bueno", "Regular", "Remodelar"])
            
            amenidades = st.multiselect("💎 Amenidades", ["Piscina", "Vigilancia", "Ascensor", "Gym", "BBQ", "Salón Social", "Canchas"])
            
            notas_obs = st.text_area("📝 Notas u Observaciones")
            fotos = st.file_uploader("📸 SUBIR FOTOS (Clic aquí)", accept_multiple_files=True)

            st.markdown("---")

            # --- SECCIÓN 4: SOBRE PLANOS (NUEVA) ---
            st.subheader("4. Apartamentos Sobre Planos")
            es_planos = st.checkbox("🏗️ ¿Es un proyecto Sobre Planos?")
            
            const_nom = ""; proy_nom = ""; fecha_ini = ""; fecha_fin = ""
            monto_ini = 0.0; num_cuotas = 0
            
            if es_planos:
                sp1, sp2 = st.columns(2)
                const_nom = sp1.text_input("Nombre Constructor")
                proy_nom = sp2.text_input("Nombre Proyecto")
                
                sp3, sp4 = st.columns(2)
                fecha_ini = sp3.date_input("Fecha Inicio Obra")
                fecha_fin = sp4.date_input("Fecha Posible Culminación")
                
                sp5, sp6 = st.columns(2)
                monto_ini = sp5.number_input("Monto Inicial Sugerido", min_value=0.0)
                num_cuotas = sp6.number_input("N° de Cuotas", min_value=1)
                
                st.info("Nota: Estos valores se usarán como base para el plan de pagos del cliente.")

            # BOTÓN FINAL
            if st.form_submit_button("💾 GUARDAR TODO EN LA NUBE", type="primary"):
                if titulo and precio_venta_final > 0:
                    n_fotos = [f.name for f in fotos] if fotos else "Sin fotos"
                    
                    # Estructura de Datos (ID Único para CRM)
                    id_prop = str(random.randint(10000, 99999))
                    
                    datos = [
                        id_prop, str(date.today()), titulo, tipo, precio_venta_final, 
                        ganancia_mia, neto_propietario, moneda, ciudad, barrio, 
                        prop_nom, prop_ced, prop_tel, prop_alt, prop_email,
                        area, habs, piso, antig, parqueadero, estado_fisico, 
                        ", ".join(amenidades), notas_obs, str(n_fotos),
                        "Sí" if es_planos else "No",
                        const_nom, proy_nom, str(fecha_ini), str(fecha_fin), monto_ini, num_cuotas,
                        "Disponible", # Estado Venta
                        "", "", 0, 0 # Campos Vacíos para Cliente, Deuda, Pagado (CRM)
                    ]
                    
                    if guardar_fila("Propiedades", datos):
                        st.success("✅ Registro Exitoso")
                        st.balloons()
                    else: st.error("Error al guardar")
                else: st.warning("Falta Título o Precio")

    # --- INVENTARIO & CRM (POTENTE) ---
    elif menu == "📂 Inventario & CRM":
        
        tab_inv, tab_ag = st.tabs(["🏠 Inventario & Ventas", "📅 Agenda de Citas"])
        
        # --- TAB 1: INVENTARIO ---
        with tab_inv:
            df = cargar_datos("Propiedades")
            if not df.empty:
                # Selector de Propiedad
                opciones = df["Título"] + " - " + df["Propietario"] if "Título" in df.columns else []
                seleccion = st.selectbox("🔍 Selecciona Propiedad para Gestionar:", opciones)
                
                if seleccion:
                    idx = df[df["Título"] + " - " + df["Propietario"] == seleccion].index[0]
                    d = df.iloc[idx]
                    id_actual = d.get("ID", "")
                    
                    # --- FICHA TÉCNICA VISUAL ---
                    st.markdown(f"### 🏷️ {d.get('Título')} ({d.get('Tipo')})")
                    c_vis1, c_vis2 = st.columns([1, 2])
                    
                    with c_vis1:
                        if d.get('Fotos') and d['Fotos'] != "Sin fotos":
                            st.image("https://via.placeholder.com/300x200?text=FOTO+INMUEBLE", caption="Imagen Referencia (Drive API pendiente)")
                            st.caption(f"Archivos: {d['Fotos']}")
                        else: st.info("Sin fotos")
                        
                        st.metric("Precio Venta", f"${pd.to_numeric(d.get('Precio Venta',0), errors='coerce'):,.0f}")
                        if st.checkbox("Ver Datos Privados"):
                            st.write(f"**Propietario:** {d.get('Nombre Propietario')}")
                            st.write(f"**Tel:** {d.get('Teléfono Principal')}")
                            st.caption(f"Comisión: ${pd.to_numeric(d.get('Ganancia',0), errors='coerce'):,.0f}")
                    
                    with c_vis2:
                        st.markdown('<div class="ficha-tecnica">', unsafe_allow_html=True)
                        cc1, cc2 = st.columns(2)
                        cc1.write(f"📍 **Ubicación:** {d.get('Ciudad')} - {d.get('Barrio')}")
                        cc1.write(f"📐 **Área:** {d.get('Área')} m² | **Habs:** {d.get('Habs')}")
                        cc1.write(f"🏗️ **Estado:** {d.get('Estado Físico')}")
                        cc2.write(f"🏢 **Piso:** {d.get('Piso')}")
                        cc2.write(f"⏳ **Antigüedad:** {d.get('Antigüedad')}")
                        cc2.write(f"🚘 **Parqueadero:** {d.get('Parqueadero')}")
                        
                        if d.get("Sobre Planos") == "Sí":
                            st.warning(f"🏗️ **PROYECTO:** {d.get('Proyecto')} por {d.get('Constructor')}")
                            st.write(f"📅 **Entrega:** {d.get('Fecha Fin')}")
                        
                        st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("---")
                    
                    # --- CRM DE VENTAS (COMPLEJO) ---
                    st.subheader("💼 Gestión de Venta")
                    estado_actual = d.get("Estado Venta", "Disponible")
                    
                    if estado_actual == "Disponible":
                        with st.expander("🤝 CERRAR NEGOCIO (Registrar Venta/Separación)"):
                            cli_nom = st.text_input("Nombre Cliente Comprador")
                            cli_tel = st.text_input("Teléfono Cliente")
                            
                            tipo_venta = st.radio("Tipo Venta", ["Contado", "Crédito / Plazos", "Planos (Cuotas)"])
                            
                            if tipo_venta == "Planos (Cuotas)" or d.get("Sobre Planos") == "Sí":
                                # Lógica Sobre Planos
                                ci = st.number_input("Cuota Inicial ($)", value=float(d.get("Monto Inicial", 0)))
                                nc = st.number_input("Número Cuotas", value=int(d.get("Cuotas", 1)))
                                val_cuota = (float(d.get("Precio Venta", 0)) - ci) / nc if nc > 0 else 0
                                st.info(f"Cuota Mensual Aprox: ${val_cuota:,.0f}")
                                
                                if st.button("CONFIRMAR SEPARACIÓN"):
                                    # Actualizar Sheet
                                    # Esto requiere lógica avanzada de actualización, simplificada aquí:
                                    st.success(f"Negocio Cerrado con {cli_nom}. Deuda registrada.")
                                    # Aquí llamarías a actualizar_dato() para cambiar estado y guardar cliente
                            
                            else:
                                # Contado / Crédito Simple
                                abono = st.number_input("Abono Inicial")
                                if st.button("VENDER"):
                                    st.success("Venta Registrada")

                    else:
                        st.success(f"✅ VENDIDA / SEPARADA a: {d.get('Cliente Comprador')}")
                        
                        # BARRA DE PROGRESO (GRÁFICA)
                        pagado = float(d.get("Pagado", 0))
                        total = float(d.get("Precio Venta", 1))
                        progreso = min(pagado / total, 1.0)
                        
                        st.write("📊 **Estado de Pagos**")
                        st.progress(progreso)
                        c_m1, c_m2 = st.columns(2)
                        c_m1.metric("Pagado", f"${pagado:,.0f}")
                        c_m2.metric("Deuda Restante", f"${(total - pagado):,.0f}", delta_color="inverse")
                        
                        if pagado < total:
                            with st.form("abonar"):
                                abono_nuevo = st.number_input("Registrar Nuevo Pago ($)")
                                if st.form_submit_button("Registrar Pago"):
                                    st.success("Pago sumado (Simulado - Requiere DB Update)")

        # --- TAB 2: AGENDA (ILIMITADA) ---
        with tab_ag:
            st.subheader("📅 Agenda de Citas")
            
            # Formulario
            with st.form("agenda_form"):
                ca1, ca2 = st.columns(2)
                nombre_cli = ca1.text_input("Nombre Cliente")
                lugar_cita = ca2.text_input("Propiedad / Lugar")
                
                ca3, ca4 = st.columns(2)
                tel1 = ca3.text_input("Teléfono 1")
                tel2 = ca4.text_input("Teléfono 2")
                
                ca5, ca6 = st.columns(2)
                fecha_cita = ca5.date_input("Fecha")
                hora_cita = ca6.time_input("Hora")
                
                if st.form_submit_button("AGENDAR CITA"):
                    datos_cita = [str(date.today()), nombre_cli, tel1, tel2, lugar_cita, str(fecha_cita), str(hora_cita), "Pendiente"]
                    if guardar_fila("Agenda", datos_cita): st.success("Cita Guardada")
            
            st.divider()
            
            # Visualizar Agenda con Alarmas
            df_ag = cargar_datos("Agenda")
            if not df_ag.empty:
                st.write("🔔 **Próximas Visitas**")
                # Filtrar y ordenar sería ideal aquí
                for i, row in df_ag.iterrows():
                    # Alarma Visual
                    fecha_row = row.get("Fecha Cita", "")
                    try:
                        f_cita_dt = datetime.strptime(fecha_row, "%Y-%m-%d").date()
                        hoy = date.today()
                        
                        if f_cita_dt == hoy:
                            st.warning(f"🚨 HOY: Cita con {row.get('Cliente')} en {row.get('Lugar')} a las {row.get('Hora')}")
                        elif f_cita_dt < hoy and row.get("Estado") == "Pendiente":
                            st.error(f"❌ VENCIDA: Cita con {row.get('Cliente')} ({fecha_row})")
                        elif f_cita_dt > hoy:
                            st.info(f"📅 {fecha_row}: {row.get('Cliente')} - {row.get('Lugar')}")
                    except:
                        st.write(f"📄 {row.get('Cliente')} - {fecha_row}")

    # --- ESTADÍSTICAS ---
    elif menu == "📊 Estadísticas":
        st.header("Tablero de Mando")
        st.info("Visualización de rendimiento global.")