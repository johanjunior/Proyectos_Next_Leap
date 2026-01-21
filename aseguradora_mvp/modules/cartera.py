import streamlit as st
import pandas as pd

def render(df: pd.DataFrame):
    st.title("💰 Cartera")

    seg = st.selectbox("Segmento de mora", ["1–15 días", "16–45 días", ">45 días"])
    if seg == "1–15 días":
        view = df[(df["dias_mora"].fillna(0) >= 1) & (df["dias_mora"].fillna(0) <= 15)]
    elif seg == "16–45 días":
        view = df[(df["dias_mora"].fillna(0) >= 16) & (df["dias_mora"].fillna(0) <= 45)]
    else:
        view = df[df["dias_mora"].fillna(0) > 45]

    view = view[view["valor_en_mora"].fillna(0) > 0]

    cols = [c for c in [
        "numero_poliza","nombre_cliente","documento_cliente",
        "dias_mora","valor_en_mora","fecha_venc_factura",
        "estado_pago","fecha_ultimo_pago",
        "promesa_pago_fecha","promesa_pago_valor",
        "canal_pago_preferido","forma_pago","frecuencia_pago",
        "email_cliente","telefono_cliente","consentimiento_email","consentimiento_whatsapp",
        "link_pago"
    ] if c in view.columns]

    st.dataframe(view[cols].sort_values(["dias_mora","valor_en_mora"], ascending=[False, False]),
                 use_container_width=True, height=420)

    st.divider()
    st.subheader("Notificación (preview)")

    if len(view) == 0:
        st.info("No hay registros en este segmento.")
        return

    pol = st.selectbox("Selecciona póliza", view["numero_poliza"].astype(str).tolist())
    row = view[view["numero_poliza"].astype(str) == str(pol)].iloc[0]

    msg = (
        f"Hola {row.get('nombre_cliente')}, registramos un saldo en mora por {row.get('valor_en_mora')}. "
        f"Fecha límite: {row.get('fecha_venc_factura')}. "
        f"Puedes pagar aquí: {row.get('link_pago', '[link_pago]')}."
    )

    st.text_area("Mensaje", msg, height=140)

    if st.button("Marcar como notificado (MVP)"):
        st.success("Marcado (simulado). En fase 2 se registra en log + envío real.")
