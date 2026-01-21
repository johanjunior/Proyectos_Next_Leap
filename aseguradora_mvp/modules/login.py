import streamlit as st

def render():
    st.title("🔐 Login")

    with st.form("login"):
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        role = st.selectbox("Rol", ["Admin", "Cartera", "Renovaciones", "Auditor"])
        ok = st.form_submit_button("Ingresar")

    if ok:
        if user and password:
            st.session_state["auth"] = True
            st.session_state["user"] = user
            st.session_state["role"] = role
            st.session_state["page"] = "clientes"
            st.rerun()
        else:
            st.error("Ingresa usuario y contraseña.")
