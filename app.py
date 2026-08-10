
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
from pathlib import Path

st.set_page_config(page_title="Finanzas Personales", page_icon="💰", layout="wide")

st.markdown("""
<style>
.stApp{background:#0b0f14}
section[data-testid="stSidebar"]{background:#111821;border-right:1px solid #26313d}
section[data-testid="stSidebar"] .stButton>button{width:100%;min-height:55px;margin:5px 0;border-radius:14px;border:1px solid #2b3744;background:#18212b;color:#fff;font-weight:700}
.kpi{background:linear-gradient(145deg,#151d26,#10161d);border:1px solid #293542;border-radius:18px;padding:17px;min-height:112px}
.kt{color:#91a0b0;font-size:13px}.kv{color:#f5f7fa;font-size:24px;font-weight:800;margin-top:7px}
@media(max-width:768px){.block-container{padding:.75rem .65rem 2rem}.kv{font-size:20px}}
</style>
""", unsafe_allow_html=True)

EXCEL_NAME = "Planificador_Financiero_Fusionado FINAL (1).xlsx"
MONTHS = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}

# Catálogo exacto recuperado del Excel
EXCEL_CATEGORIES = ['Compras Online / Impulsivas', 'Impuestos y Costos TC', 'Educación / Cursos', 'Delivery', 'Prepaga', 'Transporte / Auto', 'Salidas / Gastronomía', 'Otros Gastos', 'Luz', 'Seguros Adicionales', 'Telefonía', 'Agua', 'Gas', 'Profesional (Colegiatura)', 'Suscripciones', 'Supermercado', 'Tarjeta', 'Monotributo', 'Internet']
EXCEL_SOURCES = ['Residencia (Epidemiología)', 'Centro de Castración de Saldán', 'Laboratorio SEVEDIC', 'Otros ingresos variables', 'CDC/Hospital', 'Laboratorio', 'CDC', 'Saldan', 'Residencia']
EXCEL_PAYMENT_METHODS = ['Efectivo/MP', 'Tarjeta de Crédito']
EXCEL_FIXED_CATEGORIES = []

def money(v):
    try: x=float(v or 0)
    except: x=0
    return "$ " + f"{x:,.2f}".replace(",","X").replace(".",",").replace("X",".")

def parse_amount(v):
    if isinstance(v,(int,float)): return float(v)
    s=str(v).strip().replace("$","").replace(" ","")
    if not s: return 0.0
    if "," in s and "." in s:
        s=s.replace(".","").replace(",",".") if s.rfind(",")>s.rfind(".") else s.replace(",","")
    elif "," in s: s=s.replace(".","").replace(",",".")
    return float(s)

def iso(v):
    if pd.isna(v) or v is None or str(v).strip()=="": return None
    if isinstance(v,(pd.Timestamp,datetime,date)):
        return pd.Timestamp(v).strftime("%Y-%m-%d")
    for f in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y"):
        try:return datetime.strptime(str(v)[:10],f).strftime("%Y-%m-%d")
        except:pass
    return None

def dmy(v):
    try:return datetime.strptime(str(v)[:10],"%Y-%m-%d").strftime("%d/%m/%Y")
    except:return ""

def month_label(m):
    try:y,mm=m.split("-"); return f"{MONTHS[int(mm)]} {y}"
    except:return m

@st.cache_resource
def db():
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
sb=db()

@st.cache_data(ttl=20)
def table(name):
    r=sb.table(name).select("*").execute()
    return pd.DataFrame(r.data or [])

def refresh(): st.cache_data.clear(); st.rerun()
def ins(t,row): sb.table(t).insert(row).execute(); refresh()
def upd(t,rid,row): sb.table(t).update(row).eq("id",rid).execute(); refresh()
def dele(t,rid): sb.table(t).delete().eq("id",rid).execute(); refresh()

def movements():
    df=table("movimientos")
    if df.empty:return pd.DataFrame(columns=["id","fecha","tipo","descripcion","monto","categoria","comparte_tomas","medio_pago","cuotas","mes_imputacion","moneda","cotizacion_mep","monto_pesos"])
    df["fecha"]=df["fecha"].astype(str).str[:10]
    for c in ["monto","monto_pesos","cotizacion_mep"]: df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)
    return df

def active_values(t):
    df=table(t)
    if df.empty:return []
    return df.loc[df["activo"]==True,"nombre"].astype(str).tolist()

def ensure_excel_import():
    # Importación idempotente: solo cuando movimientos está vacío.
    try:
        if len(table("movimientos"))>0:return
        p=Path(EXCEL_NAME)
        if not p.exists():return
        gg=pd.read_excel(p,sheet_name="Gastos",header=3)
        ii=pd.read_excel(p,sheet_name="Ingresos",header=3)
        rows=[]
        for _,r in gg.iterrows():
            f=iso(r.get("Fecha"))
            if not f:continue
            try:m=parse_amount(r.get("Monto ($)",0))
            except:continue
            if m==0:continue
            rows.append({"fecha":f,"tipo":"Gasto Fijo" if str(r.get("Tipo","")).strip().lower()=="fijo" else "Gasto Variable",
                         "descripcion":str(r.get("Descripción","") if pd.notna(r.get("Descripción")) else ""),
                         "monto":m,"categoria":str(r.get("Categoría","Otros Gastos")),
                         "comparte_tomas":False,"medio_pago":str(r.get("Medio de Pago","")),
                         "cuotas":1,"mes_imputacion":f[:7],"moneda":"ARS","cotizacion_mep":0,"monto_pesos":m})
        for _,r in ii.iterrows():
            f=iso(r.get("Fecha"))
            if not f:continue
            try:m=parse_amount(r.get("Monto ($)",0))
            except:continue
            if m==0:continue
            rows.append({"fecha":f,"tipo":"Ingreso","descripcion":str(r.get("Detalle","") if pd.notna(r.get("Detalle")) else ""),
                         "monto":m,"categoria":str(r.get("Fuente","Otros ingresos variables")),
                         "comparte_tomas":False,"medio_pago":"Transferencia","cuotas":1,
                         "mes_imputacion":f[:7],"moneda":"ARS","cotizacion_mep":0,"monto_pesos":m})
        for j in range(0,len(rows),100): sb.table("movimientos").insert(rows[j:j+100]).execute()
    except Exception as e:
        st.sidebar.warning(f"Importación Excel: {e}")

ensure_excel_import()

if "page" not in st.session_state: st.session_state.page="➕ Cargar Movimiento"
pages=["📊 Dashboard General","➕ Cargar Movimiento","📅 Registro Diario","🔄 Fijos y Automatización","💳 Estado de Tarjetas","⚙️ Configuración"]
with st.sidebar:
    st.markdown("## 💰 Finanzas")
    st.caption("Sincronización en la nube")
    for p in pages:
        if st.button(p,key="nav_"+p):
            st.session_state.page=p; st.rerun()
    st.divider()
    st.caption("Inicio rápido: Cargar Movimiento")

def page_load():
    st.title("➕ Cargar Movimiento")
    typ=st.segmented_control("Tipo",["🔴 Gasto Variable","🟢 Ingreso"],default="🔴 Gasto Variable")
    is_income=typ.startswith("🟢")
    cats=active_values("categorias") or EXCEL_CATEGORIES
    payments=active_values("medios_pago") or EXCEL_PAYMENT_METHODS
    with st.form("new",clear_on_submit=True):
        a,b=st.columns(2)
        with a:
            f=st.date_input("Fecha",date.today(),format="DD/MM/YYYY")
            desc=st.text_input("Descripción / Detalle")
            amt=st.text_input("Monto",placeholder="1.500.000,00")
        with b:
            cat=st.selectbox("Categoría / Fuente",cats)
            medio=st.selectbox("Medio de pago",payments)
            share=st.toggle("Dividir 50% con Tomas",disabled=is_income)
        c,d,e=st.columns(3)
        with c: cur=st.selectbox("Moneda",["ARS - Pesos","USD - Dólares"])
        with d: cuotas=st.number_input("Cuotas",1,60,1)
        with e: mep=st.number_input("Dólar MEP",0.0,step=1.0,disabled=cur.startswith("ARS"))
        mes=st.text_input("Mes de imputación",f.strftime("%Y-%m"))
        ok=st.form_submit_button("💾 GUARDAR Y SINCRONIZAR",use_container_width=True)
    if ok:
        try:
            m=parse_amount(amt)
            if m<=0: raise ValueError("El monto debe ser mayor que cero.")
            pesos=m if cur.startswith("ARS") else m*mep
            if cur.startswith("USD") and mep<=0: raise ValueError("Ingresá la cotización MEP.")
            if share and not is_income: pesos*=.5
            ins("movimientos",{"fecha":f.strftime("%Y-%m-%d"),"tipo":"Ingreso" if is_income else "Gasto Variable",
                "descripcion":desc.strip(),"monto":m,"categoria":cat,"comparte_tomas":bool(share),
                "medio_pago":medio,"cuotas":int(cuotas),"mes_imputacion":mes[:7],
                "moneda":"USD" if cur.startswith("USD") else "ARS","cotizacion_mep":float(mep),"monto_pesos":float(pesos)})
        except Exception as e: st.error(str(e))

def page_dash():
    st.title("📊 Dashboard General")
    df=movements()
    if df.empty: st.info("No hay movimientos."); return
    months=sorted(df.fecha.str[:7].unique(),reverse=True)
    default="2026-08" if "2026-08" in months else (date.today().strftime("%Y-%m") if date.today().strftime("%Y-%m") in months else months[0])
    m=st.selectbox("Mes",months,index=months.index(default),format_func=month_label)
    x=df[df.fecha.str[:7]==m]
    inc=x.loc[x.tipo=="Ingreso","monto_pesos"].sum()
    exp=x.loc[x.tipo!="Ingreso","monto_pesos"].sum()
    bal=inc-exp
    cs=st.columns(4)
    for col,title,val in zip(cs,["Ingresos","Gastos","Balance","Movimientos"],[inc,exp,bal,len(x)]):
        col.markdown(f'<div class="kpi"><div class="kt">{title}</div><div class="kv">{money(val) if title!="Movimientos" else int(val)}</div></div>',unsafe_allow_html=True)
    a,b=st.columns(2)
    with a:
        fig=go.Figure(go.Waterfall(x=["Ingresos","Gastos","Balance"],y=[inc,-exp,bal],measure=["relative","relative","total"],text=[money(inc),money(-exp),money(bal)],textposition="outside"))
        fig.update_layout(template="plotly_dark",height=400,margin=dict(l=10,r=10,t=25,b=10))
        st.plotly_chart(fig,use_container_width=True)
    with b:
        q=x[x.tipo!="Ingreso"].groupby("categoria",as_index=False).monto_pesos.sum()
        if not q.empty:
            fig=px.pie(q,names="categoria",values="monto_pesos",hole=.48)
            fig.update_layout(template="plotly_dark",height=400,margin=dict(l=10,r=10,t=25,b=10))
            st.plotly_chart(fig,use_container_width=True)

def page_daily():
    st.title("📅 Registro Diario")
    df=movements()
    if df.empty:st.info("No hay movimientos.");return
    months=sorted(df.fecha.str[:7].unique(),reverse=True)
    default="2026-08" if "2026-08" in months else months[0]
    m=st.selectbox("Mes",months,index=months.index(default),format_func=month_label)
    x=df[df.fecha.str[:7]==m].sort_values(["fecha","id"],ascending=[False,False])
    st.download_button("⬇️ Exportar base completa a CSV",df.to_csv(index=False).encode("utf-8-sig"),f"movimientos_{date.today()}.csv","text/csv",use_container_width=True)
    for _,r in x.iterrows():
        rid=int(r.id)
        with st.expander(f"{dmy(r.fecha)} · {r.descripcion or r.categoria} · {money(r.monto_pesos)}"):
            with st.form(f"edit{rid}"):
                a,b=st.columns(2)
                with a:
                    nd=st.date_input("Fecha",datetime.strptime(r.fecha,"%Y-%m-%d").date(),format="DD/MM/YYYY")
                    ndesc=st.text_input("Descripción",str(r.descripcion or ""))
                    namt=st.text_input("Monto",str(r.monto))
                with b:
                    opts=["Gasto Variable","Gasto Fijo","Ingreso"]
                    nt=st.selectbox("Tipo",opts,index=opts.index(r.tipo) if r.tipo in opts else 0)
                    cats=list(dict.fromkeys(active_values("categorias")+EXCEL_CATEGORIES+[str(r.categoria)]))
                    nc=st.selectbox("Categoría / Fuente",cats,index=cats.index(str(r.categoria)))
                    pays=list(dict.fromkeys(active_values("medios_pago")+EXCEL_PAYMENT_METHODS+[str(r.medio_pago)]))
                    npay=st.selectbox("Medio de pago",pays,index=pays.index(str(r.medio_pago)))
                c,d,e=st.columns(3)
                with c:nq=st.number_input("Cuotas",1,60,int(r.cuotas or 1))
                with d:nm=st.text_input("Mes imputación",str(r.mes_imputacion or r.fecha[:7]))
                with e:ncur=st.selectbox("Moneda",["ARS","USD"],index=0 if str(r.moneda)=="ARS" else 1)
                share=st.toggle("50% con Tomas",bool(r.comparte_tomas),disabled=nt=="Ingreso")
                mep=st.number_input("Cotización MEP",0.0,value=float(r.cotizacion_mep or 0),disabled=ncur=="ARS")
                save=st.form_submit_button("💾 Guardar cambios",use_container_width=True)
            if save:
                mval=parse_amount(namt); pesos=mval if ncur=="ARS" else mval*mep
                if ncur=="USD" and mep<=0:st.error("Ingresá MEP.")
                else:
                    if share and nt!="Ingreso":pesos*=.5
                    upd("movimientos",rid,{"fecha":nd.strftime("%Y-%m-%d"),"tipo":nt,"descripcion":ndesc.strip(),"monto":mval,"categoria":nc,"comparte_tomas":bool(share),"medio_pago":npay,"cuotas":int(nq),"mes_imputacion":nm[:7],"moneda":ncur,"cotizacion_mep":mep,"monto_pesos":pesos})
            if st.button("🗑️ Borrar movimiento",key=f"del{rid}",use_container_width=True):
                dele("movimientos",rid)

def page_fixed():
    st.title("🔄 Fijos y Automatización")
    df=table("gastos_fijos")
    if df.empty:st.info("No hay gastos fijos.");return
    for _,r in df.iterrows():
        rid=int(r.id)
        with st.container(border=True):
            a,b,c=st.columns([2,1,1])
            a.markdown(f"**{r.nombre}**")
            b.write(money(r.monto))
            if c.button("↩️ Desconfirmar" if r.confirmado_mes else "✅ Confirmar",key=f"fix{rid}"):
                upd("gastos_fijos",rid,{"confirmado_mes":not bool(r.confirmado_mes)})
            st.caption("🟢 Activo" if r.activo else "⚪ Inactivo")

def page_cards():
    st.title("💳 Estado de Tarjetas")
    c=table("tarjetas"); m=movements()
    if c.empty:st.info("Agregá tarjetas desde Configuración.");return
    for _,r in c[c.activo==True].iterrows():
        limit=float(r.limite or 0)
        spent=m[(m.medio_pago==r.nombre)&(m.tipo!="Ingreso")].monto_pesos.sum() if not m.empty else 0
        pct=spent/limit if limit else 0
        with st.container(border=True):
            st.markdown(f"### 💳 {r.nombre}")
            a,b,d=st.columns(3);a.metric("Límite",money(limit));b.metric("Consumido",money(spent));d.metric("Disponible",money(max(limit-spent,0)))
            st.progress(min(pct,1));st.caption(f"{pct*100:.1f}% utilizado")

def page_config():
    st.title("⚙️ Configuración")
    t1,t2,t3,t4=st.tabs(["💳 Tarjetas","🏷️ Categorías","🏠 Gastos Fijos","💵 Medios de Pago"])
    with t1:
        df=table("tarjetas")
        for _,r in df.iterrows():
            rid=int(r.id)
            with st.form(f"card{rid}"):
                a,b,c=st.columns(3);n=a.text_input("Nombre",r.nombre);lim=b.number_input("Límite",0.0,value=float(r.limite or 0));act=c.toggle("Activa",bool(r.activo))
                if st.form_submit_button("Guardar"):upd("tarjetas",rid,{"nombre":n.strip(),"limite":lim,"activo":act})
        with st.form("newcard"):
            n=st.text_input("Nueva tarjeta");lim=st.number_input("Nuevo límite",0.0)
            if st.form_submit_button("➕ Agregar") and n.strip():ins("tarjetas",{"nombre":n.strip(),"limite":lim,"activo":True})
    with t2:
        df=table("categorias")
        for _,r in df.iterrows():
            rid=int(r.id)
            with st.form(f"cat{rid}"):
                a,b=st.columns([3,1]);n=a.text_input("Nombre",r.nombre);act=b.toggle("Activa",bool(r.activo))
                if st.form_submit_button("Guardar"):upd("categorias",rid,{"nombre":n.strip(),"activo":act})
        with st.form("newcat"):
            n=st.text_input("Nueva categoría")
            if st.form_submit_button("➕ Agregar") and n.strip():ins("categorias",{"nombre":n.strip(),"activo":True})
    with t3:
        df=table("gastos_fijos")
        for _,r in df.iterrows():
            rid=int(r.id)
            with st.form(f"fixcfg{rid}"):
                a,b,c=st.columns(3);n=a.text_input("Nombre",r.nombre);amt=b.number_input("Monto",0.0,value=float(r.monto or 0));day=c.number_input("Vencimiento",1,31,int(r.dia_vencimiento or 10));act=st.toggle("Activo",bool(r.activo))
                if st.form_submit_button("Guardar"):upd("gastos_fijos",rid,{"nombre":n.strip(),"monto":amt,"dia_vencimiento":day,"activo":act})
        with st.form("newfix"):
            a,b,c=st.columns(3);n=a.text_input("Nuevo gasto fijo");amt=b.number_input("Monto",0.0);day=c.number_input("Día",1,31,10)
            if st.form_submit_button("➕ Agregar") and n.strip():ins("gastos_fijos",{"nombre":n.strip(),"monto":amt,"dia_vencimiento":day,"activo":True,"confirmado_mes":False})
    with t4:
        df=table("medios_pago")
        for _,r in df.iterrows():
            rid=int(r.id)
            with st.form(f"pay{rid}"):
                a,b=st.columns([3,1]);n=a.text_input("Nombre",r.nombre);act=b.toggle("Activo",bool(r.activo))
                if st.form_submit_button("Guardar"):upd("medios_pago",rid,{"nombre":n.strip(),"activo":act})
        with st.form("newpay"):
            n=st.text_input("Nuevo medio")
            if st.form_submit_button("➕ Agregar") and n.strip():ins("medios_pago",{"nombre":n.strip(),"activo":True})

if st.session_state.page=="📊 Dashboard General":page_dash()
elif st.session_state.page=="➕ Cargar Movimiento":page_load()
elif st.session_state.page=="📅 Registro Diario":page_daily()
elif st.session_state.page=="🔄 Fijos y Automatización":page_fixed()
elif st.session_state.page=="💳 Estado de Tarjetas":page_cards()
else:page_config()
