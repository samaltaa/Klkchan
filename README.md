# KLKCHAN API

Pre-MVP de una API tipo imageboard/forum con **FastAPI**.  
Incluye autenticación JWT, gestión de usuarios, boards, posts, comments y **moderación de texto multilenguaje** (ES/EN).

> Estado actual: `v0.10.0-alpha.1` · **74/74 tests OK** · cobertura ≈ **91%** ✅

---

## ✨ Features
- **Auth**: register, login (OAuth2 password), change/forgot/reset password (reset placeholder).
- **Users**: CRUD básico + relación `user → posts`.
- **Boards / Posts / Comments**: creación y listados con relaciones embebidas.
- **Moderación**: filtro de palabras ofensivas (ES/EN) usando **LDNOOBW** + normalización y overrides.
- **JSON store** temporal (migración a DB planificada).
- **Tests** con `pytest` + `TestClient` y (opcional) gate de cobertura ≥ 90%.

---

## 🧱 Stack
- Python 3.13
- FastAPI · Pydantic v2 · Uvicorn
- PyJWT / bcrypt
- Pytest (TestClient)

---

## 🚀 Quickstart

```bash
# 1) (opcional) entorno virtual
python -m venv .venv
# Windows
. .venv/Scripts/activate
# Linux/macOS
# source .venv/bin/activate

# 2) dependencias
pip install -r requirements.txt

# 3) (una vez) prepara listas LDNOOBW (ES/EN)
# Crea app/data/ldnoobw/ y coloca es.txt y en.txt (ver Moderación)

# 4) correr el servidor
uvicorn app.app:app --reload
# Swagger UI: http://127.0.0.1:8000/docs
