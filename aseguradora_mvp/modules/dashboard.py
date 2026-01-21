"""
Módulo ejecutivo: Dashboard consolidado de Cartera y Renovaciones
"""
import streamlit as st
import pandas as pd
import plotly.express as px

def render(df: pd.DataFrame):
    st.title("📊 Tablero de Visualización")
    st.caption("Vista ejecutiva consolidada de Cartera y Renovaciones")
    
    # ========== SECCIÓN RENOVACIONES ==========
    st.header("♻️ Renovaciones")
    
    # Selector de ventana
    ventana = st.selectbox("Ventana de Renovación", ["<= 30 días", "<= 15 días", "<= 7 días"], key="ventana_renov")
    limite = 30 if ventana == "<= 30 días" else 15 if ventana == "<= 15 días" else 7
    
    # Filtrar renovaciones (dentro de la ventana)
    view_renov = df.copy()
    view_renov = view_renov[
        (view_renov["dias_para_vencimiento"].fillna(9999) <= limite) &
        (view_renov["renovable"].astype(str).str.lower().isin(["true","1","si","sí","yes"]) | view_renov["renovable"].isna())
    ]
    
    # Contar registros excluidos de la ventana (para agregar como "verde")
    view_excluidos = df.copy()
    view_excluidos = view_excluidos[
        (view_excluidos["dias_para_vencimiento"].fillna(9999) > limite) &
        (view_excluidos["renovable"].astype(str).str.lower().isin(["true","1","si","sí","yes"]) | view_excluidos["renovable"].isna())
    ]
    cantidad_excluidos = len(view_excluidos)
    
    # Visualización: Funnel por Semáforo
    if "semáforo_vencimiento" in view_renov.columns:
        semaforo_counts = view_renov["semáforo_vencimiento"].value_counts().sort_index()
        
        df_semaforo = None
        if len(semaforo_counts) > 0 or cantidad_excluidos > 0:
            # Crear DataFrame con los semáforos de la ventana
            if len(semaforo_counts) > 0:
                df_semaforo = pd.DataFrame({
                    "Semáforo": semaforo_counts.index,
                    "Cantidad": semaforo_counts.values
                })
            else:
                df_semaforo = pd.DataFrame(columns=["Semáforo", "Cantidad"])
            
            # Agregar categoría "verde" con los excluidos
            if cantidad_excluidos > 0:
                nueva_fila = pd.DataFrame({
                    "Semáforo": ["Verde"],
                    "Cantidad": [cantidad_excluidos]
                })
                df_semaforo = pd.concat([df_semaforo, nueva_fila], ignore_index=True)
            
            def orden_urgencia(sem):
                sem_str = str(sem).lower()
                if "rojo" in sem_str or "🔴" in str(sem) or "red" in sem_str:
                    return 1
                elif "amarillo" in sem_str or "🟡" in str(sem) or "yellow" in sem_str:
                    return 2
                elif "verde" in sem_str or "🟢" in str(sem) or "green" in sem_str:
                    return 3
                else:
                    return 4
            
            df_semaforo["orden"] = df_semaforo["Semáforo"].apply(orden_urgencia)
            df_semaforo = df_semaforo.sort_values(["orden", "Cantidad"], ascending=[True, False])
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if df_semaforo is not None and len(df_semaforo) > 0:
                color_map = {}
                for sem in df_semaforo["Semáforo"]:
                    sem_lower = str(sem).lower()
                    if "rojo" in sem_lower or "🔴" in str(sem):
                        color_map[sem] = "#EF4444"
                    elif "amarillo" in sem_lower or "🟡" in str(sem):
                        color_map[sem] = "#F59E0B"
                    elif "verde" in sem_lower or "🟢" in str(sem):
                        color_map[sem] = "#10B981"
                    else:
                        color_map[sem] = "#6B7280"
                
                fig_renov = px.bar(
                    df_semaforo,
                    x="Cantidad",
                    y="Semáforo",
                    orientation='h',
                    title=f"Renovaciones por Urgencia ({ventana})",
                    color="Semáforo",
                    color_discrete_map=color_map,
                    text="Cantidad"
                )
                # Calcular altura dinámica basada en número de categorías
                altura_renov = max(250, len(df_semaforo) * 80)
                fig_renov.update_layout(
                    showlegend=False,
                    height=altura_renov,
                    yaxis={'categoryorder': 'array', 'categoryarray': df_semaforo["Semáforo"].tolist()},
                    margin=dict(t=50, b=50, l=50, r=50)  # Márgenes para que no se corte
                )
                fig_renov.update_traces(textposition='outside')
                st.plotly_chart(fig_renov, use_container_width=True)
            else:
                st.info("No hay datos de semáforo disponibles")
        
        with col2:
            # Total incluye tanto los de la ventana como los excluidos
            total_renov = len(view_renov) + cantidad_excluidos
            st.metric("Total a Renovar", total_renov)
            
            if df_semaforo is not None and len(df_semaforo) > 0:
                st.markdown("**Por Urgencia:**")
                for _, row in df_semaforo.iterrows():
                    sem = row["Semáforo"]
                    count = row["Cantidad"]
                    porcentaje = (count / total_renov * 100) if total_renov > 0 else 0
                    sem_lower = str(sem).lower()
                    badge = "🔴" if ("rojo" in sem_lower or "🔴" in str(sem)) else "🟡" if ("amarillo" in sem_lower or "🟡" in str(sem)) else "🟢" if ("verde" in sem_lower or "🟢" in str(sem)) else "⚪"
                    st.write(f"{badge} **{sem}**: {count} ({porcentaje:.1f}%)")
    
    st.divider()
    
    # ========== SECCIÓN CARTERA ==========
    st.header("💰 Cartera en Mora")
    
    # Selector de segmento
    seg = st.selectbox("Segmento de Mora", ["1–15 días", "16–45 días", ">45 días"], key="seg_cartera")
    
    # Filtrar cartera
    if seg == "1–15 días":
        view_cartera = df[
            (df["dias_mora"].fillna(0) >= 1) & 
            (df["dias_mora"].fillna(0) <= 15) &
            (df["valor_en_mora"].fillna(0) > 0)
        ]
    elif seg == "16–45 días":
        view_cartera = df[
            (df["dias_mora"].fillna(0) >= 16) & 
            (df["dias_mora"].fillna(0) <= 45) &
            (df["valor_en_mora"].fillna(0) > 0)
        ]
    else:
        view_cartera = df[
            (df["dias_mora"].fillna(0) > 45) &
            (df["valor_en_mora"].fillna(0) > 0)
        ]
    
    # Métricas principales
    total_clientes = len(view_cartera)
    monto_total_mora = view_cartera["valor_en_mora"].fillna(0).sum()
    monto_promedio_mora = view_cartera["valor_en_mora"].fillna(0).mean() if total_clientes > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Clientes", f"{total_clientes:,}")
    col2.metric("Monto Total", f"${monto_total_mora:,.0f}")
    col3.metric("Promedio", f"${monto_promedio_mora:,.0f}")
    
    # Gráficas
    if total_clientes > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            # Histograma
            valores_mora = view_cartera["valor_en_mora"].fillna(0)
            fig_hist = px.histogram(
                valores_mora,
                nbins=20,
                title=f"Distribución de Valores ({seg})",
                labels={"value": "Valor en Mora ($)", "count": "Clientes"},
                color_discrete_sequence=["#EF4444"]
            )
            fig_hist.update_layout(
                height=350,
                showlegend=False,
                margin=dict(t=50, b=50, l=50, r=50)  # Márgenes para que no se corte
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Gráfica por rangos
            bins = [0, 100000, 500000, 1000000, 5000000, float('inf')]
            labels = ["$0-$100K", "$100K-$500K", "$500K-$1M", "$1M-$5M", ">$5M"]
            view_copy = view_cartera.copy()
            view_copy["rango_mora"] = pd.cut(valores_mora, bins=bins, labels=labels, right=False)
            rango_counts = view_copy["rango_mora"].value_counts().sort_index()
            
            df_rangos = pd.DataFrame({
                "Rango": rango_counts.index,
                "Cantidad": rango_counts.values.astype(int)
            })
            fig_rangos = px.bar(
                df_rangos,
                x="Rango",
                y="Cantidad",
                title=f"Clientes por Rango ({seg})",
                text="Cantidad"
            )
            # Calcular escala Y dinámica
            max_valor = df_rangos["Cantidad"].max() if len(df_rangos) > 0 else 1
            # Determinar incremento apropiado basado en el máximo
            if max_valor <= 10:
                dtick_val = 1
            elif max_valor <= 50:
                dtick_val = 5
            elif max_valor <= 100:
                dtick_val = 10
            elif max_valor <= 500:
                dtick_val = 50
            else:
                dtick_val = max(1, int(max_valor / 20))  # Aproximadamente 20 ticks
            
            fig_rangos.update_traces(
                marker_color="#EF4444",
                textposition='outside'
            )
            fig_rangos.update_layout(
                height=350,  # Mismo tamaño que el histograma
                showlegend=False,
                margin=dict(t=50, b=80, l=50, r=50),  # Márgenes para que no se corte, más espacio abajo para labels
                yaxis=dict(
                    tickmode='linear',
                    dtick=dtick_val,
                    tickformat='d',
                    range=[0, max_valor * 1.15]  # Agregar 15% de espacio arriba para que las barras no se corten
                )
            )
            st.plotly_chart(fig_rangos, use_container_width=True)
    else:
        st.info("No hay datos de cartera para el segmento seleccionado")
