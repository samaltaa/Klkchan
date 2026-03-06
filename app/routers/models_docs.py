import html
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter(tags=["Documentación"])

@router.get("/docs/models", response_class=HTMLResponse, include_in_schema=True)
async def get_models_documentation():
    markdown_file = Path(__file__).resolve().parents[1] / "docs" / "models.md"

    if not markdown_file.exists():
        return HTMLResponse(content="<h1>Error: models.md no encontrado</h1>", status_code=404)

    markdown_content = markdown_file.read_text(encoding="utf-8")
    escaped = html.escape(markdown_content)

    html_page = f"""<html>
<head>
    <title>KLKCHAN API Models</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #fff; }}
        pre {{ white-space: pre-wrap; font-family: monospace; font-size: 14px;
               background: #f8f8f8; padding: 16px; border-radius: 4px; }}
    </style>
</head>
<body>
<pre>{escaped}</pre>
</body>
</html>"""
    return HTMLResponse(content=html_page)
