# RAG Frontend (React + Ant Design)

Frontend del asistente documental RAG: React, TypeScript, Vite y [Ant Design](https://ant.design/).

## Requisitos

- Node.js 18+
- npm o yarn

## Configuración

1. Copia `.env.example` a `.env` y ajusta si es necesario:
   - `VITE_BACKEND_URL`: URL del backend (por defecto `http://localhost:8000`).

2. En el **backend** (raíz del proyecto), configura en `.env`:
   - `FRONTEND_URL=http://localhost:3000` para que el login con Google redirija al frontend React.

## Instalación

```bash
cd frontend_react
npm install
```

## Desarrollo

### Con Node.js local

```bash
npm run dev
```

### Con Docker (sin instalar Node en la máquina)

1. Instalar dependencias (solo la primera vez o al cambiar `package.json`):

```bash
docker run --rm -v "$PWD":/app -w /app node:lts-alpine npm install
```

2. Arrancar el servidor de desarrollo **publicando el puerto** y exponiendo el host para que Vite escuche en `0.0.0.0`:

```bash
docker run --rm -it -p 3000:3000 -v "$PWD":/app -w /app node:lts-alpine npm run dev
```

Abre [http://localhost:3000](http://localhost:3000) en el navegador de tu laptop.

**Importante:** Sin `-p 3000:3000` el puerto 3000 solo existe dentro del contenedor y no podrás acceder desde el host. El `vite.config.ts` ya tiene `host: true` para que el servidor acepte conexiones desde fuera del contenedor.

## Build

```bash
npm run build
```

Salida en `dist/`. Para previsualizar:

```bash
npm run preview
```

## Estructura

- `src/pages/` — Login, Chat
- `src/components/` — MessageList, SourceList, PdfViewerModal
- `src/auth/` — AuthContext (token, usuario, login/logout)
- `src/api/` — Cliente HTTP (auth, chat)
