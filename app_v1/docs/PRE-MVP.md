# KLKCHAN — Pre-MVP Plan (v0.10.0-alpha.1)

## 1) Alcance
- Auth: register, login, change/forgot/reset password.
- Users: CRUD básico (sin admin UI).
- Boards/Posts/Comments: creación + listado, relación con usuario.
- Moderation: remove post/comment, ban user (JSON store).
- Filtro de palabras (ES/EN) en boards/posts/comments/users.

## 2) Criterios de salida
- Todos los endpoints del OpenAPI responden 2xx/4xx esperados.
- Cobertura de tests smoke para rutas críticas.
- Sin errores en logs al ejecutar 30 min con uso básico.
- CHANGELOG.md actualizado y tag `v0.10.0-alpha.1` creado.

## 3) Pendientes / Riesgos
- Persistencia JSON → migración a DB (Postgres/SQLite).
- Rate limiting y throttling (Auth/Posts).
- Emails reales para reset password (mock en dev).
- Moderation UI/cola real (placeholder por ahora).

## 4) QA Checklist (Smoke)
- Auth: register/login/logout/reset.
- Users: create/update (password hash), get by id, list.
- Boards: create + list (posts embebidos por board).
- Posts: create + list, comments embebidos.
- Comments: create.
- Moderation: actions (remove post/comment, ban user).
- Filtro: rechaza posts/comments con palabras baneadas.

## 5) Cómo correr
```bash
uvicorn app.app:app --reload
```

## 6) Entregables
- CHANGELOG.md
- Endpoint Matrix (CSV/MD)
- Tag v0.10.0-alpha.1 (pre-release)
