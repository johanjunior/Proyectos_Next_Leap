"""
Módulo de trazabilidad para visualizar logs de notificaciones
"""
import streamlit as st
import pandas as pd
from modules.notificaciones import obtener_logs_notificaciones

def render(df: pd.DataFrame = None):
    st.title("📋 Trazabilidad de Notificaciones")
    
    # Filtros
    col1, col2, col3, col4 = st.columns(4)
    
    tipo_filtro = col1.selectbox(
        "Tipo",
        ["Todos", "Cartera", "Renovación"],
        key="filtro_tipo"
    )
    
    canal_filtro = col2.selectbox(
        "Canal",
        ["Todos", "Email", "WhatsApp"],
        key="filtro_canal"
    )
    
    estado_filtro = col3.selectbox(
        "Estado",
        ["Todos", "Enviado", "Fallido", "Bloqueado"],
        key="filtro_estado"
    )
    
    limite = col4.number_input("Límite de registros", min_value=10, max_value=1000, value=100, step=10)
    
    # Obtener logs
    df_logs = obtener_logs_notificaciones(limite=limite)
    
    if df_logs.empty:
        st.info("No hay registros de notificaciones aún.")
        return
    
    # Aplicar filtros
    view = df_logs.copy()
    
    if tipo_filtro != "Todos":
        tipo_map = {"Cartera": "cartera", "Renovación": "renovacion"}
        tipo_buscado = tipo_map.get(tipo_filtro, tipo_filtro.lower())
        # Comparación case-insensitive y normalizada
        view = view[view["tipo"].astype(str).str.lower().str.strip() == tipo_buscado.lower()]
    
    if canal_filtro != "Todos":
        canal_map = {"Email": "email", "WhatsApp": "whatsapp"}
        canal_buscado = canal_map.get(canal_filtro, canal_filtro.lower())
        # Comparación case-insensitive y normalizada
        view = view[view["canal"].astype(str).str.lower().str.strip() == canal_buscado.lower()]
    
    if estado_filtro != "Todos":
        estado_map = {"Enviado": "enviado", "Fallido": "fallido", "Bloqueado": "bloqueado"}
        estado_buscado = estado_map.get(estado_filtro, estado_filtro.lower())
        # Comparación case-insensitive y normalizada
        view = view[view["estado"].astype(str).str.lower().str.strip() == estado_buscado.lower()]
    
    # Métricas
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    
    total = len(view)
    enviados = len(view[view["estado"] == "enviado"])
    fallidos = len(view[view["estado"] == "fallido"])
    bloqueados = len(view[view["estado"] == "bloqueado"])
    
    col1.metric("Total", total)
    col2.metric("Enviados", enviados, delta=f"{(enviados/total*100) if total > 0 else 0:.1f}%")
    col3.metric("Fallidos", fallidos, delta=f"{(fallidos/total*100) if total > 0 else 0:.1f}%")
    col4.metric("Bloqueados", bloqueados, delta=f"{(bloqueados/total*100) if total > 0 else 0:.1f}%")
    
    st.divider()
    
    # Tabla de logs
    if len(view) == 0:
        st.info("No hay registros que coincidan con los filtros.")
        return
    
    # Preparar datos para visualización más amigable
    view_display = view.copy()
    
    # Agregar información del cliente desde el DataFrame principal
    if df is not None and "id_cliente" in view_display.columns:
        # Crear un DataFrame con la información del cliente (tomar el primero si hay duplicados)
        df_clientes = df[["id_cliente", "nombre_cliente", "documento_cliente"]].drop_duplicates(subset=["id_cliente"])
        
        # Convertir id_cliente a string para hacer el merge
        view_display["id_cliente_str"] = view_display["id_cliente"].astype(str)
        df_clientes["id_cliente_str"] = df_clientes["id_cliente"].astype(str)
        
        # Hacer merge para obtener nombre y documento
        view_display = view_display.merge(
            df_clientes[["id_cliente_str", "nombre_cliente", "documento_cliente"]],
            on="id_cliente_str",
            how="left"
        )
        
        # Limpiar columna temporal
        view_display = view_display.drop(columns=["id_cliente_str"])
    else:
        # Si no hay DataFrame principal, agregar columnas vacías
        view_display["nombre_cliente"] = "N/A"
        view_display["documento_cliente"] = "N/A"
    
    # Formatear timestamp
    if "timestamp" in view_display.columns:
        view_display["Fecha/Hora"] = view_display["timestamp"].apply(
            lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) and isinstance(x, pd.Timestamp) else str(x) if pd.notna(x) else "N/A"
        )
    
    # Formatear tipo con iconos
    if "tipo" in view_display.columns:
        view_display["Tipo"] = view_display["tipo"].apply(
            lambda x: {
                "cartera": "💰 Cartera",
                "renovacion": "♻️ Renovación",
                "general": "📧 General"
            }.get(str(x).lower(), str(x).title())
        )
    
    # Formatear canal con iconos
    if "canal" in view_display.columns:
        view_display["Canal"] = view_display["canal"].apply(
            lambda x: {
                "email": "📧 Email",
                "whatsapp": "💬 WhatsApp"
            }.get(str(x).lower(), str(x).title())
        )
    
    # Formatear estado con iconos y colores
    if "estado" in view_display.columns:
        view_display["Estado"] = view_display["estado"].apply(
            lambda x: {
                "enviado": "✅ Enviado",
                "fallido": "❌ Fallido",
                "bloqueado": "⚠️ Bloqueado"
            }.get(str(x).lower(), str(x).title())
        )
    
    # Renombrar columnas
    rename_map = {
        "destinatario": "Destinatario",
        "id_cliente": "ID Cliente",
        "id_poliza": "ID Póliza",
        "usuario": "Usuario",
        "documento_cliente": "Documento Cliente",
        "nombre_cliente": "Nombre Cliente"
    }
    
    for old, new in rename_map.items():
        if old in view_display.columns:
            view_display[new] = view_display[old]
    
    # Columnas a mostrar (en orden: Fecha/Hora, Documento, Nombre, luego el resto)
    cols_display = [
        "Fecha/Hora", "Documento Cliente", "Nombre Cliente", "Tipo", "Canal", "Estado", "Destinatario",
        "ID Cliente", "ID Póliza", "Usuario"
    ]
    
    cols_available = [c for c in cols_display if c in view_display.columns]
    
    st.dataframe(
        view_display[cols_available],
        use_container_width=True,
        height=400,
        hide_index=True
    )
    
    # Mostrar errores si hay en la vista filtrada
    if "error" in view.columns:
        view_con_error = view[view["error"].notna() & (view["error"] != "")]
        if len(view_con_error) > 0:
            st.caption(f"ℹ️ {len(view_con_error)} registro(s) con errores. Selecciona uno para ver detalles.")
    
    # Búsqueda por cliente
    st.divider()
    st.subheader("📄 Trazabilidad por Cliente")
    
    if df is not None and len(df_logs) > 0:
        # Campo de búsqueda
        busqueda_cliente = st.text_input("🔍 Buscar cliente (nombre o documento)", key="busqueda_cliente_trazabilidad")
        
        if busqueda_cliente:
            busqueda_lower = busqueda_cliente.lower().strip()
            
            # Buscar clientes en el DataFrame original que coincidan
            clientes_coincidentes = df[
                (df["nombre_cliente"].astype(str).str.lower().str.contains(busqueda_lower, na=False)) |
                (df["documento_cliente"].astype(str).str.lower().str.contains(busqueda_lower, na=False))
            ]
            
            if len(clientes_coincidentes) > 0:
                # Obtener IDs de clientes que coinciden
                ids_clientes = clientes_coincidentes["id_cliente"].astype(str).unique()
                
                # Filtrar logs completos por esos IDs de clientes (sin aplicar otros filtros)
                view_cliente = df_logs[df_logs["id_cliente"].astype(str).isin(ids_clientes)]
                
                if len(view_cliente) > 0:
                    st.success(f"✅ Se encontraron {len(view_cliente)} notificación(es) para el cliente")
                    
                    # Mostrar información del cliente
                    cliente_principal = clientes_coincidentes.iloc[0]
                    st.info(f"**Cliente:** {cliente_principal.get('nombre_cliente', 'N/A')} | **Documento:** {cliente_principal.get('documento_cliente', 'N/A')}")
                    
                    # Mostrar todas las notificaciones del cliente
                    for idx, registro in view_cliente.iterrows():
                        with st.expander(
                            f"{registro.get('timestamp', '').strftime('%Y-%m-%d %H:%M:%S') if pd.notna(registro.get('timestamp')) and isinstance(registro.get('timestamp'), pd.Timestamp) else str(registro.get('timestamp', 'N/A'))} | "
                            f"{str(registro.get('tipo', '')).title()} | "
                            f"{str(registro.get('canal', '')).title()} | "
                            f"{str(registro.get('estado', '')).title()}",
                            expanded=False
                        ):
                            # Información General
                            st.markdown("### 📋 Información General")
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.markdown("**📅 Fecha y Hora**")
                                timestamp = registro.get("timestamp", "")
                                if pd.notna(timestamp):
                                    if isinstance(timestamp, pd.Timestamp):
                                        st.write(timestamp.strftime("%Y-%m-%d %H:%M:%S"))
                                    else:
                                        st.write(str(timestamp))
                                else:
                                    st.write("N/A")
                            
                            with col2:
                                st.markdown("**📌 Tipo**")
                                tipo = str(registro.get("tipo", "")).lower().strip()
                                tipo_icon = "💰" if tipo == "cartera" else "♻️" if tipo == "renovacion" else "📧"
                                tipo_display = "Cartera" if tipo == "cartera" else "Renovación" if tipo == "renovacion" else tipo.title()
                                st.write(f"{tipo_icon} {tipo_display}")
                            
                            with col3:
                                st.markdown("**📱 Canal**")
                                canal = str(registro.get("canal", "")).lower().strip()
                                canal_icon = "📧" if canal == "email" else "💬"
                                canal_display = "Email" if canal == "email" else "WhatsApp" if canal == "whatsapp" else canal.title()
                                st.write(f"{canal_icon} {canal_display}")
                            
                            with col4:
                                st.markdown("**✅ Estado**")
                                estado = str(registro.get("estado", "")).lower().strip()
                                if estado == "enviado":
                                    st.success("✅ Enviado")
                                elif estado == "fallido":
                                    st.error("❌ Fallido")
                                elif estado == "bloqueado":
                                    st.warning("⚠️ Bloqueado")
                                else:
                                    st.write(estado.title())
                            
                            st.divider()
                            
                            # Información del Destinatario
                            st.markdown("### 👤 Información del Destinatario")
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.markdown("**📧/📱 Contacto**")
                                destinatario = registro.get("destinatario", "")
                                if destinatario:
                                    st.write(destinatario)
                                else:
                                    st.write("_No disponible_")
                            
                            with col2:
                                st.markdown("**🆔 ID Cliente**")
                                id_cliente = registro.get("id_cliente", "")
                                st.write(id_cliente if id_cliente else "_No disponible_")
                            
                            with col3:
                                st.markdown("**📄 ID Póliza**")
                                id_poliza = registro.get("id_poliza", "")
                                st.write(id_poliza if id_poliza else "_No disponible_")
                            
                            st.divider()
                            
                            # Usuario que envió
                            usuario = registro.get("usuario", "")
                            if usuario:
                                st.markdown(f"**👤 Enviado por:** {usuario}")
                            
                            st.divider()
                            
                            # Mensaje
                            st.markdown("### 💬 Mensaje Enviado")
                            mensaje = registro.get("mensaje", "")
                            if mensaje:
                                st.text_area("", mensaje, height=120, disabled=True, label_visibility="collapsed", key=f"msg_{idx}")
                            else:
                                st.info("_No hay mensaje registrado_")
                            
                            # Error si existe
                            error = registro.get("error")
                            if error and pd.notna(error):
                                st.divider()
                                st.markdown("### ⚠️ Detalles del Error")
                                st.error(error)
                else:
                    st.warning(f"⚠️ No se encontraron notificaciones para el cliente buscado")
            else:
                st.warning("⚠️ No se encontró ningún cliente con ese nombre o documento")
    elif df is None:
        st.info("ℹ️ Para buscar por cliente, el módulo debe recibir el DataFrame de datos")
