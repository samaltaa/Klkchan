from typing import List, Dict, Any
from sqlalchemy.orm import Query

# 🔹 Paginación para consultas SQLAlchemy
def paginate_query(query: Query, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """
    Aplica paginación a un Query de SQLAlchemy.
    Retorna un dict con resultados y metadata.
    """
    total_items = query.count()
    total_pages = (total_items + limit - 1) // limit

    items: List[Any] = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "page": page,
        "limit": limit,
        "total_items": total_items,
        "total_pages": total_pages,
        "data": items,
    }
