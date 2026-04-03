# Changelog

## [Unreleased]
### Added
- (pendiente)

### Changed
- (pendiente)

### Fixed
- (pendiente)

---

## [v0.9.0] - 2025-09-12
### Added
- Moderación de texto en Boards, Posts, Comments y Users (filtro con normalización/regex).
- Helper `enforce_clean_text` aplicado en endpoints.
- Router de Moderation con acciones mínimas (remove/ban user/remove comment).

### Changed
- Validaciones antes de persistir en creaciones/actualizaciones.

### Fixed
- Limpieza de imports y separación correcta del router de moderación.

## [v0.8.0] - 2025-09-10
### Added
- Autenticación (register/login/forgot/refresh).
- Estructura base FastAPI + data store JSON.
