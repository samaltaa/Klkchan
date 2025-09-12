✨ Features

Auth: register, login (OAuth2 password), change/forgot/reset password (reset placeholder).

Users: CRUD básico + relación user → posts.

Boards / Posts / Comments: creación y listados con relaciones embebidas.

Moderación: filtro de palabras ofensivas (ES/EN) usando LDNOOBW + normalización y overrides.

JSON store temporal (migración a DB planificada).

Tests con pytest + TestClient y gate de cobertura (opcional) ≥ 90%.

🧱 Stack

Python 3.13 (recomendado)

FastAPI · Pydantic v2 · Uvicorn

PyJWT/bcrypt (seguridad)

Pytest (TestClient)

🚀 Quickstart
# 1) (opcional) crea venv
python -m venv .venv && . .venv/Scripts/activate    # Windows PowerShell
# source .venv/bin/activate                         # Linux/macOS

# 2) instala dependencias
pip install -r requirements.txt

# 3) (una vez) prepara listas LDNOOBW (ES/EN)
# Crea app/data/ldnoobw/ y coloca es.txt, en.txt (ver sección Moderación)
# Opcional: docs/ATTRIBUTION.md + docs/licenses/CC-BY-4.0.txt

# 4) corre el servidor
uvicorn app.app:app --reload

# Swagger UI
# http://127.0.0.1:8000/docs
