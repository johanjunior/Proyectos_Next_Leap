# RAG MVP - Plataforma de Consulta Documental

Plataforma RAG (Retrieval-Augmented Generation) con interfaz tipo chatbot para consultar y generar respuestas a partir de documentos propios de la empresa.

## Características

- 🔐 Autenticación con Google OAuth
- 💬 Interfaz de chat tipo chatbot
- 📚 Respuestas fundamentadas con fuentes verificables
- 🔗 Acceso directo a documentos originales mediante URLs firmadas
- 🚀 Arquitectura escalable con FastAPI y frontend React (Ant Design) o Streamlit

## Arquitectura

### Backend (FastAPI)
- **API REST** con FastAPI
- **Autenticación** con Google OAuth y JWT
- **Base de datos** SQLite (configurable)
- **Endpoints** para autenticación, chat, documentos y administración

### Frontend (React + Ant Design) — recomendado
- **Interfaz** con [Ant Design](https://ant.design/) (React, TypeScript, Vite)
- **Chat** con historial y fuentes documentales
- **Login** con Google; **visor de PDF** en modal para las fuentes
- Carpeta: `frontend_react/`

### Frontend (Streamlit) — legacy
- **Interfaz de chat** interactiva (Python/Streamlit)
- **Autenticación** integrada con Google
- Carpeta: `frontend/`

## Configuración

### Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
# Google OAuth
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret

# URLs
FRONTEND_URL=http://localhost:8501
BACKEND_URL=http://localhost:8000

# JWT
JWT_SECRET_KEY=tu-secret-key-super-segura
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database
DATABASE_URL=sqlite:///./rag_app.db
```

**Usar con ngrok (túnel público al frontend):** Si expones el frontend con `ngrok http 3000`, el backend acepta por defecto orígenes de `*.ngrok-free.app`, `*.ngrok.io` y `*.trycloudflare.com` (CORS con regex). No hace falta poner `CORS_EXTRA_ORIGINS` para esas URLs. El frontend sigue llamando al backend en `http://localhost:8000`; asegúrate de que `VITE_BACKEND_URL` (o el default en el frontend) sea `http://localhost:8000` si el backend corre en local.

Para **otros orígenes** (dominio propio, otro túnel), añade en `.env` del backend:
```env
CORS_EXTRA_ORIGINS=https://tu-dominio.com
```

**CORS con backend en túnel (Cloudflare, ngrok):** Si el backend está en una URL pública (p. ej. `https://xxx.trycloudflare.com`) y el frontend en otra (p. ej. `https://yyy.ngrok-free.app`), los orígenes de ngrok y trycloudflare están permitidos por defecto. Solo necesitas `CORS_EXTRA_ORIGINS` si el frontend se carga desde un origen que no sea localhost ni `*.ngrok-free.app` / `*.trycloudflare.com`.

**Probar desde el celular (frontend + backend vía ngrok):** En el celular, `localhost` es el propio teléfono, no tu PC. Por eso el frontend no puede conectarse a `http://localhost:8000`. Hay que exponer **también** el backend por ngrok:

1. **Dos túneles ngrok** (en dos terminales):
   - `ngrok http 3000` → URL frontend, p. ej. `https://aaaa.ngrok-free.app`
   - `ngrok http 8000` → URL backend, p. ej. `https://bbbb.ngrok-free.app`

2. **`.env` en la raíz del proyecto (backend):**
   ```env
   FRONTEND_URL=https://aaaa.ngrok-free.app
   BACKEND_URL=https://bbbb.ngrok-free.app
   ```
   Sustituye por tus URLs reales. `CORS_EXTRA_ORIGINS` no hace falta para orígenes ngrok/trycloudflare (ya permitidos por regex).

3. **Frontend que use la URL del backend:** En `frontend_react/` crea o edita `.env` o `.env.local` y pon:
   ```env
   VITE_BACKEND_URL=https://bbbb.ngrok-free.app
   ```
   Reinicia el dev server de Vite (`npm run dev`). Las variables `VITE_*` se leen al arrancar.

4. **Google OAuth:** En Google Cloud Console → Credenciales → tu cliente OAuth → **URI de redirección autorizados**, añade:
   ```
   https://bbbb.ngrok-free.app/auth/callback
   ```
   (la URL del **backend** ngrok, no del frontend).

5. Entra desde el celular a `https://aaaa.ngrok-free.app` (frontend). Login y API irán al backend vía `https://bbbb.ngrok-free.app`.

### Configuración de Google OAuth

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente OAuth**
4. Tipo de aplicación: **Aplicación web**
5. **URI de redirección autorizados**: debe ser **exactamente** `http://localhost:8000/auth/callback` (o `{BACKEND_URL}/auth/callback` si usas otra URL)
6. Copia el **Client ID** y **Client secret** al archivo `.env` en la raíz del proyecto
7. El archivo `.env` debe estar en la raíz del proyecto (mismo nivel que `backend/` y `frontend/`)

**Comprobar configuración:** Con el backend en marcha, abre `http://localhost:8000/auth/status`. Debe devolver `oauth_configured: true` y el `redirect_uri` que uses en Google Cloud.

### Roles y permisos

- **Administrador (`admin`)**: control total; gestión de usuarios, permisos y auditoría.
- **Usuario (`user`)**: mínimo privilegio; solo lo que el admin habilite.

**Bootstrap de admins:** en `.env` define `ADMIN_EMAILS` (emails separados por coma). Esos usuarios tendrán rol `admin` al crear cuenta o en el siguiente login:

```env
ADMIN_EMAILS=admin@example.com,otro@example.com
```

**Migración (roles, permisos, auditoría):** antes de usar el sistema de roles, ejecuta una vez:

```bash
python -m backend.scripts.migrate_roles_permissions
```

Añade `users.role`, crea `user_permissions`, adapta `agent_messages` (user_email, request_id, session_id) y elimina filas assistant antiguas.

**Migración (columna sources para historial):** si la tabla `agent_messages` ya existía sin la columna `sources` y quieres que al cambiar de agente se vean también las respuestas del bot (y fuentes), ejecuta una vez:

```bash
python -m backend.scripts.migrate_add_sources_column
```

## Instalación

1. Instala las dependencias:

```bash
pip install -r requirements.txt
```

2. Asegúrate de tener las variables de entorno configuradas en `.env`

3. Inicializa la base de datos (se crea automáticamente al iniciar el backend)

## Uso

### Iniciar el Backend

**IMPORTANTE:** 
1. Primero activa el entorno conda `rag-mvp`
2. El backend debe ejecutarse desde la raíz del proyecto (no desde el directorio `backend/`)

```bash
# Activar el entorno conda
conda activate rag-mvp

# Desde la raíz del proyecto (RAG/)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

El backend estará disponible en `http://localhost:8000`
Documentación de la API: `http://localhost:8000/docs`

### Ver logs del backend en tiempo real

**Opción A – En primer plano (recomendado)**  
Ejecuta el backend en una terminal y **no** lo pongas en background. Los logs se imprimen ahí mismo:

```bash
conda activate rag-mvp
cd /ruta/al/proyecto/RAG   # raíz del proyecto
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Deja esa terminal abierta. Verás en vivo cada request, errores y mensajes del RAG.

**Opción B – Guardar en archivo y seguir con `tail -f`**  
Si prefieres correrlo en background, redirige la salida a un archivo y en **otra terminal** haz:

```bash
# Terminal 1: iniciar backend y escribir en backend.log
conda activate rag-mvp
cd /ruta/al/proyecto/RAG
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 2>&1 | tee backend.log

# Terminal 2: seguir el log en tiempo real
tail -f backend.log
```

**Opción C – Solo archivo (backend en background)**  
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
# En otra terminal:
tail -f backend.log
```

### LLM (OpenRouter) y filtrado por metadata

**¿Se usa la API de OpenAI?**  
No. El chat usa **OpenRouter** (p. ej. `deepseek/deepseek-r1-0528:free`). Los logs pueden mostrar `openai` o `openai._base_client` porque LlamaIndex usa un cliente compatible con la API de OpenAI para llamar a OpenRouter.

**Error 429 (rate limit)**  
El modelo gratuito de OpenRouter tiene límites. Si ves `429 Too Many Requests` o "Rate limit exceeded: free-models-per-day":
- Espera un rato o prueba más tarde.
- Añade créditos en [OpenRouter](https://openrouter.ai/settings/credits) o usa tu propia API key del proveedor.

**Error 400 de Qdrant: "Index required but not found for nombre/sede/..."**  
El filtrado por metadata (`nombre`, `sede`, `radicado`, etc.) usa índices de tipo **keyword** en Qdrant. Si la colección no tiene esos índices, Qdrant devuelve 400.

- **Solución rápida:** desactivar el filtro. En `.env` pon `USE_METADATA_FILTER=false` (por defecto ya está desactivado). Solo se hace búsqueda vectorial, sin filtros por metadata.
- **Para usar filtros:** crea los índices una vez y luego activa el filtro:
  ```bash
  conda activate rag-mvp
  cd /ruta/al/proyecto/RAG
  python backend/scripts/create_qdrant_payload_indexes.py
  ```
  Luego en `.env`: `USE_METADATA_FILTER=true`.

### Iniciar el Frontend

**Opción A – React + Ant Design (recomendado)**

1. En la raíz del proyecto, en `.env`, pon `FRONTEND_URL=http://localhost:3000` para que el login con Google redirija al frontend React.
2. Instala y arranca el frontend:

```bash
cd frontend_react
npm install
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000). El backend debe estar corriendo en `http://localhost:8000`.

**Opción B – Streamlit (legacy)**

Asegúrate de tener el entorno conda `rag-mvp` activado y `FRONTEND_URL=http://localhost:8501` en `.env` si usas este frontend.

```bash
conda activate rag-mvp
streamlit run frontend/app.py
```

El frontend estará disponible en `http://localhost:8501`.

**Nota:** Asegúrate de que el backend esté corriendo antes de iniciar el frontend.

## Flujo de Autenticación

1. El usuario accede al frontend
2. Se muestra la página de login con botón de Google
3. Al hacer clic, se redirige a Google para autenticación
4. Google redirige al backend (`/auth/callback`) con código de autorización
5. El backend intercambia el código por ID token y crea JWT
6. El backend redirige al frontend con el JWT token
7. El frontend almacena el token y muestra la interfaz principal

## Estructura del Proyecto

```
rag-mvp/
├── backend/
│   ├── main.py              # FastAPI entrypoint
│   ├── api/                 # Endpoints
│   │   ├── routes_auth.py   # Autenticación
│   │   ├── routes_chat.py   # Chat/RAG
│   │   ├── routes_docs.py   # Documentos
│   │   └── routes_admin.py  # Administración
│   ├── security/            # Seguridad
│   │   ├── jwt.py           # JWT tokens
│   │   └── deps.py          # Dependencias de auth
│   ├── db/                  # Base de datos
│   │   ├── models.py        # Modelos SQLAlchemy
│   │   └── session.py       # Sesión de BD
│   └── ...
├── frontend/
│   ├── app.py               # Streamlit app principal
│   ├── auth/                # Autenticación
│   │   └── client.py        # Cliente OAuth
│   ├── components/          # Componentes UI
│   │   ├── chat.py          # Interfaz de chat
│   │   └── sources.py       # Visualización de fuentes
│   └── config.py            # Configuración
└── requirements.txt
```

## Próximos Pasos

- [ ] Integración con Vector DB (LlamaIndex)
- [ ] Integración con Hetzner Object Storage
- [ ] Implementación completa del motor RAG
- [ ] Sistema de OCR para documentos
- [ ] Almacenamiento de historial de conversaciones
- [ ] Panel de administración

## Notas

- El sistema de RAG y Vector DB se implementará en fases posteriores
- La conexión con Hetzner Object Storage ya está preparada pero no se utiliza en esta fase
- La base de datos SQLite se puede cambiar por PostgreSQL u otra BD configurando `DATABASE_URL`
