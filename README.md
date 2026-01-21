# 📊 MVP Aseguradora | Cartera & Renovaciones

Aplicación web MVP desarrollada con Streamlit para la gestión integral de cartera, renovaciones y clientes de una aseguradora, con sistema completo de notificaciones y trazabilidad.

## 📋 Descripción

Este proyecto es un MVP (Minimum Viable Product) que permite gestionar las áreas principales de una aseguradora:

- **Clientes**: Visualización y gestión de información detallada de clientes y pólizas
- **Tablero de Visualización**: Dashboard ejecutivo con métricas consolidadas y visualizaciones interactivas
- **Cartera**: Seguimiento de mora y gestión de pagos pendientes con envío de notificaciones
- **Renovaciones**: Control de pólizas próximas a vencer y gestión de renovaciones
- **Trazabilidad**: Sistema completo de logs y seguimiento de todas las notificaciones enviadas

La aplicación utiliza un archivo CSV como fuente de datos y proporciona una interfaz web intuitiva para el análisis, gestión y comunicación con clientes.

## ✨ Características

### 🔐 Autenticación
- Sistema de login con roles (Admin, Cartera, Renovaciones, Auditor)
- Gestión de sesiones de usuario
- Control de acceso basado en roles
- Interfaz de login intuitiva

### 👥 Módulo de Clientes
- **Búsqueda avanzada**: Filtrado por nombre o documento de cliente
- **Ficha 360°**: Vista completa del cliente con búsqueda por nombre o documento
  - Información personal (nombre, documento, email, teléfono)
  - Información de póliza (número, producto, plan, fechas)
  - Métricas clave: días en mora, valor en mora, días para vencimiento
  - Estado de consentimientos (Email y WhatsApp)
  - Soporte para múltiples pólizas por cliente
- **Visualización amigable**: Interfaz estructurada con iconos y secciones organizadas
- **Tabla interactiva**: Visualización de clientes con filtros dinámicos

### 📊 Tablero de Visualización
- **Vista ejecutiva consolidada**: Métricas agregadas de renovaciones y cartera
- **Sección Renovaciones**:
  - Selector de ventana de renovación (<= 30 días, <= 15 días, <= 7 días)
  - Gráfica de barras horizontal por semáforo de vencimiento (Rojo, Amarillo, Verde)
  - Categoría "Verde" para registros excluidos de la ventana seleccionada
  - Métricas de total a renovar y desglose por urgencia con porcentajes
  - Altura dinámica de gráficas según número de categorías
- **Sección Cartera en Mora**:
  - Selector de segmento de mora (1-15 días, 16-45 días, >45 días)
  - Métricas clave: Total Clientes, Monto Total, Promedio
  - Histograma de distribución de valores en mora
  - Gráfica de barras de clientes por rango de mora
  - Escala Y dinámica para mejor visualización
- **Visualizaciones interactivas**: Utilizando Plotly para gráficas dinámicas y responsivas

### 💰 Módulo de Cartera
- **Segmentación de mora**: 
  - 1-15 días
  - 16-45 días
  - >45 días
- **Tabla de clientes en mora**: Filtrado automático por segmento seleccionado
- **Envío masivo de notificaciones**:
  - Selección de canal (Email o WhatsApp)
  - Mensajes personalizados por cliente (monto, fecha límite, link de pago)
  - Validación automática de consentimientos
  - Tabla previa de clientes sin autorización en ningún canal
  - Progreso en tiempo real durante el envío
  - Resumen completo con métricas (enviados, fallidos, bloqueados)
  - Tabla detallada de resultados con estado por cliente
- **Soporte para múltiples canales**: Email y WhatsApp con validación independiente de consentimientos
- **Mensajes dinámicos**: Personalización automática con datos del cliente

### ♻️ Módulo de Renovaciones
- **Ventanas de renovación configurables**: 
  - <= 7 días
  - <= 15 días
  - <= 30 días
- **Filtrado inteligente**: Pólizas renovables dentro de la ventana seleccionada
- **Manejo de pólizas vencidas**:
  - Detección automática de pólizas ya vencidas
  - Mensajes específicos indicando días de vencimiento
  - Alertas urgentes para pólizas vencidas
- **Envío masivo de notificaciones**:
  - Selección de canal (Email o WhatsApp)
  - Mensajes personalizados según días para vencimiento
    - Pólizas vencidas: "Tu póliza venció hace X días"
    - Vencimiento hoy: "Tu póliza vence hoy"
    - Próximas a vencer: "Faltan X días"
  - Validación automática de consentimientos
  - Tabla previa de clientes sin autorización
  - Progreso en tiempo real
  - Resumen completo con métricas y tabla detallada
- **Soporte para múltiples canales**: Email y WhatsApp con validación independiente

### 📋 Módulo de Trazabilidad
- **Visualización completa de logs**: Todas las notificaciones enviadas
- **Filtros avanzados**:
  - Por tipo (Cartera, Renovación, General)
  - Por canal (Email, WhatsApp)
  - Por estado (Enviado, Fallido, Bloqueado)
  - Límite de registros configurable
- **Tabla principal mejorada**:
  - Columnas: Fecha/Hora, Documento Cliente, Nombre Cliente, Tipo, Canal, Estado, Destinatario, ID Cliente, ID Póliza, Usuario
  - Información del cliente visible directamente en la tabla
  - Formato amigable con iconos y colores
- **Búsqueda por cliente**: 
  - Campo de búsqueda por nombre o documento
  - Visualización de todas las notificaciones históricas del cliente
  - Expanders con detalle completo de cada notificación
  - Información estructurada y fácil de leer
- **Métricas en tiempo real**: Total, Enviados, Fallidos, Bloqueados con porcentajes
- **Detalle expandible**: Mensaje completo, información del destinatario, errores si los hay

### 📧 Sistema de Notificaciones

#### Modo Prototipo
- **Simulación inteligente**: Envíos simulados exitosos sin requerir tokens reales
- **Logging completo**: Todas las notificaciones se registran en el sistema de trazabilidad
- **Personalización completa**: Mensajes personalizados por cliente manteniendo el formato real
- **Ideal para desarrollo**: Permite probar toda la funcionalidad sin configuración de APIs

#### Modo Producción
- **Email (Gmail)**:
  - Configuración mediante SMTP
  - Soporte para App Passwords de Gmail
  - Validación de formato de email
- **WhatsApp (Twilio)**:
  - Integración con API de Twilio
  - Formato internacional de números telefónicos
  - Validación de números

#### Características del Sistema
- **Validación de consentimientos**: Verificación automática antes de enviar
- **Manejo de errores**: Captura y registro de errores en los logs
- **Bloqueo inteligente**: Clientes sin consentimiento se bloquean automáticamente
- **Personalización**: Mensajes dinámicos con datos del cliente
- **Enlaces de pago**: Generación automática de URLs personalizadas

## 🚀 Instalación

### Requisitos previos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

1. **Clonar o descargar el repositorio:**
```bash
cd /home/sebastian/PycharmProjects/Proyectos_Next_Leap/aseguradora_mvp
```

2. **Crear un entorno virtual (recomendado):**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar las dependencias:**
```bash
pip install -r requirements.txt
```

### Dependencias

El archivo `requirements.txt` incluye:
- `streamlit>=1.28.0` - Framework web para la aplicación
- `pandas>=2.0.0` - Manipulación y análisis de datos
- `twilio>=8.0.0` - Integración con WhatsApp (opcional, solo si usas modo producción)
- `plotly>=5.0.0` - Visualizaciones interactivas y gráficas dinámicas

## 📁 Estructura del Proyecto

```
aseguradora_mvp/
├── app.py                              # Aplicación principal y routing
├── modules/
│   ├── __init__.py                     # Inicialización del módulo
│   ├── login.py                        # Módulo de autenticación
│   ├── clientes.py                     # Módulo de gestión de clientes
│   ├── dashboard.py                    # Tablero de visualización ejecutivo
│   ├── cartera.py                      # Módulo de gestión de cartera
│   ├── renovaciones.py                 # Módulo de renovaciones
│   ├── notificaciones.py               # Sistema de envío de notificaciones
│   └── trazabilidad.py                 # Visualización de logs y trazabilidad
├── .streamlit/
│   ├── secrets.toml                    # Credenciales (no subir a Git)
│   └── secrets.toml.example            # Ejemplo de configuración
├── logs/                               # Directorio de logs (generado automáticamente)
│   └── notificaciones.jsonl            # Logs de notificaciones en formato JSONL
├── sabana_cartera_renovaciones_200cols.csv  # Archivo de datos principal
├── requirements.txt                    # Dependencias del proyecto
├── .gitignore                          # Archivos ignorados por Git
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
2. **Navegación**: Usa el menú lateral para acceder a los diferentes módulos:
   - **1. Clientes**: Busca y visualiza información detallada de clientes
   - **2. Tablero de Visualización**: Revisa métricas ejecutivas consolidadas
   - **3. Renovaciones**: Gestiona pólizas próximas a vencer y envía notificaciones
   - **4. Cartera**: Revisa mora por segmentos y gestiona notificaciones de cobro
   - **5. Trazabilidad**: Consulta el historial completo de notificaciones enviadas

### Casos de uso principales

#### Enviar notificaciones masivas de cartera
1. Ir al módulo **Cartera**
2. Seleccionar el segmento de mora deseado
3. Seleccionar el canal (Email o WhatsApp)
4. Revisar la tabla de clientes sin autorización (si existe)
5. Hacer clic en "Enviar Notificaciones Masivas"
6. Revisar el resumen y tabla de resultados

#### Enviar notificaciones de renovación
1. Ir al módulo **Renovaciones**
2. Seleccionar la ventana de renovación (7, 15 o 30 días)
3. Seleccionar el canal (Email o WhatsApp)
4. Revisar la tabla de clientes sin autorización (si existe)
5. Hacer clic en "Enviar Notificaciones Masivas"
6. Revisar el resumen y tabla de resultados

#### Consultar trazabilidad de un cliente
1. Ir al módulo **Trazabilidad**
2. Usar los filtros principales si se desea (Tipo, Canal, Estado)
3. En la sección "Trazabilidad por Cliente", ingresar nombre o documento
4. Revisar todas las notificaciones históricas del cliente en los expanders

#### Visualizar métricas ejecutivas
1. Ir al módulo **Tablero de Visualización**
2. Seleccionar la ventana de renovación para ver el estado
3. Seleccionar el segmento de mora para ver estadísticas de cartera
4. Analizar las visualizaciones interactivas

## 📊 Formato de Datos

La aplicación espera un archivo CSV (`sabana_cartera_renovaciones_200cols.csv`) con las siguientes columnas principales:

### Columnas requeridas:

**Identificación:**
- `id_cliente`, `id_poliza`
- `nombre_cliente`, `documento_cliente`
- `numero_poliza`

**Información de Póliza:**
- `producto`, `plan`
- `estado_poliza`, `segmento`
- `fecha_inicio_vigencia`, `fecha_fin_vigencia`
- `fecha_venc_factura`, `fecha_factura`
- `fecha_ultimo_pago`, `promesa_pago_fecha`

**Renovaciones:**
- `dias_para_vencimiento`
- `semáforo_vencimiento` (valores: Rojo, Amarillo, Verde o similares)
- `estado_renovacion`, `fecha_renovacion_estimada`
- `renovable` (true/false, 1/0, sí/no)

**Cartera:**
- `dias_mora`
- `valor_en_mora`
- `estado_pago`

**Contacto y Consentimientos:**
- `email_cliente`, `telefono_cliente`
- `consentimiento_email` (sí/no)
- `consentimiento_whatsapp` (sí/no)

Y otras columnas según necesidades del negocio.

## ⚙️ Configuración

### Variables de configuración en `app.py`:

- `DATA_PATH`: Ruta al archivo CSV de datos
- `BASE_PAGOS`: URL base para enlaces de pago (actualmente: `https://optimoconsultores.com/pagos/`)

### Configuración de Notificaciones (Modo Producción)

#### Modo Prototipo (Recomendado para desarrollo)
El sistema funciona por defecto en modo prototipo, simulando envíos exitosos sin requerir configuración adicional. Todos los envíos se registran en el sistema de trazabilidad.

#### Configuración para Envíos Reales

##### 1. Configurar Email (Gmail)

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

##### 2. Configurar WhatsApp (Twilio)

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

El sistema maneja automáticamente la ausencia de configuración, funcionando en modo prototipo.

## 📝 Logs y Trazabilidad

### Sistema de Logging

- **Formato**: JSONL (JSON Lines) - un registro por línea
- **Ubicación**: `logs/notificaciones.jsonl`
- **Información registrada**:
  - Timestamp de la notificación
  - Tipo (Cartera, Renovación, General)
  - Canal (Email, WhatsApp)
  - Estado (Enviado, Fallido, Bloqueado)
  - Información del destinatario
  - ID Cliente e ID Póliza
  - Mensaje completo enviado
  - Errores (si los hay)
  - Usuario que realizó el envío

### Visualización de Logs

Todos los logs son accesibles desde el módulo de **Trazabilidad**, donde puedes:
- Filtrar por tipo, canal y estado
- Buscar notificaciones por cliente
- Ver el detalle completo de cada notificación
- Revisar errores y bloqueos

## 🔒 Seguridad

⚠️ **Nota importante**: Este es un MVP. El sistema de autenticación actual es básico y no debe usarse en producción sin implementar:
- Validación real de credenciales contra base de datos
- Conexión a base de datos segura
- Encriptación de contraseñas (hashing con bcrypt/argon2)
- Tokens de sesión seguros (JWT)
- Logs de auditoría completos
- HTTPS obligatorio
- Rate limiting para APIs

### Buenas prácticas implementadas

- ✅ Validación de consentimientos antes de enviar notificaciones
- ✅ Manejo seguro de errores sin exponer información sensible
- ✅ Logging completo de todas las acciones
- ✅ Validación de formatos (email, teléfono)
- ✅ Archivo `.gitignore` para proteger credenciales

## 🚧 Limitaciones del MVP

- **Autenticación simulada**: No hay validación real contra base de datos
- **Datos en CSV**: No hay base de datos persistente
- **Sin persistencia de cambios**: Los datos se leen siempre del CSV original
- **Logs en archivo**: Los logs se guardan en JSONL local (no en base de datos)
- **Sin programación automática**: Las notificaciones se envían manualmente
- **Sin plantillas personalizables**: Los mensajes tienen formato predefinido

## 🔮 Próximos pasos (Fase 2)

### Funcionalidades completadas ✅
- [x] Sistema de envío de notificaciones (Email/WhatsApp)
- [x] Modo prototipo para desarrollo
- [x] Sistema de logs y trazabilidad completo
- [x] Dashboard ejecutivo con visualizaciones
- [x] Envío masivo de notificaciones personalizadas
- [x] Validación de consentimientos
- [x] Búsqueda avanzada en módulos
- [x] Visualizaciones interactivas con Plotly

### Pendientes para producción
- [ ] Integración con base de datos (PostgreSQL/MySQL)
- [ ] Sistema de autenticación real (OAuth2/JWT)
- [ ] Persistencia de cambios en base de datos
- [ ] API REST para integraciones externas
- [ ] Exportación de reportes (PDF, Excel)
- [ ] Programación automática de notificaciones (cron jobs)
- [ ] Plantillas personalizables de mensajes
- [ ] Sistema de notificaciones push en tiempo real
- [ ] Dashboard con métricas en tiempo real
- [ ] Integración con sistemas de pago reales
- [ ] Análisis predictivo de mora
- [ ] Recomendaciones automáticas de acción

## 👥 Roles de Usuario

- **Admin**: Acceso completo a todos los módulos y configuración
- **Cartera**: Enfoque en gestión de mora, pagos y envío de notificaciones de cobro
- **Renovaciones**: Enfoque en gestión de renovaciones y envío de recordatorios
- **Auditor**: Acceso de solo lectura para auditoría y revisión de trazabilidad

## 📄 Licencia

Este proyecto es un MVP desarrollado para propósitos internos y de demostración.

## 🤝 Contribuciones

Este es un proyecto MVP. Para mejoras o sugerencias, contactar al equipo de desarrollo.

---

**Desarrollado con ❤️ usando Streamlit, Pandas y Plotly**
