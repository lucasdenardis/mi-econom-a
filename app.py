import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json

# --- 1. CONFIGURACIÓN MODERNA DE LA INTERFAZ ---
st.set_page_config(page_title="Mi Economía | Dashboard", layout="wide", page_icon="💸")

# CSS para botones grandes y táctiles en mobile
st.markdown("""
<style>
[data-testid="stSidebar"] div[role="radiogroup"] > label {
    padding: 15px 20px;
    margin-bottom: 15px;
    background-color: #1E1E24;
    border-radius: 10px;
    border: 1px solid #444;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label p {
    font-size: 18px !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
    background-color: #2E2E38;
}
</style>
""", unsafe_allow_html=True)

# --- 2. GESTIÓN DE DATOS Y PERSISTENCIA (JSON + EXCEL) ---
ARCHIVO_DATOS = "datos_usuario.json"

@st.cache_data
def cargar_datos_historicos():
    archivo_excel = "Planificador_Financiero_Fusionado FINAL (1).xlsx"
    df_gastos_hist = pd.DataFrame()
    df_ingresos_hist = pd.DataFrame()
    
    if os.path.exists(archivo_excel):
        try:
            df_gastos_hist = pd.read_excel(archivo_excel, sheet_name='Gastos', header=3)
            df_gastos_hist = df_gastos_hist.dropna(subset=['Fecha', 'Monto ($)'])
            
            df_ingresos_hist = pd.read_excel(archivo_excel, sheet_name='Ingresos', header=3)
            df_ingresos_hist = df_ingresos_hist.dropna(subset=['Fecha', 'Monto ($)'])
        except Exception as e:
            st.error(f"Error leyendo el Excel: {e}")
            
    return df_ingresos_hist, df_gastos_hist

df_ingresos_hist, df_gastos_hist = cargar_datos_historicos()

# Inicializar Estado de Sesión por defecto
if 'tarjetas' not in st.session_state:
    st.session_state.tarjetas = [
        {"nombre": "Visa Macro", "limite": 4500000.0, "tipo": "Crédito"}
    ]

if 'gastos' not in st.session_state:
    st.session_state.gastos = df_gastos_hist

if 'ingresos' not in st.session_state:
    st.session_state.ingresos = df_ingresos_hist

# Cargar persistencia local de forma ultra segura (si falla, borra el archivo corrupto)
if os.path.exists(ARCHIVO_DATOS):
    try:
        with open(ARCHIVO_DATOS, "r") as f:
            data = json.load(f)
            if "gastos" in data and isinstance(data["gastos"], list) and len(data["gastos"]) > 0:
                st.session_state.gastos = pd.DataFrame(data["gastos"])
            if "ingresos" in data and isinstance(data["ingresos"], list) and len(data["ingresos"]) > 0:
                st.session_state.ingresos = pd.DataFrame(data["ingresos"])
            if "tarjetas" in data and isinstance(data["tarjetas"], list) and len(data["tarjetas"]) > 0:
                st.session_state.tarjetas = data["tarjetas"]
    except Exception:
        # Si el JSON está roto, lo eliminamos para evitar bloqueos
        os.remove(ARCHIVO_DATOS)

def guardar_estado():
    try:
        gasto_dict = st.session_state.gastos.to_dict(orient="records") if isinstance(st.session_state.gastos, pd.DataFrame) and not st.session_state.gastos.empty else []
        ingreso_dict = st.session_state.ingresos.to_dict(orient="records") if isinstance(st.session_state.ingresos, pd.DataFrame) and not st.session_state.ingresos.empty else []
        
        data = {
            "gastos": gasto_dict,
            "ingresos": ingreso_dict,
            "tarjetas": st.session_state.tarjetas
        }
        with open(ARCHIVO_DATOS, "w") as f:
            json.dump(data, f)
    except Exception as e:
        st.error(f"Error al guardar los datos: {e}")

def formato_arg(valor):
    return f"${float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- 3. NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.title("💸 Mi Economía")
    st.markdown("---")
    pagina = st.radio("Menú Principal", [
        "📊 Dashboard General", 
        "➕ Cargar Movimiento",
        "📅 Registro Diario",
        "🔄 Fijos y Automatización", 
        "💳 Estado de Tarjetas",
        "⚙️ Configurar Tarjetas"
    ])
    st.markdown("---")

# --- 4. PÁGINA: DASHBOARD GENERAL ---
if pagina == "📊 Dashboard General":
    st.title("Panel de Control Financiero")
    
    meses_disponibles = st.session_state.gastos['Mes'].dropna().unique().tolist() if not st.session_state.gastos.empty else ["Mes Actual"]
    indice_por_defecto = meses_disponibles.index("Julio") if "Julio" in meses_disponibles else 0
    mes_seleccionado = st.selectbox("Seleccionar Mes de Análisis", options=meses_disponibles, index=indice_por_defecto)
    
    df_gastos_mes = st.session_state.gastos[st.session_state.gastos['Mes'] == mes_seleccionado] if not st.session_state.gastos.empty else pd.DataFrame()
    df_ingresos_mes = st.session_state.ingresos[st.session_state.ingresos['Mes'] == mes_seleccionado] if not st.session_state.ingresos.empty else pd.DataFrame()
    
    ingresos_totales = df_ingresos_mes['Monto ($)'].sum() if not df_ingresos_mes.empty else 0
    
    if not df_gastos_mes.empty:
        mask_tc = df_gastos_mes['Medio de Pago'].astype(str).str.contains("Tarjeta|Visa|Mastercard", case=False, na=False)
        salidas_efectivas = df_gastos_mes[~mask_tc]['Monto ($)'].sum()
        deuda_tc = df_gastos_mes[mask_tc]['Monto ($)'].sum()
    else:
        salidas_efectivas = 0
        deuda_tc = 0

    ahorro_real = ingresos_totales - salidas_efectivas - deuda_tc
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ingresos Totales", formato_arg(ingresos_totales), "Liquidez")
    col2.metric("Salidas Efectivas", formato_arg(salidas_efectivas), "Débito/Efectivo", delta_color="inverse")
    col3.metric("Deuda TC Mes", formato_arg(deuda_tc), "Tarjetas", delta_color="inverse")
    col4.metric("Ahorro Real", formato_arg(ahorro_real), "Disponible libre")

    st.markdown("---")
    
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.subheader(f"Flujo de Caja ({mes_seleccionado})")
        fig_waterfall = go.Figure(go.Waterfall(
            name = "Flujo", orientation = "v",
            measure = ["relative", "relative", "relative", "total"],
            x = ["Ingresos", "Gastos Corrientes", "Tarjetas (Cuotas Mes)", "Ahorro Real"],
            textposition = "outside",
            y = [ingresos_totales, -salidas_efectivas, -deuda_tc, ahorro_real],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        fig_waterfall.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_waterfall, use_container_width=True)

    with col_graf2:
        st.subheader(f"Distribución de Gastos ({mes_seleccionado})")
        if not df_gastos_mes.empty:
            df_plot = df_gastos_mes.groupby('Categoría')['Monto ($)'].sum().reset_index()
            fig_pie = px.pie(df_plot, values='Monto ($)', names='Categoría', hole=0.4, template="plotly_dark")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info(f"No hay datos de gastos para graficar en {mes_seleccionado}.")

# --- 5. PÁGINA: REGISTRO DIARIO ---
elif pagina == "📅 Registro Diario":
    st.title("Registro Diario de Movimientos")
    st.write("Visualizá todos tus movimientos cargados y exportalos.")
    
    meses_historicos = st.session_state.gastos['Mes'].dropna().unique().tolist() if not st.session_state.gastos.empty else []
    mes_filtro = st.selectbox("Filtrar por Mes", options=["Ver Todos"] + meses_historicos)
    
    df_mostrar = st.session_state.gastos.copy()
    if mes_filtro != "Ver Todos" and not df_mostrar.empty:
        df_mostrar = df_mostrar[df_mostrar['Mes'] == mes_filtro]
    
    if not df_mostrar.empty and 'Monto ($)' in df_mostrar.columns:
        df_mostrar_fmt = df_mostrar.copy()
        df_mostrar_fmt['Monto ($)'] = df_mostrar_fmt['Monto ($)'].apply(lambda x: formato_arg(x) if pd.notnull(x) else x)
        st.dataframe(df_mostrar_fmt, use_container_width=True)
    else:
        st.info("No hay movimientos registrados para mostrar.")
    
    if not df_mostrar.empty:
        csv = df_mostrar.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Exportar Movimientos a CSV", data=csv, file_name='registro_gastos.csv', mime='text/csv')

# --- 6. PÁGINA: CARGAR MOVIMIENTO ---
elif pagina == "➕ Cargar Movimiento":
    st.title("Registrar Nuevo Movimiento")
    
    tipo_movimiento = st.segmented_control("Tipo de Registro", ["🔴 Gasto Variable", "🟢 Ingreso"], default="🔴 Gasto Variable")
    
    categorias_completas = [
        "Supermercado", "Salidas / Gastronomía", "Delivery", "Mascota (Chancho)", 
        "Gimnasio / CrossFit", "Transporte / Auto", "Salud / Farmacia", 
        "Expensas", "Luz", "Agua", "Gas", "Internet", "Telefonía", 
        "Prepaga", "Seguro Auto", "Seguros Adicionales", "Monotributo", 
        "Profesional (Colegiatura)", "Impuestos y Costos TC", 
        "Compras Online / Impulsivas", "Otros Gastos"
    ]
    
    nombres_tarjetas = [t["nombre"] for t in st.session_state.tarjetas]
    medios_pago_opciones = ["Débito / Efectivo / MP"] + nombres_tarjetas
    
    with st.container(border=True):
        if tipo_movimiento == "🔴 Gasto Variable":
            col1, col2 = st.columns(2)
            with col1:
                fecha = st.date_input("Fecha", format="DD/MM/YYYY")
                descripcion = st.text_input("Descripción (Ej. Supermercado, Amazon)")
                monto = st.number_input("Monto", min_value=0.0, format="%.2f")
                categoria = st.selectbox("Categoría", categorias_completas)
                compartido = st.toggle("Dividir 50% con Tomas")
            
            with col2:
                medio = st.selectbox("Medio de Pago", medios_pago_opciones)
                if medio != "Débito / Efectivo / MP":
                    mes_imputacion = st.selectbox("Mes de Imputación", ["Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
                    cuotas = st.number_input("Cuotas", 1, 24, 1)
                else:
                    mes_imputacion = "Julio"
                    cuotas = 1
                
                moneda = st.selectbox("Moneda", ["Pesos (ARS)", "Dólares (USD)"])
                if moneda == "Dólares (USD)":
                    metodo_usd = st.radio("Forma de pago", ["Dólar Tarjeta (Suma impuestos)", "Dólar MEP (Stop Debit)"])
                    if metodo_usd == "Dólar MEP (Stop Debit)":
                        st.number_input("Cotización MEP (ARS)", min_value=1000.0)
            
            if st.button("💾 Guardar Gasto", type="primary", use_container_width=True):
                nuevo_gasto = pd.DataFrame([{
                    "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Mes": mes_imputacion,
                    "Descripción": descripcion if descripcion else "Sin descripción",
                    "Categoría": categoria,
                    "Tipo": "Variable",
                    "Monto ($)": monto,
                    "Medio de Pago": medio
                }])
                st.session_state.gastos = pd.concat([st.session_state.gastos, nuevo_gasto], ignore_index=True)
                guardar_estado()
                st.success("¡Gasto guardado con éxito y registrado en el sistema!")
                
        else:
            st.subheader("Cargar Ingreso")
            fuente = st.selectbox("Fuente", ["Residencia (Epidemiología)", "Saldan", "Laboratorio SEVEDIC", "Otros ingresos"])
            fecha_ingreso = st.date_input("Fecha de Ingreso", format="DD/MM/YYYY")
            monto_ingreso = st.number_input("Monto ($)", min_value=0.0)
            if st.button("💾 Guardar Ingreso", type="primary", use_container_width=True):
                nuevo_ingreso = pd.DataFrame([{
                    "Fecha": fecha_ingreso.strftime("%Y-%m-%d"),
                    "Mes": "Julio",
                    "Fuente": fuente,
                    "Detalle": "Ingreso manual",
                    "Monto ($)": monto_ingreso
                }])
                st.session_state.ingresos = pd.concat([st.session_state.ingresos, nuevo_ingreso], ignore_index=True)
                guardar_estado()
                st.success("¡Ingreso registrado con éxito!")

# --- 7. PÁGINA: FIJOS Y AUTOMATIZACIÓN ---
elif pagina == "🔄 Fijos y Automatización":
    st.title("Gastos Fijos del Mes")
    st.write("Estos gastos se precargan el día 1. Confirmá el monto real para que impacten en tu flujo.")
    
    fijos = [
        {"nombre": "Expensas", "estimado": 120000, "estado": "Pendiente"},
        {"nombre": "EPEC", "estimado": 31622, "estado": "Pendiente"},
        {"nombre": "Gimnasio / CrossFit", "estimado": 35000, "estado": "Confirmado"},
        {"nombre": "Prepaga", "estimado": 218514, "estado": "Pendiente"}
    ]
    
    for f in fijos:
        with st.container(border=True):
            col_izq, col_der = st.columns([3, 1])
            with col_izq:
                st.markdown(f"**{f['nombre']}**")
                monto_real = st.number_input(f"Monto Final", value=f['estimado'], key=f['nombre'])
            with col_der:
                st.write("")
                st.write("")
                if f['estado'] == "Pendiente":
                    st.button("🟡 Confirmar Pago", key=f"btn_{f['nombre']}", use_container_width=True)
                else:
                    st.button("🟢 Pagado", disabled=True, key=f"btn_{f['nombre']}", use_container_width=True)

# --- 8. PÁGINA: ESTADO DE TARJETAS ---
elif pagina == "💳 Estado de Tarjetas":
    st.title("Límites y Consumos de Tarjetas")
    st.info("Monitoreo dinámico de tus plásticos cargados.")
    
    for t in st.session_state.tarjetas:
        st.subheader(t["nombre"])
        col_lim1, col_lim2 = st.columns(2)
        with col_lim1:
            st.write(f"Límite Configurado: {formato_arg(t['limite'])}")
            
            if not st.session_state.gastos.empty and 'Medio de Pago' in st.session_state.gastos.columns:
                gasto_tc = st.session_state.gastos[st.session_state.gastos['Medio de Pago'] == t["nombre"]]['Monto ($)'].sum()
            else:
                gasto_tc = 0
                
            porcentaje = min(gasto_tc / t["limite"], 1.0) if t["limite"] > 0 else 0
            st.progress(porcentaje)
            st.caption(f"Consumido: {formato_arg(gasto_tc)} / Disponible: {formato_arg(t['limite'] - gasto_tc)}")
        with col_lim2:
            st.metric("Total Proyectado en Resumen", formato_arg(gasto_tc))
        st.markdown("---")

# --- 9. PÁGINA: CONFIGURAR TARJETAS ---
elif pagina == "⚙️ Configurar Tarjetas":
    st.title("Administración de Tarjetas de Crédito")
    st.write("Agregá nuevas tarjetas, modificá sus nombres o actualiza sus límites de compra.")
    
    with st.form("form_nueva_tarjeta"):
        st.subheader("Agregar Nueva Tarjeta")
        nuevo_nombre = st.text_input("Nombre de la Tarjeta (Ej. Mastercard Galicia, Visa Macro Roby)")
        nuevo_limite = st.number_input("Límite de Compra ($)", min_value=0.0, value=1000000.0)
        
        btn_agregar = st.form_submit_button("➕ Agregar Tarjeta", type="primary")
        if btn_agregar:
            if nuevo_nombre:
                st.session_state.tarjetas.append({"nombre": nuevo_nombre, "limite": nuevo_limite, "tipo": "Crédito"})
                guardar_estado()
                st.success(f"¡Tarjeta '{nuevo_nombre}' agregada con éxito!")
                st.rerun()
            else:
                st.error("Por favor ingresá un nombre para la tarjeta.")
                
    st.markdown("---")
    st.subheader("Tarjetas Registradas Actualmente")
    for i, t in enumerate(st.session_state.tarjetas):
        col_t1, col_t2, col_t3 = st.columns([2, 2, 1])
        with col_t1:
            st.text(f"💳 {t['nombre']}")
        with col_t2:
            st.text(f"Límite: {formato_arg(t['limite'])}")
        with col_t3:
            if st.button("🗑️ Eliminar", key=f"del_card_{i}"):
                st.session_state.tarjetas.pop(i)
                guardar_estado()
                st.rerun()
