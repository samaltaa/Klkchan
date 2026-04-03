from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import markdown2
from pathlib import Path

router = APIRouter(tags=["Documentación"])


@router.get("/docs/models", response_class=HTMLResponse, include_in_schema=True)
async def get_models_documentation():
    """
    Retorna la documentación de modelos de KLKCHAN en formato HTML.

    Lee el archivo app/docs/models.md y lo convierte a HTML con estilos básicos.

    Returns:
        HTMLResponse con el contenido formateado del archivo models.md.

    Raises:
        HTTPException 404: Si el archivo models.md no se encuentra.
    """
    markdown_file = Path(__file__).resolve().parents[1] / "docs" / "models.md"

    if not markdown_file.exists():
        return HTMLResponse(content="<h1>Error: models.md no encontrado</h1>", status_code=404)

    markdown_content = markdown_file.read_text(encoding="utf-8")
    html_body = markdown2.markdown(markdown_content)

    html_page = f"""<html>
<head>
    <title>KLKCHAN API Models</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 40px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        h1, h2 {{ color: #333; }}
        pre {{ background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <pre class="klkchan-models-header">KLKCHAN API — Models Reference</pre>
    {html_body}
</body>
</html>"""
    return HTMLResponse(content=html_page)
