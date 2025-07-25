# ✅ KLKCHAN API Models

Este documento describe las validaciones esperadas y su estado de implementación actual según el diseño del sistema.

---

## 🔐 Validaciones de usuarios

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Formato de correo (EmailStr)                    | ✓ Implementado |
| Unicidad de usuario (username único)            | ✗ Falta    |
| Complejidad de contraseña                       | ✗ Falta    |
| Longitud mínima/máxima de username              | ✗ Falta    |
| URL de avatar válida                            | ✗ Falta    |
| Edad mínima                                     | ✗ Falta    |
| Aceptación de términos                          | ✗ Falta    |

---

## 📝 Validaciones de posts

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Título no vacío y longitud mínima/máxima       | ✗ Falta    |
| Contenido no vacío y longitud mínima/máxima    | ✗ Falta    |
| Número de etiquetas (tags) máx/min             | ✗ Falta    |
| Formato de URL en enlaces o imágenes           | ✗ Falta    |
| Existencia de la comunidad referenciada        | ✗ Falta    |

---

## 💬 Validaciones de comentarios

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Longitud mínima/máxima del comentario          | ✗ Falta    |
| Prohibición de palabras                         | ✗ Falta    |
| Profundidad de anidamiento máxima               | ✗ Falta    |

---

## 👍 Validaciones de interacción

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Valores de voto permitidos (-1, +1)             | ✗ Falta    |
| Formato de flairs                               | ✗ Falta    |
| Límite de votos por usuario                     | ✗ Falta    |

---

## ⚙️ Validaciones generales

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Campos obligatorios (no null)                   | ✓ Parcialmente (esquemas base) |
| Tipos de datos correctos                        | ✓ Parcialmente (pydantic) |
| Timestamps válidos                              | ✗ Falta    |
| Integridad referencial (FKs)                    | ✗ Falta    |

---

## 🔒 Seguridad y abuso

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Rate-limiting (peticiones por IP/usuario)       | ✗ Falta    |
| Protección CSRF                                 | ✗ Falta    |
| Sanitización anti-XSS                           | ✗ Falta    |
| CAPTCHA / reCAPTCHA                             | ✗ Falta    |
| Detección de spam                               | ✗ Falta    |
| Bloqueo de IPs o usuarios                       | ✗ Falta    |

---

## 📁 Archivos y multimedia

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Tipo de archivo permitido (imágenes, vídeos)    | ✗ Falta    |
| Tamaño máximo de archivo                        | ✗ Falta    |
| Dimensiones mín/máx de imágenes                 | ✗ Falta    |
| Validación de formatos MIME                     | ✗ Falta    |

---

## 🌐 URL, slugs y rutas

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Slugs únicos para posts/comunidades             | ✗ Falta    |
| Longitud y caracteres válidos en slugs          | ✗ Falta    |
| Validación de URLs externas                     | ✗ Falta    |

---

## 🛡 Moderación y roles

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Permisos según rol (usuario/mod/admin)          | ✗ Falta    |
| Estado de aprobación de contenido               | ✗ Falta    |
| Verificación de flairs válidos                  | ✗ Falta    |

---

## 🔐 Autenticación y cuenta

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Formato y unicidad de tokens JWT                | ✗ Falta    |
| Caducidad de sesiones y tokens                  | ✗ Falta    |
| Validación de reset de contraseña (token)       | ✗ Falta    |
| Verificación de email                           | ✗ Falta    |

---

## 📜 Reglas de negocio

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Cooldown entre operaciones                      | ✗ Falta    |
| Máximo de votos por recurso                     | ✗ Falta    |
| Límite de anidamiento de comentarios            | ✗ Falta    |
| Límite de subidas de archivos por recurso       | ✗ Falta    |

---

## 🌍 Internacionalización

| Validación                                      | Estado     |
|-------------------------------------------------|------------|
| Validación de campos multilenguaje (UTF-8)      | ✗ Falta    |
| Formato de fechas/monedas según locale          | ✗ Falta    |

---

### ✅ Notas adicionales

- Los modelos `User`, `Post`, `Test` y `Upload File` ya tienen sus endpoints funcionales.
- Las validaciones actuales están limitadas a estructura de datos y campos requeridos definidos en los esquemas `pydantic`.
- El sistema aún no implementa validaciones de seguridad, lógica de negocio compleja ni control de roles.
"""