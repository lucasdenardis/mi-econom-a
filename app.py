import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Mi Economía | Dashboard", layout="wide", page_icon="💸")

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

# --- 2. CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error("Error de conexión a Supabase. Revisá los Secrets.")
    st.stop()

# --- 3. FUNCIONES DE LECTURA Y ESCRITURA ---
def cargar_datos():
    res_mov = supabase.table("movimientos").select("*").execute()
    df_mov = pd.DataFrame(res_mov.data)
    
    res_tarjetas = supabase.table("tarjetas").select("*").eq("activo", True).execute()
    lista_tarjetas = res_tarjetas.data if res_tarjetas.data else []
    
    return df_mov, lista_tarjetas

df_movimientos, tarjetas_activas = cargar_datos()

def formato_arg(valor):
    try:
        return f"${float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "$0,00"

# --- 4. NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.title("💸 Mi Economía")
    st.markdown("---")
    pagina = st.radio("Menú Principal", [
        "📊 Dashboard General", 
        "➕ Cargar Movimiento",
        "📅 Registro Diario",
        "🔄 Fijos y Automatización", 
        "⚙️ Configurar Tarjetas"
    ], index=1)
    st.markdown("---")

# --- 5. PÁGINAS ---

if pagina == "📊 Dashboard General":
    st.title("Panel de Control Financiero")
    
    if not df_movimientos.empty:
        df_movimientos['monto'] = pd.to_numeric(df_movimientos['monto'], errors='coerce').fillna(0)
        meses_disponibles = df_movimientos['mes_imputacion'].dropna().unique().tolist()
        
        mes_seleccionado = st.selectbox("Seleccionar Mes de Análisis", options=meses_disponibles, index=len(meses_disponibles)-1)
        st.markdown("---")
        
        df_mes = df_movimientos[df_movimientos['mes_imputacion'] == mes_seleccionado]
        
        ingresos_mes = df_mes[df_mes['tipo'] == 'Ingreso']['monto'].sum()
        fijos_mes = df_mes[df_mes['tipo'] == 'Fijo']['monto'].sum()
        variables_mes = df_mes[df_mes['tipo'] == 'Variable']['monto'].sum()
        gastos_totales_mes = fijos_mes + variables_mes
        ahorro_real = ingresos_mes - gastos_totales_mes
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Ingresos Totales", formato_arg(ingresos_mes))
        col2.metric("Gastos Totales", formato_arg(gastos_totales_mes), delta=formato_arg(-gastos_totales_mes), delta_color="inverse")
        col3.metric("Ahorro Real", formato_arg(ahorro_real), delta=f"{(ahorro_real/ingresos_mes*100) if ingresos_mes > 0 else 0:.1f}% del ingreso")
        
        st.markdown("---")
        st.markdown("### 🎯 Análisis y Regla de Presupuesto")
        
        with st.expander("⚙️ Ajustar regla de porcentajes (Ej: 50/30/20)", expanded=True):
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                obj_fijos = st.number_input("% Gastos Fijos (Necesidades)", min_value=0, max_value=100, value=50)
            with col_p2:
                obj_var = st.number_input("% Gastos Variables (Deseos)", min_value=0, max_value=100, value=30)
            with col_p3:
                obj_aho = st.number_input("% Ahorro (Futuro)", min_value=0, max_value=100, value=20)
                
            if (obj_fijos + obj_var + obj_aho) != 100:
                st.warning("⚠️ Los porcentajes deben sumar exactamente 100%.")

        ideal_fijos = ingresos_mes * (obj_fijos / 100)
        ideal_var = ingresos_mes * (obj_var / 100)
        ideal_aho = ingresos_mes * (obj_aho / 100)

        estado_fijos = "✅ Bien" if fijos_mes <= ideal_fijos else "⚠️ Excedido"
        estado_var = "✅ Bien" if variables_mes <= ideal_var else "⚠️ Excedido"
        estado_aho = "✅ Bien" if ahorro_real >= ideal_aho else "🔻 Por debajo"

        data_presupuesto = {
            "Categoría": ["Gastos Fijos", "Gastos Variables", "Ahorro"],
            "Objetivo %": [f"{obj_fijos}%", f"{obj_var}%", f"{obj_aho}%"],
            "Presupuesto Ideal ($)": [formato_arg(ideal_fijos), formato_arg(ideal_var), formato_arg(ideal_aho)],
            "Gasto Real ($)": [formato_arg(fijos_mes), formato_arg(variables_mes), formato_arg(ahorro_real)],
            "Gasto Real %": [
                f"{(fijos_mes/ingresos_mes*100) if ingresos_mes > 0 else 0:.1f}%",
                f"{(variables_mes/ingresos_mes*100) if ingresos_mes > 0 else 0:.1f}%",
                f"{(ahorro_real/ingresos_mes*100) if ingresos_mes > 0 else 0:.1f}%"
            ],
            "Estado": [estado_fijos, estado_var, estado_aho]
        }
        st.dataframe(pd.DataFrame(data_presupuesto), use_container_width=True, hide_index=True)

        st.markdown("---")
        
        st.markdown("### 🗓️ Comparativa Histórica Mes a Mes")
        historico = []
        for m in meses_disponibles:
            df_m = df_movimientos[df_movimientos['mes_imputacion'] == m]
            ing = df_m[df_m['tipo'] == 'Ingreso']['monto'].sum()
            gst = df_m[df_m['tipo'] != 'Ingreso']['monto'].sum()
            ahorro = ing - gst
            porcentaje = (ahorro / ing * 100) if ing > 0 else 0
            
            historico.append({
                "Mes": m,
                "Ingresos": ing,
                "Gastos": gst,
                "Ahorro Real": ahorro,
                "% Ahorrado": f"{porcentaje:.1f}%"
            })
            
        df_hist = pd.DataFrame(historico)
        df_hist['Ingresos'] = df_hist['Ingresos'].apply(formato_arg)
        df_hist['Gastos'] = df_hist['Gastos'].apply(formato_arg)
        df_hist['Ahorro Real'] = df_hist['Ahorro Real'].apply(formato_arg)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)

        st.markdown("---")
        
        st.markdown("### 💳 Estado de Tarjetas (Consumos del Mes)")
        nombres_tarjetas = [t['nombre'] for t in tarjetas_activas]
        if nombres_tarjetas:
            resumen_tarjetas = []
            for t in tarjetas_activas:
                consumo = df_mes[(df_mes['medio_pago'] == t['nombre'])]['monto'].sum()
                limite = t['limite']
                disponible = limite - consumo
                estado = "Crítico" if consumo > limite * 0.8 else "Normal"
                
                resumen_tarjetas.append({
                    "Tarjeta": t['nombre'],
                    "Límite": formato_arg(limite),
                    "Consumido": formato_arg(consumo),
                    "Disponible": formato_arg(disponible),
                    "Estado": estado
                })
            st.dataframe(pd.DataFrame(resumen_tarjetas), use_container_width=True, hide_index=True)
        else:
            st.info("No hay tarjetas configuradas.")
            
    else:
        st.info("Aún no hay movimientos cargados en la base de datos.")

elif pagina == "➕ Cargar Movimiento":
    st.title("Registrar Nuevo Movimiento")
    
    tipo_mov = st.segmented_control("Tipo de Registro", ["🔴 Gasto", "🟢 Ingreso"], default="🔴 Gasto")
    
    with st.container(border=True):
        if tipo_mov == "🔴 Gasto":
            col1, col2 = st.columns(2)
            with col1:
                fecha = st.date_input("Fecha", format="DD/MM/YYYY")
                descripcion = st.text_input("Descripción (Ej. Supermercado, Amazon)")
                monto = st.number_input("Monto ($)", min_value=0.0, format="%.2f", value=None, placeholder="Ej. 15000")
                categoria = st.selectbox("Categoría", [
                    "Supermercado", "Salidas / Gastronomía", "Delivery", "Mascota", 
                    "Gimnasio / CrossFit", "Transporte / Auto", "Salud / Farmacia", 
                    "Expensas", "Luz", "Agua", "Gas", "Internet", "Telefonía", 
                    "Prepaga", "Monotributo", "Profesional (Colegiatura)", 
                    "Compras Online / Impulsivas", "Otros Gastos"
                ])
                comparte = st.toggle("Dividir 50% con Tomas")
            
            with col2:
                metodo_general = st.selectbox("Método de Pago", ["Efectivo / Débito / MP", "Tarjeta de Crédito"])
                
                if metodo_general == "Tarjeta de Crédito":
                    nombres_tarjetas = [t['nombre'] for t in tarjetas_activas]
                    if not nombres_tarjetas:
                        st.warning("⚠️ No tenés tarjetas cargadas. Andá a 'Configurar Tarjetas'.")
                        medio_pago_final = "Tarjeta (Sin definir)"
                    else:
                        medio_pago_final = st.selectbox("Seleccionar Tarjeta", nombres_tarjetas)
                    
                    cuotas = st.number_input("Cuotas", min_value=1, max_value=24, value=1)
                    mes_imputacion = st.selectbox("Mes de Imputación", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=7)
                else:
                    medio_pago_final = "Débito / Efectivo / MP"
                    cuotas = 1
                    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                    mes_imputacion = meses[fecha.month - 1]
                
            if st.button("💾 Guardar Gasto", type="primary", use_container_width=True):
                if monto is None or monto <= 0:
                    st.error("⚠️ Por favor, ingresá un monto válido antes de guardar.")
                else:
                    monto_final = monto / 2 if comparte else monto
                    nuevo_dato = {
                        "fecha": fecha.strftime("%Y-%m-%d"),
                        "tipo": "Variable",
                        "descripcion": descripcion,
                        "monto": monto_final,
                        "categoria": categoria,
                        "comparte_tomas": comparte,
                        "medio_pago": medio_pago_final,
                        "cuotas": cuotas,
                        "mes_imputacion": mes_imputacion
                    }
                    supabase.table("movimientos").insert(nuevo_dato).execute()
                    st.success("¡Gasto guardado con éxito en la nube!")
                    st.rerun()
                
        else:
            st.subheader("Cargar Ingreso")
            fecha_ing = st.date_input("Fecha", format="DD/MM/YYYY")
            fuente = st.selectbox("Fuente", ["Residencia (Epidemiología)", "Laboratorio", "Otros ingresos"])
            monto_ingreso = st.number_input("Monto ($)", min_value=0.0, format="%.2f", value=None, placeholder="Ej. 500000")
            
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_imp_ing = st.selectbox("Mes Imputación", meses, index=fecha_ing.month - 1)
            
            if st.button("💾 Guardar Ingreso", type="primary", use_container_width=True):
                if monto_ingreso is None or monto_ingreso <= 0:
                    st.error("⚠️ Por favor, ingresá un monto válido antes de guardar.")
                else:
                    nuevo_ingreso = {
                        "fecha": fecha_ing.strftime("%Y-%m-%d"),
                        "tipo": "Ingreso",
                        "descripcion": fuente,
                        "monto": monto_ingreso,
                        "categoria": "Ingreso",
                        "comparte_tomas": False,
                        "medio_pago": "Transferencia / Depósito",
                        "cuotas": 1,
                        "mes_imputacion": mes_imp_ing
                    }
                    supabase.table("movimientos").insert(nuevo_ingreso).execute()
                    st.success("¡Ingreso guardado con éxito!")
                    st.rerun()

elif pagina == "📅 Registro Diario":
    st.title("Registro Histórico y Edición")
    st.write("Visualizá, filtrá por mes, y **editá** cualquier celda si te equivocaste (luego presioná Guardar).")
    
    if not df_movimientos.empty:
        df_mostrar = df_movimientos[['id', 'fecha', 'mes_imputacion', 'tipo', 'categoria', 'descripcion', 'monto', 'medio_pago', 'cuotas']].copy()
        
        # --- CORRECCIÓN DE FORMATOS ---
        df_mostrar['fecha'] = pd.to_datetime(df_mostrar['fecha']).dt.date
        df_mostrar['monto'] = pd.to_numeric(df_mostrar['monto'], errors='coerce').fillna(0.0)
        df_mostrar['cuotas'] = pd.to_numeric(df_mostrar['cuotas'], errors='coerce').fillna(1).astype(int)
        
        # Si hay meses viejos en letras o vacíos, los normalizamos automáticamente al formato AAAA-MM basado en la fecha
        def limpiar_mes(row):
            mes_actual_val = str(row['mes_imputacion'])
            if "-" not in mes_actual_val or len(mes_actual_val) != 7:
                try:
                    return pd.to_datetime(row['fecha']).strftime("%Y-%m")
                except:
                    return "2026-08"
            return mes_actual_val

        df_mostrar['mes_imputacion'] = df_mostrar.apply(limpiar_mes, axis=1)
        
        # Lista de opciones limpias y ordenadas en formato AAAA-MM
        meses_unicos_ordenados = sorted(df_mostrar['mes_imputacion'].dropna().unique().tolist())
        opciones_filtro = ["Ver Todos"] + meses_unicos_ordenados
        
        mes_actual_str = datetime.date.today().strftime("%Y-%m")
        indice_defecto = opciones_filtro.index(mes_actual_str) if mes_actual_str in opciones_filtro else (len(opciones_filtro) - 1 if len(opciones_filtro) > 1 else 0)
        
        mes_filtro = st.selectbox("Filtrar por Mes", options=opciones_filtro, index=indice_defecto)
        
        st.markdown("---")
        
        if mes_filtro != "Ver Todos":
            df_mostrar = df_mostrar[df_mostrar['mes_imputacion'] == mes_filtro]
            
        df_mostrar = df_mostrar.sort_values(by='fecha', ascending=False).reset_index(drop=True)
        
        # Editor de Datos con opciones estrictas en formato AAAA-MM
        edited_df = st.data_editor(
            df_mostrar,
            use_container_width=True,
            hide_index=True,
            disabled=["id"],
            column_config={
                "id": None,
                "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "mes_imputacion": st.column_config.SelectboxColumn("Mes (AAAA-MM)", options=meses_unicos_ordenados),
                "tipo": st.column_config.SelectboxColumn("Tipo", options=["Variable", "Fijo", "Ingreso"]),
                "categoria": st.column_config.TextColumn("Categoría"),
                "descripcion": st.column_config.TextColumn("Descripción"),
                "monto": st.column_config.NumberColumn("Monto ($)", format="%.2f"),
                "medio_pago": st.column_config.TextColumn("Medio de Pago"),
                "cuotas": st.column_config.NumberColumn("Cuotas", min_value=1, max_value=24)
            }
        )
        
        if st.button("💾 Guardar Cambios Editados", type="primary"):
            cambios = 0
            for index in edited_df.index:
                fila_edit = edited_df.loc[index]
                fila_orig = df_mostrar.loc[index]
                
                if not fila_edit.equals(fila_orig):
                    datos_update = {
                        "fecha": str(fila_edit['fecha']),
                        "mes_imputacion": str(fila_edit['mes_imputacion']),
                        "tipo": fila_edit['tipo'],
                        "categoria": fila_edit['categoria'],
                        "descripcion": fila_edit['descripcion'],
                        "monto": float(fila_edit['monto']),
                        "medio_pago": fila_edit['medio_pago'],
                        "cuotas": int(fila_edit['cuotas'])
                    }
                    supabase.table("movimientos").update(datos_update).eq("id", int(fila_edit['id'])).execute()
                    cambios += 1
            
            if cambios > 0:
                st.success(f"¡Se actualizaron {cambios} registros correctamente!")
                st.rerun()
            else:
                st.info("No se detectaron modificaciones.")
    else:
        st.info("No hay datos para mostrar.")

elif pagina == "🔄 Fijos y Automatización":
    st.title("Confirmación de Gastos Fijos")
    st.write("Confirmá el monto real de tus obligaciones para que impacten en el balance.")
    
    fijos_estimados = [
        {"nombre": "Expensas", "cat": "Expensas", "estimado": 120000},
        {"nombre": "EPEC (Luz)", "cat": "Luz", "estimado": 31622},
        {"nombre": "Gimnasio / CrossFit", "cat": "Gimnasio / CrossFit", "estimado": 35000},
        {"nombre": "Prepaga", "cat": "Prepaga", "estimado": 218514},
        {"nombre": "Internet", "cat": "Internet", "estimado": 25000},
        {"nombre": "Seguro Auto", "cat": "Transporte / Auto", "estimado": 45000}
    ]
    
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_actual = meses[datetime.date.today().month - 1]
    mes_fijo = st.selectbox("¿A qué mes imputar los pagos?", meses, index=datetime.date.today().month - 1)
    
    st.markdown("---")
    
    for f in fijos_estimados:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.markdown(f"**{f['nombre']}**")
            with c2:
                monto_real = st.number_input(f"Monto Final", value=float(f['estimado']), key=f['nombre'])
            with c3:
                st.write("") 
                if st.button("🟢 Pagar y Guardar", key=f"btn_{f['nombre']}", use_container_width=True):
                    nuevo_fijo = {
                        "fecha": datetime.date.today().strftime("%Y-%m-%d"),
                        "tipo": "Fijo",
                        "descripcion": f['nombre'],
                        "monto": monto_real,
                        "categoria": f['cat'],
                        "comparte_tomas": False,
                        "medio_pago": "Débito / Efectivo / MP",
                        "cuotas": 1,
                        "mes_imputacion": mes_fijo
                    }
                    supabase.table("movimientos").insert(nuevo_fijo).execute()
                    st.success(f"¡{f['nombre']} guardado en {mes_fijo}!")

elif pagina == "⚙️ Configurar Tarjetas":
    st.title("Gestión de Tarjetas")
    
    st.subheader("➕ Agregar Nueva Tarjeta")
    with st.form("form_nueva_tarjeta", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_nombre = st.text_input("Nombre (Ej. Visa Galicia)")
        with col2:
            nuevo_limite = st.number_input("Límite de Compra ($)", min_value=0.0, step=100000.0, value=None, placeholder="Ej. 1000000")
            
        btn_agregar = st.form_submit_button("Guardar Tarjeta", type="primary")
        if btn_agregar:
            if nuevo_nombre and nuevo_limite is not None:
                supabase.table("tarjetas").insert({"nombre": nuevo_nombre, "limite": nuevo_limite, "activo": True}).execute()
                st.success("¡Tarjeta agregada!")
                st.rerun()
            else:
                st.error("⚠️ Completá el nombre y el límite de la tarjeta.")
            
    st.markdown("---")
    
    st.subheader("💳 Tarjetas Activas")
    if tarjetas_activas:
        for t in tarjetas_activas:
            with st.container(border=True):
                col_t1, col_t2, col_t3 = st.columns([2, 2, 1])
                with col_t1:
                    st.write(f"**{t['nombre']}**")
                with col_t2:
                    st.write(f"Límite: {formato_arg(t['limite'])}")
                with col_t3:
                    if st.button("🗑️ Borrar", key=f"del_{t['id']}"):
                        supabase.table("tarjetas").delete().eq("id", t['id']).execute()
                        st.rerun()
    else:
        st.info("No hay tarjetas guardadas. Agregá una desde el panel superior.")
