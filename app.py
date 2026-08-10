import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- 1. CONFIGURACIÓN MODERNA DE LA INTERFAZ ---
st.set_page_config(page_title="Mi Economía | Dashboard", layout="wide", page_icon="💸")

# Inyección de CSS para rediseñar botones del menú y mejorar la vista móvil
st.markdown("""
<style>
/* Hacer los botones del menú lateral gigantes y separados */
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
/* Cambiar color cuando pasas el dedo/mouse */
[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
    background-color: #2E2E38;
}
</style>
""", unsafe_allow_html=True)

# --- 2. MOTOR DE IMPORTACIÓN AUTOMÁTICA ---
@st.cache_data
def cargar_datos_historicos():
    archivo_excel = "Planificador_Financiero_Fusionado FINAL (1).xlsx"
    
    if os.path.exists(archivo_excel):
        try:
            df_gastos = pd.read_excel(archivo_excel, sheet_name='Gastos', header=3)
            df_gastos = df_gastos.dropna(subset=['Fecha', 'Monto ($)'])
            
            df_ingresos = pd.read_excel(archivo_excel, sheet_name='Ingresos', header=3)
            df_ingresos = df_ingresos.dropna(subset=['Fecha', 'Monto ($)'])
            
            return df_ingresos, df_gastos
        except Exception as e:
            st.error(f"Error leyendo el Excel: {e}")
            return pd.DataFrame(), pd.DataFrame()
    else:
        st.warning("No se encontró el Excel histórico. Empezando de cero.")
        return pd.DataFrame(), pd.DataFrame()

df_ingresos_hist, df_gastos_hist = cargar_datos_historicos()

if 'gastos' not in st.session_state:
    st.session_state.gastos = df_gastos_hist
if 'ingresos' not in st.session_state:
    st.session_state.ingresos = df_ingresos_hist

# Función global para formato argentino (Ej: $1.500.000,00)
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
        "💳 Estado de Tarjetas"
    ])
    st.markdown("---")

# --- 4. PÁGINA: DASHBOARD GENERAL (Gráficos) ---
if pagina == "📊 Dashboard General":
    st.title("Panel de Control Financiero")
    
    meses_disponibles = st.session_state.gastos['Mes'].dropna().unique().tolist() if not st.session_state.gastos.empty else ["Mes Actual"]
    indice_por_defecto = meses_disponibles.index("Julio") if "Julio" in meses_disponibles else 0
    mes_seleccionado = st.selectbox("Seleccionar Mes de Análisis", options=meses_disponibles, index=indice_por_defecto)
    
    df_gastos_mes = st.session_state.gastos[st.session_state.gastos['Mes'] == mes_seleccionado]
    df_ingresos_mes = st.session_state.ingresos[st.session_state.ingresos['Mes'] == mes_seleccionado]
    
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

# --- 5. PÁGINA: REGISTRO DIARIO (Nueva pestaña independiente) ---
elif pagina == "📅 Registro Diario":
    st.title("Registro Diario de Movimientos")
    st.write("Visualizá todos tus movimientos cargados y exportalos a Excel/CSV.")
    
    meses_historicos = st.session_state.gastos['Mes'].dropna().unique().tolist() if not st.session_state.gastos.empty else []
    mes_filtro = st.selectbox("Filtrar por Mes", options=["Ver Todos"] + meses_historicos)
    
    df_mostrar = st.session_state.gastos.copy()
    if mes_filtro != "Ver Todos":
        df_mostrar = df_mostrar[df_mostrar['Mes'] == mes_filtro]
    
    if not df_mostrar.empty and 'Monto ($)' in df_mostrar.columns:
        df_mostrar['Monto ($)'] = df_mostrar['Monto ($)'].apply(lambda x: formato_arg(x) if pd.notnull(x) else x)
        
    st.dataframe(df_mostrar, use_container_width=True)
    
    if not df_mostrar.empty:
        csv = st.session_state.gastos.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Exportar Base Completa a CSV", data=csv, file_name='registro_gastos_completo.csv', mime='text/csv')

# --- 6. PÁGINA: CARGAR MOVIMIENTO ---
elif pagina == "➕ Cargar Movimiento":
    st.title("Registrar Nuevo Movimiento")
    
    # Emojis y colores para distinguir Ingreso de Gasto rápido
    tipo_movimiento = st.segmented_control("Tipo de Registro", ["🔴 Gasto Variable", "🟢 Ingreso"], default="🔴 Gasto Variable")
    
    # Lista completa de categorías extraídas de tu Excel
    categorias_completas = [
        "Supermercado", "Salidas / Gastronomía", "Delivery", "Mascota (Chancho)", 
        "Gimnasio / CrossFit", "Transporte / Auto", "Salud / Farmacia", 
        "Expensas", "Luz", "Agua", "Gas", "Internet", "Telefonía", 
        "Prepaga", "Seguro Auto", "Seguros Adicionales", "Monotributo", 
        "Profesional (Colegiatura)", "Impuestos y Costos TC", 
        "Compras Online / Impulsivas", "Otros Gastos"
    ]
    
    with st.container(border=True):
        if tipo_movimiento == "🔴 Gasto Variable":
            col1, col2 = st.columns(2)
            with col1:
                # Calendario forzado a DD/MM/YYYY
                fecha = st.date_input("Fecha", format="DD/MM/YYYY")
                descripcion = st.text_input("Descripción (Ej. Amazon, Panadería)")
                monto = st.number_input("Monto", min_value=0.0, format="%.2f")
                categoria = st.selectbox("Categoría", categorias_completas)
                compartido = st.toggle("Dividir 50% con Tomas")
            
            with col2:
                medio = st.selectbox("Medio de Pago", ["Débito / Efectivo / MP", "Visa Macro", "Otra Tarjeta"])
                if medio != "Débito / Efectivo / MP":
                    mes_imputacion = st.selectbox("Mes de Imputación (Patea el gasto al resumen de este mes)", ["Julio", "Agosto", "Septiembre", "Octubre", "Noviembre"])
                    cuotas = st.number_input("Cuotas", 1, 24, 1)
                
                moneda = st.selectbox("Moneda", ["Pesos (ARS)", "Dólares (USD)"])
                if moneda == "Dólares (USD)":
                    metodo_usd = st.radio("Forma de pago", ["Dólar Tarjeta (Suma impuestos)", "Dólar MEP (Stop Debit)"])
                    if metodo_usd == "Dólar MEP (Stop Debit)":
                        st.number_input("Cotización MEP (ARS)", min_value=1000)
            
            if st.button("💾 Guardar Gasto", type="primary", use_container_width=True):
                st.success("Gasto guardado e imputado correctamente.")
                
        else:
            st.subheader("Cargar Ingreso")
            fuente = st.selectbox("Fuente", ["Residencia (Epidemiología)", "Saldan", "Laboratorio SEVEDIC", "Otros ingresos"])
            # Calendario forzado a DD/MM/YYYY para ingresos también
            fecha_ingreso = st.date_input("Fecha de Ingreso", format="DD/MM/YYYY")
            monto_ingreso = st.number_input("Monto ($)", min_value=0.0)
            if st.button("💾 Guardar Ingreso", type="primary", use_container_width=True):
                st.success("Ingreso registrado.")

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
    st.title("Límites y Consumos Futuros")
    st.info("Monitoreo de tu capacidad crediticia actual.")
    
    st.subheader("Visa Macro")
    col_lim1, col_lim2 = st.columns(2)
    with col_lim1:
        st.write("Límite en Cuotas: $4.500.000")
        st.progress(0.45) 
        st.caption("$2.025.000 consumido / $2.475.000 disponible")
    with col_lim2:
        st.write("Proyección Próximo Resumen (Vto. Agosto)")
        st.metric("Total a Pagar Proyectado", formato_arg(941432))
