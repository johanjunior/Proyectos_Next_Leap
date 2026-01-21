# 📊 MVP Aseguradora | Cartera & Renovaciones

Aplicación web MVP desarrollada con Streamlit para la gestión de cartera, renovaciones y clientes de una aseguradora.

## 📋 Descripción

Este proyecto es un MVP (Minimum Viable Product) que permite gestionar tres áreas principales de una aseguradora:

- **Clientes**: Visualización y gestión de información de clientes y pólizas
- **Cartera**: Seguimiento de mora y gestión de pagos pendientes
- **Renovaciones**: Control de pólizas próximas a vencer y gestión de renovaciones

La aplicación utiliza un archivo CSV como fuente de datos y proporciona una interfaz web intuitiva para el análisis y gestión de la información.

## ✨ Características

### 🔐 Autenticación
- Sistema de login con roles (Admin, Cartera, Renovaciones, Auditor)
- Gestión de sesiones de usuario
- Control de acceso basado en roles

### 👥 Módulo de Clientes
- Búsqueda por nombre, documento o número de póliza
- Filtros por estado de póliza y segmento
- Vista 360° del cliente con información detallada
- Métricas clave: días en mora, valor en mora, días para vencimiento

### 💰 Módulo de Cartera
- Segmentación de mora (1-15 días, 16-45 días, >45 días)
- Visualización de saldos pendientes
- Envío real de notificaciones por Email o WhatsApp
- Generación de mensajes de notificación personalizados
- Enlaces de pago dinámicos
- Información de consentimientos para comunicación
- Validación automática de consentimientos antes de enviar

### ♻️ Módulo de Renovaciones
- Ventanas de renovación configurables (7, 15, 30 días)
- Filtrado de pólizas renovables
- Envío real de notificaciones por Email o WhatsApp
- Generación de mensajes de renovación
- Soporte para múltiples canales (Email, WhatsApp)
- Validación de consentimientos por canal

### 📋 Módulo de Trazabilidad
- Visualización completa de logs de notificaciones
- Filtros por tipo, canal y estado
- Métricas de envíos (enviados, fallidos, bloqueados)
- Detalle de cada notificación con mensaje completo
- Registro de errores y bloqueos por falta de consentimiento

## 🚀 Instalación

### Requisitos previos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

1. Clonar o descargar el repositorio:
```bash
cd /home/sebastian/PycharmProjects/Proyectos_Next_Leap/aseguradora_mvp
```

2. Crear un entorno virtual (recomendado):
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

El archivo `requirements.txt` incluye:
- `streamlit>=1.28.0` - Framework web
- `pandas>=2.0.0` - Manejo de datos
- `twilio>=8.0.0` - Integración con WhatsApp (opcional, solo si usas WhatsApp)

## 📁 Estructura del Proyecto

```
aseguradora_mvp/
├── app.py                              # Aplicación principal
├── modules/
│   ├── __init__.py                     # Inicialización del módulo
│   ├── login.py                        # Módulo de autenticación
│   ├── clientes.py                     # Módulo de gestión de clientes
│   ├── cartera.py                      # Módulo de gestión de cartera
│   ├── renovaciones.py                 # Módulo de renovaciones
│   ├── notificaciones.py               # Sistema de envío de notificaciones
│   └── trazabilidad.py                 # Visualización de logs
├── .streamlit/
│   ├── secrets.toml                    # Credenciales (no subir a Git)
│   └── secrets.toml.example            # Ejemplo de configuración
├── logs/                               # Directorio de logs (generado automáticamente)
│   └── notificaciones.jsonl            # Logs de notificaciones
├── sabana_cartera_renovaciones_200cols.csv  # Archivo de datos
├── requirements.txt                    # Dependencias del proyecto
└── README.md                           # Este archivo
```

## 🎯 Uso

### Ejecutar la aplicación

```bash
streamlit run app.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`

### Flujo de uso

1. **Login**: Ingresa con usuario, contraseña y selecciona un rol
2. **Navegación**: Usa el menú lateral para acceder a los diferentes módulos
3. **Clientes**: Busca y filtra clientes, visualiza fichas 360°
4. **Cartera**: Revisa mora por segmentos, genera notificaciones
5. **Renovaciones**: Gestiona pólizas próximas a vencer, envía recordatorios

## 📊 Formato de Datos

La aplicación espera un archivo CSV (`sabana_cartera_renovaciones_200cols.csv`) con las siguientes columnas principales:

### Columnas requeridas:
- `id_cliente`, `id_poliza`
- `nombre_cliente`, `documento_cliente`
- `numero_poliza`, `producto`, `plan`
- `estado_poliza`, `segmento`
- `dias_mora`, `valor_en_mora`
- `fecha_inicio_vigencia`, `fecha_fin_vigencia`
- `fecha_venc_factura`, `fecha_factura`
- `fecha_ultimo_pago`, `promesa_pago_fecha`
- `dias_para_vencimiento`, `semáforo_vencimiento`
- `estado_renovacion`, `fecha_renovacion_estimada`
- `email_cliente`, `telefono_cliente`
- `consentimiento_email`, `consentimiento_whatsapp`
- `renovable`
- Y otras columnas según necesidades del negocio

## ⚙️ Configuración

### Variables de configuración en `app.py`:

- `DATA_PATH`: Ruta al archivo CSV de datos
- `BASE_PAGOS`: URL base para enlaces de pago (actualmente: `https://optimoconsultores.com/pagos/`)

### Configuración de Notificaciones

Para habilitar el envío real de notificaciones por Email y WhatsApp, necesitas configurar las credenciales:

#### 1. Configurar Email (Gmail)

1. **Crear App Password en Gmail:**
   - Ve a tu cuenta de Google > [Seguridad](https://myaccount.google.com/security)
   - Activa la verificación en 2 pasos si no está activada
   - Busca "Contraseñas de aplicaciones" y crea una nueva
   - Copia la contraseña generada (16 caracteres)

2. **Editar `.streamlit/secrets.toml`:**
   ```toml
   [email]
   smtp_server = "smtp.gmail.com"
   smtp_port = 587
   email_from = "tu_email@gmail.com"
   email_password = "tu_app_password_aqui"
   ```

#### 2. Configurar WhatsApp (Twilio)

1. **Crear cuenta en Twilio:**
   - Regístrate en [Twilio](https://www.twilio.com/)
   - Obtén tu Account SID y Auth Token desde el dashboard
   - Configura un número de WhatsApp en Twilio

2. **Editar `.streamlit/secrets.toml`:**
   ```toml
   [whatsapp]
   account_sid = "tu_twilio_account_sid"
   auth_token = "tu_twilio_auth_token"
   whatsapp_from = "whatsapp:+14155238886"
   ```

**Nota:** También puedes usar variables de entorno en lugar del archivo `secrets.toml`:
- `EMAIL_FROM`, `EMAIL_PASSWORD`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `WHATSAPP_FROM`

## 🔒 Seguridad

⚠️ **Nota importante**: Este es un MVP. El sistema de autenticación actual es básico y no debe usarse en producción sin implementar:
- Validación real de credenciales
- Conexión a base de datos
- Encriptación de contraseñas
- Tokens de sesión seguros
- Logs de auditoría

## 🚧 Limitaciones del MVP

- Autenticación simulada (no hay validación real)
- Datos en CSV (no hay base de datos)
- Sin persistencia de cambios (los datos se leen del CSV)
- Los logs de notificaciones se guardan en archivo JSONL (no en base de datos)

## 🔮 Próximos pasos (Fase 2)

- [x] Envío real de notificaciones (Email/WhatsApp) ✅
- [x] Sistema de logs y trazabilidad ✅
- [ ] Integración con base de datos
- [ ] Sistema de autenticación real
- [ ] Persistencia de cambios en base de datos
- [ ] Dashboard con métricas agregadas
- [ ] Exportación de reportes
- [ ] Programación automática de notificaciones
- [ ] Plantillas personalizables de mensajes

## 👥 Roles de Usuario

- **Admin**: Acceso completo a todos los módulos
- **Cartera**: Enfoque en gestión de mora y pagos
- **Renovaciones**: Enfoque en gestión de renovaciones
- **Auditor**: Acceso de solo lectura para auditoría

## 📝 Licencia

Este proyecto es un MVP desarrollado para propósitos internos.

## 🤝 Contribuciones

Este es un proyecto MVP. Para mejoras o sugerencias, contactar al equipo de desarrollo.

---

**Desarrollado con ❤️ usando Streamlit**
