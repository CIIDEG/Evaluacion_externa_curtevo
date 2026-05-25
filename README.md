# Centro de Evaluación Cutervo

Portal web para la **Evaluación Final Externa** del proyecto *“Mejora de las oportunidades de inserción sociolaboral juvenil en Cutervo, Cajamarca, Perú”* (Expediente SOLPCD/2024/0118 — Generalitat Valenciana).

- Biblioteca documental del proyecto (descargas).
- Encuestas online para estudiantes y docentes.
- Panel de administración con exportación a CSV/Excel.
- Dashboard de avance del cronograma 12 semanas.
- HTTPS automático con Caddy + Let’s Encrypt.
- Versionado en GitHub con auto-despliegue al VPS de Hostinger.

## Arquitectura

```
┌─────────────────────────────────────────────┐
│  GitHub  →  push main  →  GitHub Actions    │
└──────────────────┬──────────────────────────┘
                   │  ssh + docker compose
                   ▼
┌─────────────────────────────────────────────┐
│  VPS Hostinger (Ubuntu 22.04)               │
│  ┌──────────┐    ┌──────────┐               │
│  │  Caddy   │ →  │ FastAPI  │ → SQLite      │
│  │ :80/:443 │    │  :8000   │   (volumen)   │
│  └──────────┘    └──────────┘               │
└─────────────────────────────────────────────┘
```

## Requisitos

- Cuenta GitHub.
- VPS Hostinger (ya lo tienes: `srv1153576.hstgr.cloud` — `31.97.86.140`).
- Subdominio apuntando al VPS (ej.: `cutervo.metacalidad.cloud` → `A` → `31.97.86.140`).

## 1. Configuración del repositorio en GitHub

```bash
# en tu PC, dentro de cutervo-eval-portal/
git init
git add .
git commit -m "Centro de Evaluación Cutervo - versión inicial"
git branch -M main
git remote add origin https://github.com/<TU-USUARIO>/cutervo-eval-portal.git
git push -u origin main
```

## 2. Preparación del VPS (una sola vez)

Entra por SSH:

```bash
ssh root@31.97.86.140
```

Y ejecuta:

```bash
# Docker + git
curl -fsSL https://get.docker.com | sh
apt-get install -y git docker-compose-plugin

# Carpeta de la app
mkdir -p /opt/cutervo
cd /opt/cutervo
git clone https://github.com/<TU-USUARIO>/cutervo-eval-portal.git .

# Variables de entorno
cp .env.example .env
nano .env   # edita ADMIN_USER, ADMIN_PASS, DOMAIN

# Levantar
docker compose up -d --build
```

Visita `https://<TU-DOMINIO>` — Caddy emitirá el certificado SSL automáticamente.

## 3. DNS (en Hostinger)

Crea un registro **A**:

| Tipo | Nombre   | Valor          | TTL  |
|------|----------|----------------|------|
| A    | cutervo  | 31.97.86.140   | 3600 |

Espera 5-10 minutos a la propagación.

## 4. Auto-despliegue vía GitHub Actions

En GitHub → tu repo → **Settings → Secrets and variables → Actions** crea:

| Secret           | Valor                                      |
|------------------|--------------------------------------------|
| `VPS_HOST`       | `31.97.86.140`                             |
| `VPS_USER`       | `root` (o usuario que crees)               |
| `VPS_SSH_KEY`    | Clave privada SSH (ver más abajo)          |
| `VPS_APP_PATH`   | `/opt/cutervo`                             |

### Generar la clave SSH

En tu PC:
```bash
ssh-keygen -t ed25519 -C "github-actions" -f cutervo_deploy
# sube la pública al VPS
ssh-copy-id -i cutervo_deploy.pub root@31.97.86.140
# pega el CONTENIDO de cutervo_deploy (privada) en el secret VPS_SSH_KEY
```

Cada `push` a `main` actualizará automáticamente el portal en el VPS.

## 5. Estructura del repositorio

```
cutervo-eval-portal/
├── app/                    Código FastAPI
│   ├── main.py             Entry point
│   ├── database.py         SQLite engine
│   ├── models.py           ORM models
│   ├── routes/             Endpoints
│   ├── templates/          Jinja2 HTML
│   └── static/             CSS, imágenes
├── docs/                   Documentos descargables
├── data/                   Volumen SQLite (no se versiona)
├── docker-compose.yml
├── Dockerfile
├── Caddyfile               Configuración HTTPS
├── .env.example
├── .github/workflows/deploy.yml
├── install.sh
└── update.sh
```

## 6. Uso

- `https://<dominio>/`               → Portada con info del proyecto.
- `https://<dominio>/documentos`     → Biblioteca documental.
- `https://<dominio>/encuesta/estudiantes` → Cuestionario estudiantes.
- `https://<dominio>/encuesta/docentes`    → Cuestionario docentes.
- `https://<dominio>/admin`          → Panel (HTTP Basic Auth).
- `https://<dominio>/admin/export/<form>.xlsx` → Descarga de respuestas.

## 7. Personalización

Para añadir documentos: cópialos a `docs/` y haz push — quedarán disponibles en la biblioteca al recargar.

Para modificar las preguntas: edita `app/routes/surveys.py` (las preguntas son una lista). Se versiona en Git automáticamente.

## Licencia

Uso interno del consorcio IS-IPP y del equipo evaluador. © 2026.
