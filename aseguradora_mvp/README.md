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
- Generación de mensajes de notificación personalizados
- Enlaces de pago dinámicos
- Información de consentimientos para comunicación

### ♻️ Módulo de Renovaciones
- Ventanas de renovación configurables (7, 15, 30 días)
- Filtrado de pólizas renovables
- Generación de mensajes de renovación
- Soporte para múltiples canales (Email, WhatsApp)
- Validación de consentimientos por canal

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
pip install streamlit pandas
```

O crear un archivo `requirements.txt` con:
```
streamlit>=1.28.0
pandas>=2.0.0
```

Y luego instalar:
```bash
pip install -r requirements.txt
```

## 📁 Estructura del Proyecto

```
aseguradora_mvp/
├── app.py                              # Aplicación principal
├── modules/
│   ├── __init__.py                     # Inicialización del módulo
│   ├── login.py                        # Módulo de autenticación
│   ├── clientes.py                     # Módulo de gestión de clientes
│   ├── cartera.py                      # Módulo de gestión de cartera
│   └── renovaciones.py                 # Módulo de renovaciones
├── sabana_cartera_renovaciones_200cols.csv  # Archivo de datos
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
- Notificaciones simuladas (no hay envío real)
- Sin persistencia de cambios (los datos se leen del CSV)

## 🔮 Próximos pasos (Fase 2)

- [ ] Integración con base de datos
- [ ] Sistema de autenticación real
- [ ] Envío real de notificaciones (Email/WhatsApp)
- [ ] Logs de auditoría
- [ ] Persistencia de cambios
- [ ] Dashboard con métricas agregadas
- [ ] Exportación de reportes

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
