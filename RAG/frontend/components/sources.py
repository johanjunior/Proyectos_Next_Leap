"""
Source documents display component.
Uses streamlit-pdf-viewer for PDF visualization and st.dialog for modal popups.

Docs: https://github.com/lfoppiano/streamlit-pdf-viewer
"""
import streamlit as st
from typing import List, Dict, Optional
import requests

# Try to import streamlit-pdf-viewer
try:
    from streamlit_pdf_viewer import pdf_viewer
    PDF_VIEWER_AVAILABLE = True
except ImportError:
    PDF_VIEWER_AVAILABLE = False


def _download_pdf_to_memory(signed_url: str) -> Optional[bytes]:
    """
    Download PDF from signed URL to memory.
    
    Args:
        signed_url: Hetzner signed URL for the PDF
        
    Returns:
        PDF bytes or None if download failed
    """
    try:
        response = requests.get(signed_url, timeout=60)
        response.raise_for_status()
        return response.content
    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.RequestException:
        return None


@st.dialog("📄 Documento PDF", width="large")
def _pdf_viewer_dialog():
    """
    Dialog to display a PDF document.
    Uses session state to get the source data.
    """
    # Get source data from session state
    source = st.session_state.get("_pdf_dialog_source", {})
    
    if not source:
        st.warning("No hay información del documento.")
        return
    
    doc_name = source.get('document_name', 'Documento')
    signed_url = source.get('signed_url')
    page_number = source.get('page_number')
    snippet = source.get('snippet', '')
    score = source.get('score')
    
    # Header with document info
    st.subheader(doc_name)
    
    # Info row
    info_cols = st.columns(3)
    with info_cols[0]:
        if page_number:
            st.info(f"📍 Página: {page_number}")
    with info_cols[1]:
        if score is not None:
            if isinstance(score, float):
                st.success(f"🎯 Relevancia: {score:.0%}")
            else:
                st.success(f"🎯 Relevancia: {score}")
    with info_cols[2]:
        if signed_url:
            st.markdown(f"[🔗 Abrir en nueva pestaña]({signed_url})")
    
    # Snippet section
    if snippet:
        with st.expander("📝 Fragmento relevante del documento", expanded=False):
            st.text(snippet[:800] + "..." if len(snippet) > 800 else snippet)
    
    st.divider()
    
    # PDF Viewer
    if signed_url:
        if PDF_VIEWER_AVAILABLE:
            with st.spinner("Descargando y cargando PDF..."):
                pdf_bytes = _download_pdf_to_memory(signed_url)
            
            if pdf_bytes:
                try:
                    # scroll_to_page: 1-based; opens PDF at relevant page when available
                    scroll_page = None
                    if page_number is not None:
                        try:
                            p = int(page_number)
                            if p > 0:
                                scroll_page = p
                        except (TypeError, ValueError):
                            pass
                    # Use streamlit-pdf-viewer with binary data
                    # Docs: https://github.com/lfoppiano/streamlit-pdf-viewer
                    kwargs = dict(
                        input=pdf_bytes,
                        width=700,
                        height=550,
                        render_text=True,  # Enable text selection/copy
                    )
                    if scroll_page is not None:
                        kwargs["scroll_to_page"] = scroll_page
                    pdf_viewer(**kwargs)
                except Exception as e:
                    st.error(f"Error al renderizar el PDF: {str(e)}")
                    st.markdown(f"**Enlace directo:** [{doc_name}]({signed_url})")
            else:
                st.warning("No se pudo descargar el documento. Intenta con el enlace directo.")
                st.markdown(f"**Enlace directo:** [{doc_name}]({signed_url})")
        else:
            # Fallback: iframe (works in most browsers)
            st.warning("streamlit-pdf-viewer no está instalado. Usando visualización básica.")
            st.markdown(
                f'<iframe src="{signed_url}" width="100%" height="550" style="border:1px solid #ddd;"></iframe>',
                unsafe_allow_html=True
            )
    else:
        st.error("No hay URL disponible para este documento.")


def display_sources(sources: List[Dict], expandable: bool = True, key_prefix: Optional[str] = None):
    """
    Display source documents as a list of buttons.
    Clicking a button opens the PDF in a modal dialog.
    
    Args:
        sources: List of source dictionaries with document information
        expandable: (Deprecated) Kept for backwards compatibility
        key_prefix: Unique prefix for Streamlit widget keys (e.g. per message).
                    Avoids "multiple elements with same key" when rendering history.
    """
    if not sources:
        return
    
    prefix = key_prefix or "sources"
    
    st.markdown("---")
    st.markdown("### 📚 Fuentes Documentales")
    st.caption(f"{len(sources)} documento(s) relevante(s)")
    
    # Display sources as buttons
    for i, source in enumerate(sources):
        doc_name = source.get('document_name', f'Documento {i+1}')
        page_number = source.get('page_number')
        score = source.get('score')
        signed_url = source.get('signed_url')
        
        # Create button label
        btn_label = f"📄 {doc_name}"
        if page_number:
            btn_label += f" (pág. {page_number})"
        
        # Layout: Button | Score | Link
        cols = st.columns([0.75, 0.12, 0.13])
        
        with cols[0]:
            # Main button to open dialog (key unique per prefix + index)
            if signed_url:
                if st.button(
                    btn_label,
                    key=f"{prefix}_src_btn_{i}",
                    use_container_width=True,
                    type="secondary",
                    help="Click para ver el documento"
                ):
                    # Store source in session state and open dialog
                    st.session_state["_pdf_dialog_source"] = source
                    _pdf_viewer_dialog()
            else:
                # No URL - show as text
                st.markdown(f"📄 {doc_name} *(URL no disponible)*")
        
        with cols[1]:
            # Relevance score
            if score is not None:
                if isinstance(score, float):
                    st.caption(f"🎯 {score:.0%}")
                else:
                    st.caption(f"🎯 {score}")
        
        with cols[2]:
            # Direct link
            if signed_url:
                st.markdown(
                    f'<a href="{signed_url}" target="_blank" title="Abrir en nueva pestaña">🔗</a>',
                    unsafe_allow_html=True
                )


def display_source_badge(source: Dict) -> str:
    """
    Create a compact badge representation of a source.
    
    Args:
        source: Source dictionary
        
    Returns:
        Formatted badge string
    """
    doc_name = source.get('document_name', 'Documento')
    page = source.get('page_number')
    
    if page:
        return f"📄 {doc_name} (p. {page})"
    return f"📄 {doc_name}"


def display_sources_compact(sources: List[Dict]):
    """
    Display sources in a compact format (badges only).
    
    Args:
        sources: List of source dictionaries
    """
    if not sources:
        return
    
    badges = [display_source_badge(s) for s in sources]
    st.caption(" | ".join(badges))
