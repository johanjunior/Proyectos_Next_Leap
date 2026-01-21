import streamlit as st
import pandas as pd
from datetime import date

from modules import login, clientes, renovaciones, cartera

DATA_PATH = "sabana_cartera_renovaciones_200cols.csv"  # ajusta en tu proyecto
BASE_PAGOS = "https://optimoconsultores.com/pagos/"    # placeholder MVP

st.set_page_config(
    page_title="MVP Aseguradora | Cartera & Renovaciones",
    page_icon="📊",
    layout="wide"
)

@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Normalizaciones mínimas (fechas)
    for c in ["fecha_inicio_vigencia", "fecha_fin_vigencia", "fecha_venc_factura",
              "fecha_factura", "fecha_ultimo_pago", "promesa_pago_fecha", "fecha_renovacion_estimada"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # Derivado: link de pago (si no existe)
    if "link_pago" not in df.columns and {"id_cliente", "id_poliza", "valor_en_mora"}.issubset(df.columns):
        df["link_pago"] = (
            BASE_PAGOS
            + "?id_cliente=" + df["id_cliente"].astype(str)
            + "&id_poliza=" + df["id_poliza"].astype(str)
            + "&valor=" + df["valor_en_mora"].fillna(0).astype(int).astype(str)
        )

    return df

def init_session():
    st.session_state.setdefault("auth", False)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("role", None)
    st.session_state.setdefault("page", "login")

    # dataset compartido
    if "df" not in st.session_state:
        st.session_state["df"] = load_data(DATA_PATH)

def logout():
    st.session_state["auth"] = False
    st.session_state["user"] = None
    st.session_state["role"] = None
    st.session_state["page"] = "login"
    st.rerun()

def sidebar():
    st.sidebar.title("Aseguradora MVP")

    if st.session_state["auth"]:
        st.sidebar.caption(f"👤 {st.session_state['user']} | Rol: {st.session_state['role']}")
        st.sidebar.divider()

        page = st.sidebar.radio("Módulos", ["Clientes", "Renovaciones", "Cartera"])
        st.session_state["page"] = page.lower()

        st.sidebar.button("Cerrar sesión", on_click=logout)
    else:
        st.session_state["page"] = "login"

def router():
    df = st.session_state["df"]

    if st.session_state["page"] == "login":
        login.render()
    elif st.session_state["page"] == "clientes":
        clientes.render(df)
    elif st.session_state["page"] == "renovaciones":
        renovaciones.render(df)
    elif st.session_state["page"] == "cartera":
        cartera.render(df)
    else:
        login.render()

def main():
    init_session()
    sidebar()
    router()

if __name__ == "__main__":
    main()
