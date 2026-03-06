✅ KLKCHAN API Models

Este documento describe las validaciones esperadas y su estado de implementación actual según el diseño del sistema.

🔐 Validaciones de usuarios
Validación	Estado
Formato de correo (EmailStr)	✅ Implementado
Unicidad de usuario (username único)	✅ Implementado (register/update)
Complejidad de contraseña	⚠️ Parcial (inconsistente entre flows)
Longitud mínima/máxima de username	✅ Implementado
URL de avatar válida	✗ Falta
Edad mínima	✗ Falta
Aceptación de términos	✗ Falta

Notas de verificación (Usuarios)

UserCreate.email usa formato email.

UserCreate.username y UserUpdate.username con min 3 / max 32.

ChangePasswordRequest min 8 vs ResetPasswordRequest min 12.

📝 Validaciones de posts
Validación	Estado
Título no vacío y longitud mínima/máxima	✅ Implementado (3–300)
Contenido no vacío y longitud mínima/máxima	⚠️ Parcial (min presente; max no)
Número de etiquetas (tags) máx/min	✗ Falta
Formato de URL en enlaces o imágenes	✗ Falta
Existencia de la comunidad referenciada	✗ Falta

Notas de verificación (Posts)

PostCreate.title 3–300 y body min 1.

tags sin límites de cantidad.

💬 Validaciones de comentarios
Validación	Estado
Longitud mínima/máxima del comentario	✅ Implementado (1–8000)
Prohibición de palabras	✅ Implementado
Profundidad de anidamiento máxima	✗ Falta

Notas de verificación (Comentarios)

CommentCreate.body 1–8000.

👍 Validaciones de interacción
Validación	Estado
Valores de voto permitidos (-1, +1)	✗ Falta
Formato de flairs	✗ Falta
Límite de votos por usuario	✗ Falta

Notas de verificación (Interacción)

VoteRequest.value es integer sin enum {−1,+1}.

Endpoints de votos ya existen.

⚙️ Validaciones generales
Validación	Estado
Campos obligatorios (no null)	✅ Parcial (esquemas base)
Tipos de datos correctos	✅ Parcial (pydantic)
Timestamps válidos	✗ Falta
Integridad referencial (FKs)	✗ Falta

Notas de verificación (Generales)

Post/Comment/Board incluyen created_at/updated_at, pero permiten null/no canónico.

🔒 Seguridad y abuso
Validación	Estado
Rate-limiting (peticiones por IP/usuario)	✗ Falta
Protección CSRF	✗ Falta
Sanitización anti-XSS	✗ Falta
CAPTCHA / reCAPTCHA	✗ Falta
Detección de spam	✗ Falta
Bloqueo de IPs o usuarios	⚠️ Parcial (ban/shadowban básicos)

Notas de verificación (Seguridad)

moderation/actions incluye ban_user y shadowban (varios como placeholders).

📁 Archivos y multimedia
Validación	Estado
Tipo de archivo permitido (imágenes, vídeos)	✗ Falta
Tamaño máximo de archivo	✗ Falta
Dimensiones mín/máx de imágenes	✗ Falta
Validación de formatos MIME	✗ Falta

Notas de verificación (Archivos)

Attachment existe (url/mime_type/size_bytes) sin validación fuerte.

🌐 URL, slugs y rutas
Validación	Estado
Slugs únicos para posts/comunidades	✗ Falta
Longitud y caracteres válidos en slugs	✗ Falta
Validación de URLs externas	✗ Falta

Notas de verificación (Slugs/URLs)

Board.slug existe pero sin unicidad/normalización.

🛡 Moderación y roles
Validación	Estado
Permisos según rol (usuario/mod/admin)	✅ Implementado (router/moderation)
Estado de aprobación de contenido	✗ Falta
Verificación de flairs válidos	✗ Falta

Notas de verificación (Moderación/Roles)

Cola y acciones de moderación expuestas (algunas en stub).

🔐 Autenticación y cuenta
Validación	Estado
Formato y unicidad de tokens JWT	✅ Parcial (claims/firmas OK; unicidad N/A)
Caducidad de sesiones y tokens	✅ Implementado
Validación de reset de contraseña (token)	⚠️ Parcial
Verificación de email	⚠️ Parcial

Notas de verificación (Auth)

Flujos: register/login/refresh/forgot/reset/verify/resend presentes.

ResetPasswordRequest exige token + new_password (min 12).

📜 Reglas de negocio
Validación	Estado
Cooldown entre operaciones	✗ Falta
Máximo de votos por recurso	✗ Falta
Límite de anidamiento de comentarios	✗ Falta
Límite de subidas de archivos por recurso	✗ Falta
🌍 Internacionalización
Validación	Estado
Validación de campos multilenguaje (UTF-8)	✅ Parcial (filtros básicos)
Formato de fechas/monedas según locale	✗ Falta