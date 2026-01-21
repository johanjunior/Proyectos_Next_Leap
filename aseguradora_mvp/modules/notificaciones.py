"""
Módulo de notificaciones para envío de mensajes por Gmail y WhatsApp
Incluye sistema de trazabilidad y logs
"""
import os
import smtplib
import json
import pandas as pd
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Tuple, Any, Callable
import streamlit as st

# Para WhatsApp - usando Twilio (alternativa: WhatsApp Business API)
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

# Configuración de rutas
LOGS_DIR = "logs"
NOTIFICACIONES_LOG = os.path.join(LOGS_DIR, "notificaciones.jsonl")

def init_logs_dir():
    """Crea el directorio de logs si no existe"""
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)

def log_notificacion(
    tipo: str,
    canal: str,
    destinatario: str,
    mensaje: str,
    estado: str,
    id_cliente: Optional[str] = None,
    id_poliza: Optional[str] = None,
    error: Optional[str] = None,
    usuario: Optional[str] = None
):
    """
    Registra una notificación en el log de trazabilidad
    
    Args:
        tipo: Tipo de notificación ('cartera', 'renovacion')
        canal: Canal usado ('email', 'whatsapp')
        destinatario: Email o teléfono del destinatario
        mensaje: Mensaje enviado
        estado: 'enviado', 'fallido', 'bloqueado'
        id_cliente: ID del cliente (opcional)
        id_poliza: ID de la póliza (opcional)
        error: Mensaje de error si falló (opcional)
        usuario: Usuario que envió la notificación (opcional)
    """
    init_logs_dir()
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tipo": tipo,
        "canal": canal,
        "destinatario": destinatario,
        "mensaje": mensaje,
        "estado": estado,
        "id_cliente": id_cliente,
        "id_poliza": id_poliza,
        "error": error,
        "usuario": usuario or st.session_state.get("user", "unknown")
    }
    
    with open(NOTIFICACIONES_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def get_config_email() -> Dict[str, str]:
    """
    Obtiene la configuración de email desde variables de entorno o secrets de Streamlit
    """
    # Intentar obtener desde secrets, si no existe usar valores por defecto
    try:
        email_secrets = st.secrets.get("email", {})
    except (AttributeError, FileNotFoundError, KeyError):
        email_secrets = {}
    
    return {
        "smtp_server": os.getenv("SMTP_SERVER", email_secrets.get("smtp_server", "smtp.gmail.com")),
        "smtp_port": int(os.getenv("SMTP_PORT", email_secrets.get("smtp_port", 587))),
        "email_from": os.getenv("EMAIL_FROM", email_secrets.get("email_from", "")),
        "email_password": os.getenv("EMAIL_PASSWORD", email_secrets.get("email_password", "")),
    }

def get_config_whatsapp() -> Dict[str, str]:
    """
    Obtiene la configuración de WhatsApp desde variables de entorno o secrets de Streamlit
    """
    # Intentar obtener desde secrets, si no existe usar valores por defecto
    try:
        whatsapp_secrets = st.secrets.get("whatsapp", {})
    except (AttributeError, FileNotFoundError, KeyError):
        whatsapp_secrets = {}
    
    return {
        "account_sid": os.getenv("TWILIO_ACCOUNT_SID", whatsapp_secrets.get("account_sid", "")),
        "auth_token": os.getenv("TWILIO_AUTH_TOKEN", whatsapp_secrets.get("auth_token", "")),
        "whatsapp_from": os.getenv("WHATSAPP_FROM", whatsapp_secrets.get("whatsapp_from", "")),
    }

def enviar_email(
    destinatario: str,
    asunto: str,
    mensaje: str,
    id_cliente: Optional[str] = None,
    id_poliza: Optional[str] = None,
    modo_prototipo: bool = True,
    tipo: str = "general"
) -> Tuple[bool, Optional[str]]:
    """
    Envía un email usando SMTP o simula el envío en modo prototipo
    
    Args:
        modo_prototipo: Si es True, simula el envío sin requerir credenciales
    
    Returns:
        Tuple[bool, Optional[str]]: (éxito, mensaje_error)
    """
    try:
        # Modo prototipo: simular envío exitoso
        if modo_prototipo:
            # Simular delay de envío
            import time
            time.sleep(0.5)  # Simular latencia de red
            
            # Log exitoso (simulado)
            log_notificacion(
                tipo=tipo,
                canal="email",
                destinatario=destinatario,
                mensaje=mensaje,
                estado="enviado",
                id_cliente=id_cliente,
                id_poliza=id_poliza
            )
            return True, None
        
        # Modo producción: envío real
        config = get_config_email()
        
        if not config["email_from"] or not config["email_password"]:
            error_msg = (
                "⚠️ Configuración de email no encontrada.\n\n"
                "Para configurar el envío de emails:\n"
                "1. Edita el archivo: .streamlit/secrets.toml\n"
                "2. Completa las credenciales en la sección [email]:\n"
                "   - email_from: tu email\n"
                "   - email_password: tu App Password de Gmail\n\n"
                "O configura las variables de entorno:\n"
                "- EMAIL_FROM\n"
                "- EMAIL_PASSWORD"
            )
            log_notificacion(
                tipo=tipo,
                canal="email",
                destinatario=destinatario,
                mensaje=mensaje,
                estado="fallido",
                id_cliente=id_cliente,
                id_poliza=id_poliza,
                error=error_msg
            )
            return False, error_msg
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg["From"] = config["email_from"]
        msg["To"] = destinatario
        msg["Subject"] = asunto
        msg.attach(MIMEText(mensaje, "plain", "utf-8"))
        
        # Enviar
        server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
        server.starttls()
        server.login(config["email_from"], config["email_password"])
        server.send_message(msg)
        server.quit()
        
        # Log exitoso
        log_notificacion(
            tipo=tipo,
            canal="email",
            destinatario=destinatario,
            mensaje=mensaje,
            estado="enviado",
            id_cliente=id_cliente,
            id_poliza=id_poliza
        )
        
        return True, None
        
    except Exception as e:
        error_msg = str(e)
        log_notificacion(
            tipo=tipo,
            canal="email",
            destinatario=destinatario,
            mensaje=mensaje,
            estado="fallido",
            id_cliente=id_cliente,
            id_poliza=id_poliza,
            error=error_msg
        )
        return False, error_msg

def enviar_whatsapp(
    destinatario: str,
    mensaje: str,
    id_cliente: Optional[str] = None,
    id_poliza: Optional[str] = None,
    modo_prototipo: bool = True,
    tipo: str = "general"
) -> Tuple[bool, Optional[str]]:
    """
    Envía un mensaje de WhatsApp usando Twilio o simula el envío en modo prototipo
    
    Args:
        modo_prototipo: Si es True, simula el envío sin requerir credenciales
    
    Returns:
        Tuple[bool, Optional[str]]: (éxito, mensaje_error)
    """
    # Modo prototipo: simular envío exitoso
    if modo_prototipo:
        # Simular delay de envío
        import time
        time.sleep(0.5)  # Simular latencia de red
        
        # Formatear número para el log (convertir a string primero)
        destinatario_str = str(destinatario).strip()
        if not destinatario_str.startswith("+"):
            destinatario_log = f"+57{destinatario_str.lstrip('57')}"
        else:
            destinatario_log = destinatario_str
        
        # Log exitoso (simulado)
        log_notificacion(
            tipo=tipo,
            canal="whatsapp",
            destinatario=destinatario_log,
            mensaje=mensaje,
            estado="enviado",
            id_cliente=id_cliente,
            id_poliza=id_poliza
        )
        return True, None
    
    # Modo producción: envío real
    if not TWILIO_AVAILABLE:
        error_msg = "Twilio no está instalado. Instala con: pip install twilio"
        log_notificacion(
            tipo=tipo,
            canal="whatsapp",
            destinatario=destinatario,
            mensaje=mensaje,
            estado="fallido",
            id_cliente=id_cliente,
            id_poliza=id_poliza,
            error=error_msg
        )
        return False, error_msg
    
    try:
        config = get_config_whatsapp()
        
        if not config["account_sid"] or not config["auth_token"] or not config["whatsapp_from"]:
            error_msg = (
                "⚠️ Configuración de WhatsApp no encontrada.\n\n"
                "Para configurar el envío de WhatsApp:\n"
                "1. Edita el archivo: .streamlit/secrets.toml\n"
                "2. Completa las credenciales en la sección [whatsapp]:\n"
                "   - account_sid: Tu Twilio Account SID\n"
                "   - auth_token: Tu Twilio Auth Token\n"
                "   - whatsapp_from: Tu número de Twilio\n\n"
                "O configura las variables de entorno:\n"
                "- TWILIO_ACCOUNT_SID\n"
                "- TWILIO_AUTH_TOKEN\n"
                "- WHATSAPP_FROM"
            )
            log_notificacion(
                tipo=tipo,
                canal="whatsapp",
                destinatario=destinatario,
                mensaje=mensaje,
                estado="fallido",
                id_cliente=id_cliente,
                id_poliza=id_poliza,
                error=error_msg
            )
            return False, error_msg
        
        # Formatear número (debe incluir código de país, ej: +573001234567)
        # Convertir a string primero por si viene como número
        destinatario = str(destinatario).strip()
        if not destinatario.startswith("+"):
            # Asumir código de país colombiano si no está presente
            destinatario = f"+57{destinatario.lstrip('57')}"
        
        # Enviar con Twilio
        client = TwilioClient(config["account_sid"], config["auth_token"])
        message = client.messages.create(
            body=mensaje,
            from_=config["whatsapp_from"],  # Formato: whatsapp:+14155238886
            to=f"whatsapp:{destinatario}"
        )
        
        # Log exitoso
        log_notificacion(
            tipo=tipo,
            canal="whatsapp",
            destinatario=destinatario,
            mensaje=mensaje,
            estado="enviado",
            id_cliente=id_cliente,
            id_poliza=id_poliza
        )
        
        return True, None
        
    except Exception as e:
        error_msg = str(e)
        log_notificacion(
            tipo=tipo,
            canal="whatsapp",
            destinatario=destinatario,
            mensaje=mensaje,
            estado="fallido",
            id_cliente=id_cliente,
            id_poliza=id_poliza,
            error=error_msg
        )
        return False, error_msg

def enviar_notificacion_cartera(
    row: pd.Series,
    canal: str = "email"
) -> Tuple[bool, Optional[str]]:
    """
    Envía notificación de cartera (mora) por el canal especificado
    
    Args:
        row: Fila del DataFrame con información del cliente/póliza
        canal: 'email' o 'whatsapp'
    
    Returns:
        Tuple[bool, Optional[str]]: (éxito, mensaje_error)
    """
    # Validar consentimiento
    if canal == "email":
        if not row.get("consentimiento_email"):
            log_notificacion(
                tipo="cartera",
                canal="email",
                destinatario=row.get("email_cliente", ""),
                mensaje="",
                estado="bloqueado",
                id_cliente=str(row.get("id_cliente", "")),
                id_poliza=str(row.get("numero_poliza", "")),
                error="Sin consentimiento de email"
            )
            return False, "Cliente no tiene consentimiento para recibir emails"
        destinatario = row.get("email_cliente", "")
    else:  # whatsapp
        if not row.get("consentimiento_whatsapp"):
            log_notificacion(
                tipo="cartera",
                canal="whatsapp",
                destinatario=row.get("telefono_cliente", ""),
                mensaje="",
                estado="bloqueado",
                id_cliente=str(row.get("id_cliente", "")),
                id_poliza=str(row.get("numero_poliza", "")),
                error="Sin consentimiento de WhatsApp"
            )
            return False, "Cliente no tiene consentimiento para recibir WhatsApp"
        destinatario = row.get("telefono_cliente", "")
    
    # Validar que haya destinatario
    if not destinatario or pd.isna(destinatario):
        error_msg = f"No hay {canal} disponible para el cliente"
        log_notificacion(
            tipo="cartera",
            canal=canal,
            destinatario="",
            mensaje="",
            estado="fallido",
            id_cliente=str(row.get("id_cliente", "")),
            id_poliza=str(row.get("numero_poliza", "")),
            error=error_msg
        )
        return False, error_msg
    
    # Construir mensaje
    nombre = row.get("nombre_cliente", "Cliente")
    valor_mora = row.get("valor_en_mora", 0)
    fecha_venc = row.get("fecha_venc_factura", "")
    link_pago = row.get("link_pago", "")
    
    mensaje = (
        f"Hola {nombre}, registramos un saldo en mora por ${valor_mora:,.0f}. "
        f"Fecha límite: {fecha_venc}. "
        f"Puedes pagar aquí: {link_pago}"
    )
    
    # Enviar según canal (modo prototipo activado por defecto)
    if canal == "email":
        asunto = f"Recordatorio de pago - Póliza {row.get('numero_poliza', '')}"
        return enviar_email(
            destinatario=destinatario,
            asunto=asunto,
            mensaje=mensaje,
            id_cliente=str(row.get("id_cliente", "")),
            id_poliza=str(row.get("numero_poliza", "")),
            modo_prototipo=True,  # Modo prototipo activado
            tipo="cartera"  # Tipo correcto para cartera
        )
    else:  # whatsapp
        return enviar_whatsapp(
            destinatario=destinatario,
            mensaje=mensaje,
            id_cliente=str(row.get("id_cliente", "")),
            id_poliza=str(row.get("numero_poliza", "")),
            modo_prototipo=True,  # Modo prototipo activado
            tipo="cartera"  # Tipo correcto para cartera
        )

def enviar_notificaciones_cartera_masivo(
    df: pd.DataFrame,
    canal: str = "email",
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Dict[str, Any]:
    """
    Envía notificaciones de cartera en bloque a múltiples clientes
    
    Args:
        df: DataFrame con las filas de clientes a notificar
        canal: 'email' o 'whatsapp'
        progress_callback: Función opcional para actualizar progreso (recibe progreso, total)
    
    Returns:
        Dict con estadísticas del envío masivo
    """
    resultados = {
        "total": len(df),
        "enviados": 0,
        "fallidos": 0,
        "bloqueados": 0,
        "sin_destinatario": 0,
        "detalles": []
    }
    
    # Función helper para convertir consentimiento a booleano
    def tiene_consentimiento(valor):
        if pd.isna(valor):
            return False
        valor_str = str(valor).lower().strip()
        return valor_str in ["sí", "si", "yes", "true", "1", "1.0", "s", "y"]
    
    total = len(df)
    for idx, (row_idx, row) in enumerate(df.iterrows(), 1):
        # Actualizar progreso si hay callback
        if progress_callback:
            progress_callback(idx, total)
        
        # Validar consentimiento
        if canal == "email":
            tiene_consent = tiene_consentimiento(row.get("consentimiento_email"))
            destinatario = row.get("email_cliente", "")
        else:  # whatsapp
            tiene_consent = tiene_consentimiento(row.get("consentimiento_whatsapp"))
            destinatario = row.get("telefono_cliente", "")
        
        # Validar destinatario
        if not destinatario or pd.isna(destinatario):
            resultados["sin_destinatario"] += 1
            resultados["detalles"].append({
                "id_poliza": str(row.get("numero_poliza", "")),
                "nombre": row.get("nombre_cliente", ""),
                "estado": "sin_destinatario",
                "error": f"No hay {canal} disponible"
            })
            continue
        
        # Validar consentimiento
        if not tiene_consent:
            resultados["bloqueados"] += 1
            resultados["detalles"].append({
                "id_poliza": str(row.get("numero_poliza", "")),
                "nombre": row.get("nombre_cliente", ""),
                "estado": "bloqueado",
                "error": f"Sin consentimiento de {canal}"
            })
            continue
        
        # Enviar notificación
        exito, error = enviar_notificacion_cartera(row, canal=canal)
        
        if exito:
            resultados["enviados"] += 1
            resultados["detalles"].append({
                "id_poliza": str(row.get("numero_poliza", "")),
                "nombre": row.get("nombre_cliente", ""),
                "estado": "enviado",
                "destinatario": destinatario
            })
        else:
            resultados["fallidos"] += 1
            resultados["detalles"].append({
                "id_poliza": str(row.get("numero_poliza", "")),
                "nombre": row.get("nombre_cliente", ""),
                "estado": "fallido",
                "error": error or "Error desconocido"
            })
    
    return resultados

def enviar_notificaciones_renovacion_masivo(
    df: pd.DataFrame,
    canal: str = "email",
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Dict[str, Any]:
    """
    Envía notificaciones de renovación en bloque a múltiples clientes
    
    Args:
        df: DataFrame con las filas de clientes a notificar
        canal: 'email' o 'whatsapp'
        progress_callback: Función opcional para actualizar progreso (recibe progreso, total)
    
    Returns:
        Dict con estadísticas del envío masivo
    """
    resultados = {
        "total": len(df),
        "enviados": 0,
        "fallidos": 0,
        "bloqueados": 0,
        "sin_destinatario": 0,
        "detalles": []
    }
    
    # Función helper para convertir consentimiento a booleano
    def tiene_consentimiento(valor):
        if pd.isna(valor):
            return False
        valor_str = str(valor).lower().strip()
        return valor_str in ["sí", "si", "yes", "true", "1", "1.0", "s", "y"]
    
    total = len(df)
    for idx, (row_idx, row) in enumerate(df.iterrows(), 1):
        # Actualizar progreso si hay callback
        if progress_callback:
            progress_callback(idx, total)
        
        # Validar consentimiento
        if canal == "email":
            tiene_consent = tiene_consentimiento(row.get("consentimiento_email"))
            destinatario = row.get("email_cliente", "")
        else:  # whatsapp
            tiene_consent = tiene_consentimiento(row.get("consentimiento_whatsapp"))
            destinatario = row.get("telefono_cliente", "")
        
        # Validar destinatario
        if not destinatario or pd.isna(destinatario):
            resultados["sin_destinatario"] += 1
            resultados["detalles"].append({
                "id_poliza": str(row.get("numero_poliza", "")),
                "nombre": row.get("nombre_cliente", ""),
                "estado": "sin_destinatario",
                "error": f"No hay {canal} disponible"
            })
            continue
        
        # Validar consentimiento
        if not tiene_consent:
            resultados["bloqueados"] += 1
            resultados["detalles"].append({
                "id_poliza": str(row.get("numero_poliza", "")),
                "nombre": row.get("nombre_cliente", ""),
                "estado": "bloqueado",
                "error": f"Sin consentimiento de {canal}"
            })
            continue
        
        # Enviar notificación
        exito, error = enviar_notificacion_renovacion(row, canal=canal)
        
        if exito:
            resultados["enviados"] += 1
            resultados["detalles"].append({
                "id_poliza": str(row.get("numero_poliza", "")),
                "nombre": row.get("nombre_cliente", ""),
                "estado": "enviado",
                "destinatario": destinatario
            })
        else:
            resultados["fallidos"] += 1
            resultados["detalles"].append({
                "id_poliza": str(row.get("numero_poliza", "")),
                "nombre": row.get("nombre_cliente", ""),
                "estado": "fallido",
                "error": error or "Error desconocido"
            })
    
    return resultados

def enviar_notificacion_renovacion(
    row: pd.Series,
    canal: str = "email"
) -> Tuple[bool, Optional[str]]:
    """
    Envía notificación de renovación por el canal especificado
    
    Args:
        row: Fila del DataFrame con información del cliente/póliza
        canal: 'email' o 'whatsapp'
    
    Returns:
        Tuple[bool, Optional[str]]: (éxito, mensaje_error)
    """
    # Función helper para convertir consentimiento a booleano
    def tiene_consentimiento(valor):
        if pd.isna(valor):
            return False
        valor_str = str(valor).lower().strip()
        return valor_str in ["sí", "si", "yes", "true", "1", "1.0", "s", "y"]
    
    # Validar consentimiento
    if canal == "email":
        if not tiene_consentimiento(row.get("consentimiento_email")):
            log_notificacion(
                tipo="renovacion",
                canal="email",
                destinatario=row.get("email_cliente", ""),
                mensaje="",
                estado="bloqueado",
                id_cliente=str(row.get("id_cliente", "")),
                id_poliza=str(row.get("numero_poliza", "")),
                error="Sin consentimiento de email"
            )
            return False, "Cliente no tiene consentimiento para recibir emails"
        destinatario = row.get("email_cliente", "")
    else:  # whatsapp
        if not tiene_consentimiento(row.get("consentimiento_whatsapp")):
            log_notificacion(
                tipo="renovacion",
                canal="whatsapp",
                destinatario=row.get("telefono_cliente", ""),
                mensaje="",
                estado="bloqueado",
                id_cliente=str(row.get("id_cliente", "")),
                id_poliza=str(row.get("numero_poliza", "")),
                error="Sin consentimiento de WhatsApp"
            )
            return False, "Cliente no tiene consentimiento para recibir WhatsApp"
        destinatario = row.get("telefono_cliente", "")
    
    # Validar que haya destinatario
    if not destinatario or pd.isna(destinatario):
        error_msg = f"No hay {canal} disponible para el cliente"
        log_notificacion(
            tipo="renovacion",
            canal=canal,
            destinatario="",
            mensaje="",
            estado="fallido",
            id_cliente=str(row.get("id_cliente", "")),
            id_poliza=str(row.get("numero_poliza", "")),
            error=error_msg
        )
        return False, error_msg
    
    # Construir mensaje
    nombre = row.get("nombre_cliente", "Cliente")
    num_poliza = row.get("numero_poliza", "")
    producto = row.get("producto", "")
    plan = row.get("plan", "")
    fecha_fin = row.get("fecha_fin_vigencia", "")
    dias_venc = int(row.get("dias_para_vencimiento", 0) or 0)
    
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
    
    mensaje = (
        f"Hola {nombre}, tu póliza {num_poliza} "
        f"({producto} - {plan}) vence el {fecha_fin}. "
        f"{msg_dias}. "
        f"{msg_renovacion}"
    )
    
    # Enviar según canal (modo prototipo activado por defecto)
    if canal == "email":
        # Ajustar asunto según días
        if dias_venc < 0:
            asunto = f"⚠️ URGENTE: Renovación de póliza {num_poliza} - Vencida hace {abs(dias_venc)} días"
        elif dias_venc == 0:
            asunto = f"Renovación de póliza {num_poliza} - Vence hoy"
        else:
            asunto = f"Renovación de póliza {num_poliza} - Vence en {dias_venc} días"
        return enviar_email(
            destinatario=destinatario,
            asunto=asunto,
            mensaje=mensaje,
            id_cliente=str(row.get("id_cliente", "")),
            id_poliza=str(num_poliza),
            modo_prototipo=True,  # Modo prototipo activado
            tipo="renovacion"  # Tipo correcto para renovación
        )
    else:  # whatsapp
        return enviar_whatsapp(
            destinatario=destinatario,
            mensaje=mensaje,
            id_cliente=str(row.get("id_cliente", "")),
            id_poliza=str(num_poliza),
            modo_prototipo=True,  # Modo prototipo activado
            tipo="renovacion"  # Tipo correcto para renovación
        )

def obtener_logs_notificaciones(limite: int = 100) -> pd.DataFrame:
    """
    Obtiene los logs de notificaciones como DataFrame
    
    Args:
        limite: Número máximo de registros a retornar
    
    Returns:
        DataFrame con los logs
    """
    if not os.path.exists(NOTIFICACIONES_LOG):
        return pd.DataFrame()
    
    logs = []
    try:
        with open(NOTIFICACIONES_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Tomar las últimas N líneas
            for line in lines[-limite:]:
                if line.strip():
                    logs.append(json.loads(line))
    except Exception as e:
        st.error(f"Error leyendo logs: {e}")
        return pd.DataFrame()
    
    if not logs:
        return pd.DataFrame()
    
    df = pd.DataFrame(logs)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp", ascending=False)
    
    return df
