KLKCHAN API MODELS

[ ] Validaciones de usuarios
    [ ] Formato de correo (EmailStr)
    [ ] Unicidad de usuario (username único)
    [ ] Complejidad de contraseña
    [ ] Longitud mínima/máxima de username
    [ ] URL de avatar válida
    [ ] Edad mínima
    [ ] Aceptación de términos

[ ] Validaciones de posts
    [ ] Título no vacío y longitud mínima/máxima
    [ ] Contenido no vacío y longitud mínima/máxima
    [ ] Número de etiquetas (tags) máx/min
    [ ] Formato de URL en enlaces o imágenes
    [ ] Existencia de la comunidad referenciada

[ ] Validaciones de comentarios
    [ ] Longitud mínima/máxima del comentario
    [ ] Prohibición de palabras
    [ ] Profundidad de anidamiento máxima

[ ] Validaciones de interacción
    [ ] Valores de voto permitidos (-1, +1)
    [ ] Formato de flairs
    [ ] Límite de votos por usuario

[ ] Validaciones generales
    [ ] Campos obligatorios (no null)
    [ ] Tipos de datos correctos
    [ ] Timestamps válidos
    [ ] Integridad referencial (FKs)

[ ] Seguridad y abuso
    [ ] Rate-limiting (límite de peticiones por IP/usuario)
    [ ] Protección CSRF
    [ ] Sanitización anti-XSS (filtrado de HTML/JS malicioso)
    [ ] CAPTCHA / reCAPTCHA
    [ ] Detección de spam (heurísticas de contenido)
    [ ] Bloqueo de IPs o usuarios en lista negra

[ ] Archivos y multimedia
    [ ] Tipo de archivo permitido (imágenes, vídeos)
    [ ] Tamaño máximo de archivo
    [ ] Dimensiones mín/máx de imágenes
    [ ] Validación de formatos MIME

[ ] URL, slugs y rutas
    [ ] Slugs únicos para posts/comunidades
    [ ] Longitud y caracteres válidos en slugs
    [ ] Validación de URLs externas (http/https)

[ ] Moderación y roles
    [ ] Permisos según rol (usuario vs. moderador vs. admin)
    [ ] Estado de aprobación de contenido (posts o comentarios pendientes)
    [ ] Verificación de flairs válidos según comunidad

[ ] Autenticación y cuenta
    [ ] Formato y unicidad de tokens JWT
    [ ] Caducidad de sesiones y tokens
    [ ] Validación de reset de contraseña (token)
    [ ] Verificación de email

[ ] Reglas de negocio
    [ ] Cooldown entre operaciones (no flood)
    [ ] Máximo de votos por recurso (un solo voto por post)
    [ ] Límite de anidamiento de comentarios
    [ ] Límite de subidas de archivos por recurso

[ ] Internacionalización
    [ ] Validación de campos multilenguaje (UTF-8)
    [ ] Formato de fechas/monedas según locale
