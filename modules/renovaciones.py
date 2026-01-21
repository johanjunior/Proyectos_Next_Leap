import streamlit as st
import pandas as pd
from modules.notificaciones import enviar_notificacion_renovacion, enviar_notificaciones_renovacion_masivo

def render(df: pd.DataFrame):
    st.title("♻️ Renovaciones")

    ventana = st.selectbox("Ventana", ["<= 30 días", "<= 15 días", "<= 7 días"])
    limite = 30 if ventana == "<= 30 días" else 15 if ventana == "<= 15 días" else 7

    view = df.copy()
    # Filtrar: incluir pólizas dentro de la ventana (pueden estar vencidas o próximas a vencer)
    # Incluir pólizas vencidas hasta cierto límite (ej: -30 días) y próximas a vencer
    view = view[
        (view["dias_para_vencimiento"].fillna(9999) <= limite) &  # Dentro de la ventana (puede ser negativo)
        (view["renovable"].astype(str).str.lower().isin(["true","1","si","sí","yes"]) | view["renovable"].isna())
    ]

    cols = [c for c in [
        "numero_poliza","nombre_cliente","producto","plan",
        "fecha_fin_vigencia","dias_para_vencimiento","semáforo_vencimiento",
        "estado_renovacion","fecha_renovacion_estimada",
        "email_cliente","telefono_cliente","consentimiento_email","consentimiento_whatsapp"
    ] if c in view.columns]

    st.dataframe(view[cols].sort_values("dias_para_vencimiento"), use_container_width=True, height=420)

    st.divider()
    st.subheader("📤 Envío Masivo de Notificaciones de Renovación")

    if len(view) == 0:
        st.info("No hay renovaciones en esta ventana.")
        return

    # Seleccionar canal
    canal = st.selectbox("Canal de notificación", ["Email", "WhatsApp"])
    canal_lower = canal.lower()

    # Función helper para convertir consentimiento a booleano
    def tiene_consentimiento(valor):
        if pd.isna(valor):
            return False
        valor_str = str(valor).lower().strip()
        return valor_str in ["sí", "si", "yes", "true", "1", "1.0", "s", "y"]
    
    # Filtrar por consentimiento y disponibilidad de contacto
    if canal == "Email":
        view_filtrado = view[
            (view["consentimiento_email"].apply(tiene_consentimiento)) &
            (view["email_cliente"].notna()) &
            (view["email_cliente"] != "")
        ].copy()
    else:  # WhatsApp
        view_filtrado = view[
            (view["consentimiento_whatsapp"].apply(tiene_consentimiento)) &
            (view["telefono_cliente"].notna()) &
            (view["telefono_cliente"] != "")
        ].copy()

    # Identificar clientes sin consentimiento en ningún canal
    view_sin_consentimiento = view[
        ~(
            (view["consentimiento_email"].apply(tiene_consentimiento) & view["email_cliente"].notna() & (view["email_cliente"] != "")) |
            (view["consentimiento_whatsapp"].apply(tiene_consentimiento) & view["telefono_cliente"].notna() & (view["telefono_cliente"] != ""))
        )
    ].copy()
    
    # Estadísticas previas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total en ventana", len(view))
    col2.metric("Con consentimiento", len(view_filtrado))
    col3.metric("Sin consentimiento", len(view) - len(view_filtrado))
    col4.metric("Listos para enviar", len(view_filtrado))

    # Mostrar tabla de clientes sin consentimiento en ningún canal
    if len(view_sin_consentimiento) > 0:
        st.divider()
        st.subheader("⚠️ Clientes sin Autorización en Ningún Canal")
        st.info(f"Se encontraron {len(view_sin_consentimiento)} cliente(s) sin consentimiento en ningún canal (Email ni WhatsApp).")
        
        cols_sin_consent = ["numero_poliza", "nombre_cliente", "documento_cliente", 
                           "email_cliente", "telefono_cliente", 
                           "consentimiento_email", "consentimiento_whatsapp"]
        cols_available = [c for c in cols_sin_consent if c in view_sin_consentimiento.columns]
        
        st.dataframe(
            view_sin_consentimiento[cols_available],
            use_container_width=True,
            height=min(300, len(view_sin_consentimiento) * 35 + 50),
            hide_index=True
        )

    if len(view_filtrado) == 0:
        st.warning("⚠️ No hay clientes con consentimiento y contacto disponible para este canal.")
        st.info("💡 Asegúrate de que los clientes tengan consentimiento y contacto configurado.")
        return

    # Vista previa de mensajes personalizados
    with st.expander("👁️ Vista previa de mensajes personalizados (primeros 3)"):
        for idx, row in view_filtrado.head(3).iterrows():
            nombre = row.get("nombre_cliente", "Cliente")
            num_poliza = row.get("numero_poliza", "")
            producto = row.get("producto", "")
            plan = row.get("plan", "")
            fecha_fin = row.get("fecha_fin_vigencia", "")
            dias_venc = int(row.get("dias_para_vencimiento", 0) or 0)
            destinatario = row.get("email_cliente", "") if canal == "Email" else row.get("telefono_cliente", "")

            # Validar días para vencimiento y ajustar mensaje
            if dias_venc < 0:
                msg_dias = f"Tu póliza venció hace {abs(dias_venc)} días"
                msg_renovacion = "Es importante que gestionemos tu renovación lo antes posible."
            elif dias_venc == 0:
                msg_dias = "Tu póliza vence hoy"
                msg_renovacion = "¿Deseas que gestionemos tu renovación?"
            else:
                msg_dias = f"Faltan {dias_venc} días"
                msg_renovacion = "¿Deseas que gestionemos tu renovación?"

            msg = (
                f"Hola {nombre}, tu póliza {num_poliza} "
                f"({producto} - {plan}) vence el {fecha_fin}. "
                f"{msg_dias}. "
                f"{msg_renovacion}"
            )

            st.markdown(f"**📧 Para: {destinatario}**")
            st.text_area("", msg, height=80, disabled=True, key=f"preview_renov_{idx}")

    # Botón de envío masivo
    st.divider()
    
    col1, col2 = st.columns([1, 3])
    
    resultados = None
    
    with col1:
        if st.button("📤 Enviar a Todos", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Callback para actualizar progreso
            def update_progress(current, total):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Enviando {current} de {total} notificaciones...")
            
            # Enviar notificaciones
            resultados = enviar_notificaciones_renovacion_masivo(
                view_filtrado, 
                canal=canal_lower,
                progress_callback=update_progress
            )
            
            # Completar barra de progreso
            progress_bar.progress(1.0)
            status_text.text("✅ Envío completado")
    
    with col2:
        if st.button("🔄 Recargar", use_container_width=True):
            st.rerun()
    
    # Mostrar resultados fuera de las columnas para que ocupen ancho completo
    if resultados is not None:
        st.divider()
        st.subheader("📊 Resumen del Envío Masivo")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("✅ Enviados", resultados["enviados"], 
                   delta=f"{(resultados['enviados']/resultados['total']*100):.1f}%")
        col2.metric("❌ Fallidos", resultados["fallidos"],
                   delta=f"{(resultados['fallidos']/resultados['total']*100):.1f}%")
        col3.metric("⚠️ Bloqueados", resultados["bloqueados"],
                   delta=f"{(resultados['bloqueados']/resultados['total']*100):.1f}%")
        col4.metric("📭 Sin destinatario", resultados["sin_destinatario"],
                   delta=f"{(resultados['sin_destinatario']/resultados['total']*100):.1f}%")
        
        # Tabla de detalles
        if resultados["detalles"]:
            st.divider()
            st.subheader("📋 Detalle por Cliente")
            
            df_resultados = pd.DataFrame(resultados["detalles"])
            
            # Formatear estado con iconos
            df_resultados["Estado"] = df_resultados["estado"].apply(
                lambda x: {
                    "enviado": "✅ Enviado",
                    "fallido": "❌ Fallido",
                    "bloqueado": "⚠️ Bloqueado",
                    "sin_destinatario": "📭 Sin destinatario"
                }.get(x, x)
            )
            
            cols_display = ["id_poliza", "nombre", "Estado"]
            if "destinatario" in df_resultados.columns:
                cols_display.append("destinatario")
            if "error" in df_resultados.columns:
                cols_display.append("error")
            
            st.dataframe(
                df_resultados[cols_display],
                use_container_width=True,
                hide_index=True
            )
        
        if resultados["enviados"] > 0:
            st.success(f"✅ {resultados['enviados']} notificación(es) enviada(s) exitosamente")
            st.info("💡 Todas las notificaciones han sido registradas en el sistema de trazabilidad")
