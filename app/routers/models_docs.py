from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import markdown2
from pathlib import Path

router = APIRouter(tags=["Documentación"])

@router.get("/docs/models", response_class=HTMLResponse, include_in_schema=True)

async def get_models_documentation():
    # Ruta absoluta al archivo models.md
    markdown_file = Path(__file__).resolve().parents[1] / "models.md"



    if not markdown_file.exists():
        return HTMLResponse(content="<h1>Error: models.md no encontrado</h1>", status_code=404)
    
    # Leer y convertir a HTML
    markdown_content = markdown_file.read_text(encoding="utf-8")
    html_body = markdown2.markdown(markdown_content)

    # HTML envoltorio
    html_page = f"""
    <html>
    <head>
        <title>KLKCHAN API Models</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 40px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            h1, h2 {{ color: #333; }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """
    return HTMLResponse(content=html_page)
