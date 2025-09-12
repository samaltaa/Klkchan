# ✅ KLKCHAN API Models

Este documento describe las validaciones esperadas y su estado de implementación actual según el diseño del sistema.

---

## 🔐 Validaciones de usuarios

| Validación                                      | Estado                         |
|-------------------------------------------------|--------------------------------|
| Formato de correo (EmailStr)                    | ✅ Implementado                |
| Unicidad de usuario (username único)            | ✅ Implementado *(register/update)* |
| Complejidad de contraseña                       | ⚠️ Parcial *(en change-password)* |
| Longitud mínima/máxima de username              | ✗ Falta                        |
| URL de avatar válida                            | ✗ Falta                        |
| Edad mínima                                     | ✗ Falta                        |
| Aceptación de términos                          | ✗ Falta                        |

**Siguientes pasos (Usuarios)**  
- Aplicar `check_password_policy` también en **register**.  
- Añadir validación **min/max** para `username` (pydantic `constr`).  
- (Opcional) Campo `avatar_url` con validación de **URL**.  
- (Opcional) Campo `birthdate` + regla de **edad mínima**.  
- Campo `accepted_terms_at` (datetime) y verificación en registro.

---

## 📝 Validaciones de posts

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Título no vacío y longitud mínima/máxima        | ✗ Falta    |
| Contenido no vacío y longitud mínima/máxima     | ✗ Falta    |
| Número de etiquetas (tags) máx/min              | ✗ Falta    |
| Formato de URL en enlaces o imágenes            | ✗ Falta    |
| Existencia de la comunidad referenciada         | ✗ Falta    |

**Siguientes pasos (Posts)**  
- Restringir `title/body` con min/max (pydantic) y trims.  
- Validar `board_id` existente antes de crear el post.  
- (Opcional) Validar **URLs** en contenido/attachments.  
- Añadir `tags: List[str]` con **límite** y normalización.

---

## 💬 Validaciones de comentarios

| Validación                                      | Estado            |
|-------------------------------------------------|-------------------|
| Longitud mínima/máxima del comentario           | ✗ Falta           |
| Prohibición de palabras                         | ✅ Implementado    |
| Profundidad de anidamiento máxima               | ✗ Falta           |

**Siguientes pasos (Comentarios)**  
- Min/max de `body` (pydantic).  
- Si habrá threads, controlar **profundidad** (p.ej. 3 niveles).  
- (Opcional) Flood-control/cooldown por usuario.

---

## 👍 Validaciones de interacción

| Validación                                      | Estado  |
|-------------------------------------------------|---------|
| Valores de voto permitidos (-1, +1)             | ✗ Falta |
| Formato de flairs                               | ✗ Falta |
| Límite de votos por usuario                     | ✗ Falta |

**Siguientes pasos (Interacción)**  
- Endpoint de **vote** que solo acepte `{-1, +1}` y **idempotencia**.  
- Esquema de **flairs** (lista blanca) + validación por board.  
- Límite de votos por usuario / recurso (antifraude básico).

---

## ⚙️ Validaciones generales

| Validación                                      | Estado                         |
|-------------------------------------------------|--------------------------------|
| Campos obligatorios (no null)                   | ✅ Parcial *(esquemas base)*   |
| Tipos de datos correctos                        | ✅ Parcial *(pydantic)*        |
| Timestamps válidos                              | ✗ Falta                        |
| Integridad referencial (FKs)                    | ✗ Falta                        |

**Siguientes pasos (Generales)**  
- Estandarizar `created_at/updated_at` en **UTC ISO-8601**.  
- Verificación de FK (`board_id`, `user_id`) en servicios.  
- (A futuro DB) constraints reales con SQLAlchemy.

---

## 🔒 Seguridad y abuso

| Validación                                      | Estado       |
|-------------------------------------------------|--------------|
| Rate-limiting (peticiones por IP/usuario)       | ✗ Falta      |
| Protección CSRF                                 | ✗ Falta      |
| Sanitización anti-XSS                           | ✗ Falta      |
| CAPTCHA / reCAPTCHA                             | ✗ Falta      |
| Detección de spam                               | ✗ Falta      |
| Bloqueo de IPs o usuarios                       | ⚠️ Parcial *(ban_user)* |

**Siguientes pasos (Seguridad)**  
- Rate limit con `slowapi`/NGINX (auth y escritura).  
- Sanitizar HTML/markdown (si se habilita) con **bleach**.  
- reCAPTCHA/HCaptcha en endpoints públicos sensibles.  
- Shadowban / bloqueo por IP (lista/regex) y auditoría.

---

## 📁 Archivos y multimedia

| Validación                                      | Estado  |
|-------------------------------------------------|---------|
| Tipo de archivo permitido (imágenes, vídeos)    | ✗ Falta |
| Tamaño máximo de archivo                        | ✗ Falta |
| Dimensiones mín/máx de imágenes                 | ✗ Falta |
| Validación de formatos MIME                     | ✗ Falta |

**Siguientes pasos (Archivos)**  
- Validar **MIME** real + extensión, `max_size`, dimensiones.  
- Thumbnailer y sanitización de metadatos (EXIF).  
- Storage (local/S3) + límites por recurso/usuario.

---

## 🌐 URL, slugs y rutas

| Validación                                      | Estado  |
|-------------------------------------------------|---------|
| Slugs únicos para posts/comunidades             | ✗ Falta |
| Longitud y caracteres válidos en slugs          | ✗ Falta |
| Validación de URLs externas                     | ✗ Falta |

**Siguientes pasos (Slugs/URLs)**  
- Generador de **slug** único (p.ej. `slugify(title)` + dedupe).  
- Validación de **URL** con lista blanca de esquemas/domains.

---

## 🛡 Moderación y roles

| Validación                                      | Estado                         |
|-------------------------------------------------|--------------------------------|
| Permisos según rol (usuario/mod/admin)          | ✅ Implementado *(router/moderation)* |
| Estado de aprobación de contenido               | ✗ Falta                        |
| Verificación de flairs válidos                  | ✗ Falta                        |

**Siguientes pasos (Moderación/Roles)**  
- Extender `require_role` a endpoints sensibles (edits/deletes).  
- Añadir estado `approved/pending/removed` a posts/comments.  
- Cola de reports + log de acciones (auditoría).

---

## 🔐 Autenticación y cuenta

| Validación                                      | Estado                                   |
|-------------------------------------------------|------------------------------------------|
| Formato y unicidad de tokens JWT                | ✅ Parcial *(claims/firmas OK; unicidad N/A)* |
| Caducidad de sesiones y tokens                  | ✅ Implementado                           |
| Validación de reset de contraseña (token)       | ✗ Falta                                  |
| Verificación de email                           | ✗ Falta                                  |

**Siguientes pasos (Auth)**  
- Implementar **reset token** (scope + exp) y endpoint real.  
- Verificación de **email** (link con token).  
- (Opcional) Revocación de tokens (lista negra/jti).

---

## 📜 Reglas de negocio

| Validación                                      | Estado  |
|-------------------------------------------------|---------|
| Cooldown entre operaciones                      | ✗ Falta |
| Máximo de votos por recurso                     | ✗ Falta |
| Límite de anidamiento de comentarios            | ✗ Falta |
| Límite de subidas de archivos por recurso       | ✗ Falta |

**Siguientes pasos (Negocio)**  
- Cooldown por usuario en creación de contenido.  
- Límite global por recurso (votes, uploads, etc.).  
- Política de anidamiento y auto-archivado de hilos.

---

## 🌍 Internacionalización

| Validación                                      | Estado                         |
|-------------------------------------------------|--------------------------------|
| Validación de campos multilenguaje (UTF-8)      | ✅ Parcial *(email & filtro LDNOOBW)* |
| Formato de fechas/monedas según locale          | ✗ Falta                        |

**Siguientes pasos (i18n)**  
- Normalización sistemática (NFKC) en entradas de texto.  
- Localización de timestamps (presentación) y mensajes.

---

### ✅ Notas adicionales

- Los endpoints **Auth**, **Users**, **Boards**, **Posts**, **Comments** están **funcionales**; Moderation activo (filtro) y router de acciones mínimas (ban/remove).  
- Las validaciones actuales cubren **estructura** y algunas reglas de **seguridad** (JWT claims/exp) y **moderación**; falta robustecer reglas de negocio, slugs, uploads y límites.  
- Suite de tests: **74/74** OK · cobertura ≈ **91%**. Recomendado añadir smoke tests para nuevos checks a medida que se implementen.
