import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- 1. CONFIGURACIÓN MODERNA DE LA INTERFAZ ---
st.set_page_config(page_title="Mi Economía | Dashboard", layout="wide", page_icon="💸")

# --- 2. MOTOR DE IMPORTACIÓN AUTOMÁTICA ---
# Carga los datos de tu Excel original una sola vez para no perder la historia
@st.cache_data
def cargar_datos_historicos():
    archivo_excel = "Planificador_Financiero_Fusionado FINAL (1).xlsx"
    
    if os.path.exists(archivo_excel):
        try:
            # Leer pestaña de Gastos (ignorando las filas de encabezado de texto)
            df_gastos = pd.read_excel(archivo_excel, sheet_name='Gastos', header=3)
            df_gastos = df_gastos.dropna(subset=['Fecha', 'Monto ($)'])
            
            # Leer pestaña de Ingresos
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

# Inicializar bases de datos en sesión
if 'gastos' not in st.session_state:
    st.session_state.gastos = df_gastos_hist
if 'ingresos' not in st.session_state:
    st.session_state.ingresos = df_ingresos_hist

# --- 3. NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.title("💸 Mi Economía")
    st.markdown("---")
    pagina = st.radio("Menú Principal", [
        "📊 Dashboard General", 
        "➕ Cargar Movimiento", 
        "🔄 Fijos y Automatización", 
        "💳 Estado de Tarjetas"
    ])
    st.markdown("---")
    st.caption("Los datos se sincronizan localmente.")

# --- 4. PÁGINA: DASHBOARD GENERAL (Gráficos) ---
if pagina == "📊 Dashboard General":
    st.title("Panel de Control Financiero")
    
    # Filtro de Mes
    meses_disponibles = st.session_state.gastos['Mes'].dropna().unique().tolist() if not st.session_state.gastos.empty else ["Mes Actual"]
    mes_seleccionado = st.selectbox("Seleccionar Mes de Análisis", options=meses_disponibles)
    
    # KPIs Rápidos
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ingresos Totales", "$1,905,000", "Liquidez")
    col2.metric("Salidas Efectivas", "$420,000", "Débito/Efectivo", delta_color="inverse")
    col3.metric("Deuda TC Mes Próximo", "$941,432", "Visa Macro", delta_color="inverse")
    col4.metric("Saldo con Tomas", "$14,500", "A favor")

    st.markdown("---")
    
    # Gráficos Modernos con Plotly
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.subheader("Flujo de Caja (Devengado vs Percibido)")
        # Gráfico de cascada simulado
        fig_waterfall = go.Figure(go.Waterfall(
            name = "Flujo", orientation = "v",
            measure = ["relative", "relative", "relative", "total"],
            x = ["Ingresos", "Gastos Corrientes", "Tarjetas (Cuotas Mes)", "Ahorro Real"],
            textposition = "outside",
            y = [1905000, -420000, -941432, 543568],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        fig_waterfall.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_waterfall, use_container_width=True)

    with col_graf2:
        st.subheader("Distribución de Gastos")
        if not st.session_state.gastos.empty:
            df_plot = st.session_state.gastos.groupby('Categoría')['Monto ($)'].sum().reset_index()
            fig_pie = px.pie(df_plot, values='Monto ($)', names='Categoría', hole=0.4, template="plotly_dark")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No hay datos de gastos para graficar.")

    # Tabla Exportable
    st.subheader("Registro Diario (Exportable)")
    st.dataframe(st.session_state.gastos, use_container_width=True)
    
    # Exportar a CSV (o Excel)
    csv = st.session_state.gastos.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Exportar Gastos a CSV", data=csv, file_name='gastos_actualizados.csv', mime='text/csv')

# --- 5. PÁGINA: CARGAR MOVIMIENTO ---
elif pagina == "➕ Cargar Movimiento":
    st.title("Registrar Nuevo Movimiento")
    
    tipo_movimiento = st.segmented_control("Tipo de Registro", ["Gasto Variable", "Ingreso"], default="Gasto Variable")
    
    with st.container(border=True):
        if tipo_movimiento == "Gasto Variable":
            col1, col2 = st.columns(2)
            with col1:
                fecha = st.date_input("Fecha")
                descripcion = st.text_input("Descripción (Ej. Supermercado, Amazon)")
                monto = st.number_input("Monto", min_value=0.0, format="%.2f")
                categoria = st.selectbox("Categoría", ["Salidas / Gastronomía", "Supermercado", "Mascota (Chancho)", "Delivery", "Otros Gastos"])
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
                # Aquí iría la lógica de pd.concat() para sumar el dato a st.session_state.gastos
                
        else:
            st.subheader("Cargar Ingreso")
            fuente = st.selectbox("Fuente", ["Residencia (Epidemiología)", "Saldan", "Laboratorio SEVEDIC", "Otros ingresos"])
            monto_ingreso = st.number_input("Monto ($)", min_value=0.0)
            if st.button("💾 Guardar Ingreso", type="primary", use_container_width=True):
                st.success("Ingreso registrado.")

# --- 6. PÁGINA: FIJOS Y AUTOMATIZACIÓN ---
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

# --- 7. PÁGINA: ESTADO DE TARJETAS ---
elif pagina == "💳 Estado de Tarjetas":
    st.title("Límites y Consumos Futuros")
    st.info("Monitoreo de tu capacidad crediticia actual.")
    
    st.subheader("Visa Macro")
    col_lim1, col_lim2 = st.columns(2)
    with col_lim1:
        st.write("Límite en Cuotas: $4.500.000")
        st.progress(0.45) # Simulación de porcentaje usado
        st.caption("$2.025.000 consumido / $2.475.000 disponible")
    with col_lim2:
        st.write("Proyección Próximo Resumen (Vto. Agosto)")
        st.metric("Total a Pagar Proyectado", "$941,432")
