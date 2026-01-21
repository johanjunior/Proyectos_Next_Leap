import streamlit as st
import pandas as pd

def render(df: pd.DataFrame):
    st.title("♻️ Renovaciones")

    ventana = st.selectbox("Ventana", ["<= 30 días", "<= 15 días", "<= 7 días"])
    limite = 30 if ventana == "<= 30 días" else 15 if ventana == "<= 15 días" else 7

    view = df.copy()
    view = view[view["dias_para_vencimiento"].fillna(9999) <= limite]
    view = view[view["renovable"].astype(str).str.lower().isin(["true","1","si","sí","yes"]) | view["renovable"].isna()]

    cols = [c for c in [
        "numero_poliza","nombre_cliente","producto","plan",
        "fecha_fin_vigencia","dias_para_vencimiento","semáforo_vencimiento",
        "estado_renovacion","fecha_renovacion_estimada",
        "email_cliente","telefono_cliente","consentimiento_email","consentimiento_whatsapp"
    ] if c in view.columns]

    st.dataframe(view[cols].sort_values("dias_para_vencimiento"), use_container_width=True, height=420)

    st.divider()
    st.subheader("Notificación (preview)")

    if len(view) == 0:
        st.info("No hay renovaciones en esta ventana.")
        return

    pol = st.selectbox("Selecciona póliza", view["numero_poliza"].astype(str).tolist())
    row = view[view["numero_poliza"].astype(str) == str(pol)].iloc[0]

    canal = st.selectbox("Canal", ["Email", "WhatsApp"])
    permitido = bool(row.get("consentimiento_email")) if canal == "Email" else bool(row.get("consentimiento_whatsapp"))

    msg = (
        f"Hola {row.get('nombre_cliente')}, tu póliza {row.get('numero_poliza')} "
        f"({row.get('producto')} - {row.get('plan')}) vence el {row.get('fecha_fin_vigencia')}. "
        f"Faltan {int(row.get('dias_para_vencimiento') or 0)} días. "
        f"¿Deseas que gestionemos tu renovación?"
    )

    st.text_area("Mensaje", msg, height=140)

    if not permitido:
        st.warning("Este canal no tiene consentimiento en la sábana. (En MVP puedes simular, en prod debe bloquearse).")

    if st.button("Marcar como notificado (MVP)"):
        st.success("Marcado (simulado). En fase 2 se registra en log + envío real.")
