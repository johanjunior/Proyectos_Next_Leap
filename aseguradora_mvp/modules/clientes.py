import streamlit as st
import pandas as pd

LIST_COLS = [
    "nombre_cliente","documento_cliente","segmento",
    "numero_poliza","producto","plan","estado_poliza",
    "email_cliente","telefono_cliente",
    "dias_mora","valor_en_mora","estado_pago",
    "fecha_fin_vigencia","dias_para_vencimiento","semáforo_vencimiento","estado_renovacion"
]

def render(df: pd.DataFrame):
    st.title("👥 Clientes")

    # Filtros
    c1, c2, c3 = st.columns(3)
    q = c1.text_input("Buscar (nombre / documento / póliza)")
    estado_poliza = c2.multiselect("Estado póliza", sorted(df["estado_poliza"].dropna().unique().tolist()))
    segmento = c3.multiselect("Segmento", sorted(df["segmento"].dropna().unique().tolist()))

    view = df.copy()

    if q:
        ql = q.lower()
        view = view[
            view["nombre_cliente"].astype(str).str.lower().str.contains(ql, na=False)
            | view["documento_cliente"].astype(str).str.lower().str.contains(ql, na=False)
            | view["numero_poliza"].astype(str).str.lower().str.contains(ql, na=False)
        ]
    if estado_poliza:
        view = view[view["estado_poliza"].isin(estado_poliza)]
    if segmento:
        view = view[view["segmento"].isin(segmento)]

    # Tabla
    cols = [c for c in LIST_COLS if c in view.columns]
    st.dataframe(view[cols], use_container_width=True, height=420)

    # Detalle (ficha)
    st.divider()
    st.subheader("Ficha 360")

    if len(view) == 0:
        st.info("No hay resultados para mostrar ficha.")
        return

    pick = st.selectbox("Selecciona un cliente (por póliza)", view["numero_poliza"].astype(str).tolist())
    row = view[view["numero_poliza"].astype(str) == str(pick)].iloc[0]

    a, b, c = st.columns(3)
    a.metric("Días mora", int(row.get("dias_mora", 0) or 0))
    b.metric("Valor en mora", float(row.get("valor_en_mora", 0) or 0))
    c.metric("Días para vencimiento", int(row.get("dias_para_vencimiento", 0) or 0))

    st.write({
        "Cliente": row.get("nombre_cliente"),
        "Documento": row.get("documento_cliente"),
        "Email": row.get("email_cliente"),
        "Teléfono": row.get("telefono_cliente"),
        "Póliza": row.get("numero_poliza"),
        "Producto": row.get("producto"),
        "Plan": row.get("plan"),
        "Vigencia fin": str(row.get("fecha_fin_vigencia")),
        "Renovación": row.get("estado_renovacion"),
        "Consent Email": row.get("consentimiento_email"),
        "Consent WhatsApp": row.get("consentimiento_whatsapp"),
    })
