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
    q = c1.text_input("Buscar (nombre / documento)")
    estado_poliza = c2.multiselect("Estado póliza", sorted(df["estado_poliza"].dropna().unique().tolist()))
    segmento = c3.multiselect("Segmento", sorted(df["segmento"].dropna().unique().tolist()))

    view = df.copy()

    if q:
        ql = q.lower()
        view = view[
            view["nombre_cliente"].astype(str).str.lower().str.contains(ql, na=False)
            | view["documento_cliente"].astype(str).str.lower().str.contains(ql, na=False)
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

    # Búsqueda por nombre o documento
    busqueda_ficha = st.text_input("🔍 Buscar cliente para ver ficha (nombre o documento)", key="busqueda_ficha_cliente")
    
    if busqueda_ficha:
        busqueda_lower = busqueda_ficha.lower().strip()
        view_ficha = view[
            (view["nombre_cliente"].astype(str).str.lower().str.contains(busqueda_lower, na=False)) |
            (view["documento_cliente"].astype(str).str.lower().str.contains(busqueda_lower, na=False))
        ]
        
        if len(view_ficha) == 0:
            st.warning("⚠️ No se encontró ningún cliente con ese nombre o documento en los resultados filtrados.")
            return
        
        # Si hay múltiples coincidencias, mostrar selector
        if len(view_ficha) > 1:
            st.info(f"Se encontraron {len(view_ficha)} cliente(s) coincidente(s). Selecciona uno:")
            opciones_ficha = []
            for idx, row in view_ficha.iterrows():
                nombre = row.get("nombre_cliente", "N/A")
                documento = row.get("documento_cliente", "N/A")
                poliza = row.get("numero_poliza", "N/A")
                opciones_ficha.append({
                    "idx": idx,
                    "label": f"{nombre} | Doc: {documento} | Póliza: {poliza}"
                })
            
            seleccion_ficha = st.selectbox(
                "Selecciona el cliente",
                range(len(opciones_ficha)),
                format_func=lambda x: opciones_ficha[x]["label"],
                key="select_cliente_ficha"
            )
            row = view_ficha.iloc[seleccion_ficha]
        else:
            # Solo una coincidencia, mostrarla directamente
            row = view_ficha.iloc[0]
            st.success(f"✅ Cliente encontrado: {row.get('nombre_cliente', 'N/A')}")
    else:
        st.info("💡 Ingresa el nombre o documento del cliente para ver su ficha 360°")
        return

    a, b, c = st.columns(3)
    a.metric("Días mora", int(row.get("dias_mora", 0) or 0))
    b.metric("Valor en mora", f"${float(row.get('valor_en_mora', 0) or 0):,.0f}")
    c.metric("Días para vencimiento", int(row.get("dias_para_vencimiento", 0) or 0))

    st.divider()
    
    # Información del Cliente
    st.markdown("### 👤 Información del Cliente")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**👤 Nombre**")
        st.write(row.get("nombre_cliente", "_No disponible_"))
        
        st.markdown("**🆔 Documento**")
        st.write(row.get("documento_cliente", "_No disponible_"))
        
        st.markdown("**📧 Email**")
        email = row.get("email_cliente", "")
        if email and not pd.isna(email):
            st.write(email)
        else:
            st.write("_No disponible_")
    
    with col2:
        st.markdown("**📱 Teléfono**")
        telefono = row.get("telefono_cliente", "")
        if telefono and not pd.isna(telefono):
            st.write(telefono)
        else:
            st.write("_No disponible_")
        
        st.markdown("**📊 Segmento**")
        st.write(row.get("segmento", "_No disponible_"))
        
        st.markdown("**📄 Estado Póliza**")
        st.write(row.get("estado_poliza", "_No disponible_"))
    
    st.divider()
    
    # Información de la Póliza
    st.markdown("### 📄 Información de la Póliza")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🔢 Número de Póliza**")
        st.write(row.get("numero_poliza", "_No disponible_"))
        
        st.markdown("**📦 Producto**")
        st.write(row.get("producto", "_No disponible_"))
    
    with col2:
        st.markdown("**📋 Plan**")
        st.write(row.get("plan", "_No disponible_"))
        
        st.markdown("**📅 Fecha Fin Vigencia**")
        fecha_fin = row.get("fecha_fin_vigencia", "")
        if fecha_fin and not pd.isna(fecha_fin):
            if isinstance(fecha_fin, pd.Timestamp):
                st.write(fecha_fin.strftime("%Y-%m-%d"))
            else:
                st.write(str(fecha_fin))
        else:
            st.write("_No disponible_")
    
    with col3:
        st.markdown("**♻️ Estado Renovación**")
        estado_renov = row.get("estado_renovacion", "")
        if estado_renov and not pd.isna(estado_renov):
            st.write(estado_renov)
        else:
            st.write("_No disponible_")
        
        st.markdown("**💰 Estado Pago**")
        estado_pago = row.get("estado_pago", "")
        if estado_pago and not pd.isna(estado_pago):
            st.write(estado_pago)
        else:
            st.write("_No disponible_")
    
    st.divider()
    
    # Consentimientos
    st.markdown("### ✅ Consentimientos de Comunicación")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📧 Consentimiento Email**")
        consent_email = row.get("consentimiento_email", "")
        if consent_email and not pd.isna(consent_email):
            consent_str = str(consent_email).lower().strip()
            if consent_str in ["sí", "si", "yes", "true", "1", "1.0", "s", "y"]:
                st.success("✅ Sí")
            else:
                st.error("❌ No")
        else:
            st.warning("⚠️ No definido")
    
    with col2:
        st.markdown("**💬 Consentimiento WhatsApp**")
        consent_whatsapp = row.get("consentimiento_whatsapp", "")
        if consent_whatsapp and not pd.isna(consent_whatsapp):
            consent_str = str(consent_whatsapp).lower().strip()
            if consent_str in ["sí", "si", "yes", "true", "1", "1.0", "s", "y"]:
                st.success("✅ Sí")
            else:
                st.error("❌ No")
        else:
            st.warning("⚠️ No definido")
