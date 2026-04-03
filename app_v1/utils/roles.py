"""
roles.py — Definición de roles y permisos — KLKCHAN.

Define la jerarquía de roles del sistema: user < mod < admin.
Usado por require_role() en deps.py para proteger endpoints.
"""
from enum import Enum


class Role(str, Enum):
    """
    Roles disponibles en el sistema.

    Jerarquía de privilegios (menor a mayor):
      - user:  rol base asignado a todo usuario registrado.
               Puede crear posts, comentarios y votar.
      - mod:   moderador. Puede acceder a la queue de moderación,
               ejecutar acciones de moderación y eliminar contenido ajeno.
      - admin: administrador. Todos los permisos de mod más
               gestión de usuarios, asignación de roles y
               estadísticas globales.

    Los valores son str, por lo que se pueden comparar directamente
    con los strings del JWT (roles vienen del token como List[str]).
    """

    user = "user"
    mod = "mod"
    admin = "admin"
