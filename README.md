# KLKCHAN API

API tipo imageboard/forum construida con **FastAPI**.  
Autenticación JWT, gestión de usuarios, boards, posts, comments, votación y moderación de contenido multilenguaje (ES/EN).

> Estado actual: `v0.1.1` · **170/170 tests OK** · cobertura ≈ **95%** ✅  
> Próximo milestone: migración a **Supabase / PostgreSQL**

---

## ✨ Features

- **Auth completo**: register, login (OAuth2), refresh token, change-password, forgot/reset-password (JWT de un solo uso), logout con revocación de token.
- **RBAC**: roles `user / mod / admin` con scopes granulares.
- **Users**: CRUD completo + auto-eliminación con cascade.
- **Boards / Posts / Comments**: CRUD con relaciones embebidas, paginación cursor-based y cascade delete.
- **Votación**: sistema de votos `-1 / 0 / 1` por post y comment.
- **Moderación**: queue real, acciones (ban/remove), reports. Filtro multilenguaje (ES/EN) con **LDNOOBW** + normalización leet-speak.
- **Admin**: gestión de usuarios, asignación de roles, stats globales.
- **Rate limiting**: SlowAPI — límites por endpoint (GET: 60/min, escritura: 30/min, auth: 5/min).
- **Seguridad**: bcrypt, token blacklist, ownership guards, OpenAPI desactivado en producción.

---

## 🧱 Stack

| Capa          | Tecnología                              |
| ------------- | --------------------------------------- |
| Framework     | FastAPI + Uvicorn                       |
| Validación    | Pydantic v2                             |
| Auth          | python-jose + passlib (bcrypt)          |
| Rate limiting | SlowAPI                                 |
| Testing       | pytest + httpx (TestClient)             |
| Lenguaje      | Python 3.13                             |
| Storage       | JSON (migración a Supabase planificada) |

---

## 🚀 Quickstart

```bash
# 1. Entorno virtual (recomendado)
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 2. Dependencias
pip install -r requirements.txt

# 3. Variables de entorno
cp .env.example .env
# Edita .env y genera tu SECRET_KEY:
python -c "import secrets; print(secrets.token_hex(32))"

# 4. Levantar el servidor
uvicorn app.app:app --reload
# Swagger UI: http://127.0.0.1:8000/docs
```

---

## ⚙️ Variables de entorno

Ver `.env.example` en la raíz del proyecto. Variables requeridas:

| Variable                      | Requerida | Default       | Descripción                                   |
| ----------------------------- | --------- | ------------- | --------------------------------------------- |
| `SECRET_KEY`                  | ✅ Sí     | —             | Clave JWT. Genera con `secrets.token_hex(32)` |
| `ALGORITHM`                   | No        | `HS256`       | Algoritmo de firma JWT                        |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No        | `15`          | Duración access token                         |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | No        | `7`           | Duración refresh token                        |
| `JWT_ISS`                     | No        | `klkchan`     | Issuer del JWT                                |
| `ENVIRONMENT`                 | No        | `development` | `development` o `production`                  |
| `ALLOWED_ORIGINS`             | No        | localhost     | Orígenes CORS (producción)                    |
| `ADMIN_EMAILS`                | No        | —             | Emails con rol admin al registrarse           |
| `MOD_EMAILS`                  | No        | —             | Emails con rol mod al registrarse             |

> En `ENVIRONMENT=production` los endpoints `/docs` y `/redoc` quedan desactivados.

---

## 📡 Endpoints

### Auth `/auth`

| Método | Ruta                        | Auth | Descripción                                   |
| ------ | --------------------------- | ---- | --------------------------------------------- |
| POST   | `/auth/register`            | No   | Registro de usuario                           |
| POST   | `/auth/login`               | No   | Login OAuth2 → JWT pair                       |
| POST   | `/auth/refresh`             | No   | Refresh token → nuevo access token            |
| PATCH  | `/auth/change-password`     | JWT  | Cambiar contraseña + revocar token            |
| POST   | `/auth/logout`              | JWT  | Logout + revocar token                        |
| POST   | `/auth/forgot-password`     | No   | Genera token de reset (devuelto en respuesta) |
| POST   | `/auth/reset-password`      | No   | Resetear contraseña con token de un solo uso  |
| POST   | `/auth/verify-email`        | No   | _(pendiente — Supabase Auth)_                 |
| POST   | `/auth/resend-verification` | No   | _(pendiente — Supabase Auth)_                 |

### Users `/users`

| Método | Ruta          | Auth  | Descripción                   |
| ------ | ------------- | ----- | ----------------------------- |
| GET    | `/users`      | No    | Lista paginada de usuarios    |
| GET    | `/users/me`   | JWT   | Perfil propio                 |
| GET    | `/users/{id}` | No    | Perfil público                |
| PUT    | `/users/{id}` | JWT   | Actualizar perfil (ownership) |
| DELETE | `/users/me`   | JWT   | Auto-eliminación + cascade    |
| DELETE | `/users/{id}` | Admin | Admin elimina usuario         |

### Boards `/boards`

| Método | Ruta           | Auth | Descripción                  |
| ------ | -------------- | ---- | ---------------------------- |
| GET    | `/boards`      | No   | Lista con post_count         |
| GET    | `/boards/{id}` | No   | Board individual             |
| POST   | `/boards`      | JWT  | Crear board                  |
| PUT    | `/boards/{id}` | JWT  | Actualizar board (ownership) |
| DELETE | `/boards/{id}` | JWT  | Eliminar + cascade           |

### Posts `/posts`

| Método | Ruta                   | Auth | Descripción                     |
| ------ | ---------------------- | ---- | ------------------------------- |
| GET    | `/posts`               | No   | Lista con comentarios embebidos |
| GET    | `/posts/{id}`          | No   | Post con comentarios            |
| POST   | `/posts`               | JWT  | Crear post                      |
| PUT    | `/posts/{id}`          | JWT  | Actualizar (ownership)          |
| DELETE | `/posts/{id}`          | JWT  | Eliminar + cascade              |
| GET    | `/posts/{id}/comments` | No   | Comentarios paginados           |

### Comments `/comments`

| Método | Ruta             | Auth | Descripción            |
| ------ | ---------------- | ---- | ---------------------- |
| GET    | `/comments`      | No   | Paginación por post_id |
| POST   | `/comments`      | JWT  | Crear comentario       |
| DELETE | `/comments/{id}` | JWT  | Eliminar (ownership)   |

### Interactions `/interactions`

| Método | Ruta                              | Auth     | Descripción        |
| ------ | --------------------------------- | -------- | ------------------ |
| POST   | `/interactions/votes`             | JWT      | Votar (-1 / 0 / 1) |
| GET    | `/interactions/votes/{type}/{id}` | Opcional | Resumen de votos   |

### Admin `/admin`

| Método | Ruta                     | Auth  | Descripción                |
| ------ | ------------------------ | ----- | -------------------------- |
| GET    | `/admin/users`           | Admin | Lista paginada de usuarios |
| PATCH  | `/admin/users/{id}/role` | Admin | Asignar/quitar roles       |
| GET    | `/admin/stats`           | Admin | Stats globales             |
| DELETE | `/admin/users/{id}`      | Admin | Eliminar usuario           |

### Moderation `/moderation`

| Método | Ruta                  | Auth | Descripción                  |
| ------ | --------------------- | ---- | ---------------------------- |
| GET    | `/moderation/queue`   | Mod  | Cola de moderación           |
| POST   | `/moderation/actions` | Mod  | Ejecutar acción (ban/remove) |
| POST   | `/moderation/reports` | JWT  | Crear reporte                |
| GET    | `/moderation/reports` | Mod  | Lista de reportes            |

### System

| Método | Ruta      | Auth | Descripción  |
| ------ | --------- | ---- | ------------ |
| GET    | `/health` | No   | Health check |
| GET    | `/`       | No   | Root status  |

---

## 🔐 Autenticación en Swagger UI

1. Ir a `http://127.0.0.1:8000/docs`
2. Ejecutar `POST /auth/login` con tu `username` y `password`
3. Copiar el `access_token` de la respuesta
4. Click en **Authorize 🔒** (arriba a la derecha)
5. Pegar el token como: `Bearer <token>`
6. Click en **Authorize** → **Close**

El token dura 15 minutos. Al expirar, repetir el login.

---

## 🧪 Tests

```bash
# Correr toda la suite
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ --cov=app --cov-report=term-missing
```

| Archivo                       | Tests   | Área                     |
| ----------------------------- | ------- | ------------------------ |
| test_auth_extended.py         | 14      | Flujos de auth completos |
| test_roles.py                 | 17      | RBAC completo            |
| test_forgot_reset_password.py | —       | Reset password flow      |
| test_security_ownership.py    | 10      | Ownership checks         |
| test_token_blacklist.py       | 7       | Revocación de tokens     |
| test_votes.py                 | 10      | Sistema de votos         |
| test_moderation.py            | 10      | Acciones de moderación   |
| test_moderation_queue.py      | —       | Queue real               |
| test_rate_limiting.py         | —       | Rate limiting 429        |
| test_cascade_delete.py        | 6       | Cascade deletes          |
| test_boards.py                | 11      | CRUD boards              |
| test_banned_words.py          | 11      | Filtro multilenguaje     |
| ...                           | ...     | ...                      |
| **TOTAL**                     | **170** |                          |

---

## 🗺️ Roadmap

- [x] Sprint 1 — Limpieza y seguridad básica
- [x] Sprint 2 — Rate limiting global, forgot/reset password, moderation queue, DRY refactor
- [ ] Sprint 2 — CI con GitHub Actions
- [ ] Sprint 3 — Migración a Supabase / PostgreSQL
- [ ] Sprint 4 — Dockerfile, logging estructurado, métricas Prometheus
- [ ] Backlog — Búsqueda full-text, adjuntos, subscripciones, notificaciones en tiempo real

---

## 📁 Estructura del proyecto

```
Klkchan-1/
├── app/
│   ├── app.py              ← Punto de entrada (FastAPI + middlewares)
│   ├── deps.py             ← Guards de autenticación y autorización
│   ├── services.py         ← Capa de repositorio (lógica de datos)
│   ├── schemas/
│   │   └── schemas.py      ← Modelos Pydantic v2
│   ├── routers/            ← Endpoints por módulo (11 archivos)
│   ├── utils/              ← security, limiter, roles, helpers, content,
│   │                          banned_words, token_blacklist
│   ├── data/
│   │   └── ldnoobw/        ← Diccionarios ES/EN para moderación
│   └── docs/
│       └── Claude.md       ← Reglas de flujo de trabajo para Claude Code
├── tests/
│   ├── conftest.py         ← Fixtures + seed data
│   └── test_*.py (×19)     ← 170 tests
├── .env.example            ← Variables de entorno documentadas
├── requirements.txt        ← Dependencias con versiones pineadas
└── README.md
```

---

## 📝 Notas

- **Storage temporal**: el proyecto usa `data.json` como almacenamiento. La migración a Supabase/PostgreSQL eliminará las race conditions actuales y permitirá múltiples workers.
- **Email**: `forgot-password` devuelve el `reset_token` directamente en la respuesta JSON. En producción se enviará por email tras la integración con Supabase Auth.
- **Tests locales**: los tests usan un archivo JSON temporal en `tests/_tmp/` que se limpia automáticamente entre ejecuciones.
