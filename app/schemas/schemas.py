"""
schemas.py — Modelos Pydantic v2 de KLKCHAN.

Define todos los esquemas de request y response de la API.
Organizado en secciones:

  Base:        OrmBase, ErrorResponse, CursorPage
  Users:       UserBase, UserCreate, UserUpdate, User, UserResponse, UserListResponse
  Boards:      BoardBase, BoardCreate, BoardUpdate, Board, BoardListResponse
  Content:     Tag, Attachment
  Comments:    CommentBase, CommentCreate, Comment, CommentListResponse, Reply
  Posts:       PostBase, PostCreate, PostUpdate, Post, PostListResponse
  Votes:       Vote, VoteSummary, UserForumSubscription, Report
  Roles:       UserRole, RoleAction, RoleUpdate, RoleUpdateResponse
  Auth/Tokens: TokenPair, RefreshTokenRequest, TokenPayload,
               ChangePasswordRequest, LogoutRequest, LogoutResponse,
               ForgotPasswordRequest, ForgotPasswordResponse,
               ResetPasswordRequest, ResetPasswordResponse,
               VerifyEmailRequest, ResendVerificationRequest

Convención:
  - *Base   → campos compartidos entre Create y Response.
  - *Create → body de POST (entrada del cliente).
  - *Update → body de PUT/PATCH (todos los campos opcionales).
  - *Response / bare name → schema de respuesta (salida de la API).
  - *ListResponse → paginación cursor-based con items + limit + next_cursor.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class OrmBase(BaseModel):
    """
    Modelo base con soporte para leer atributos desde objetos ORM.

    Configura from_attributes=True (Pydantic v2) para que los modelos
    puedan construirse desde dicts y objetos con atributos (ORM-style).
    """

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """
    Schema de respuesta estándar para errores de la API.

    Todos los endpoints documentan este modelo en sus responses 4xx/5xx.
    Permite al cliente identificar el error por código máquina y
    mostrar un mensaje legible al usuario.

    Attributes:
        code: Identificador del error en formato máquina (snake_case).
        message: Descripción legible del error para el usuario final.
        details: Contexto adicional opcional (p.ej. qué campo falló la validación).
    """

    code: str = Field(..., description="Machine readable error identifier.")
    message: str = Field(..., description="Human readable error description.")
    details: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional contextual information that helps callers debug the issue.",
    )


class CursorPage(BaseModel):
    """
    Base para responses de listas con paginación cursor-based.

    Todas las *ListResponse heredan de este modelo y añaden 'items'.
    El cliente debe pasar next_cursor como ?cursor= en la siguiente
    request para obtener la página siguiente.

    Attributes:
        limit: Número de registros solicitados en esta página.
        next_cursor: ID del último item de la página actual.
                     None indica que no hay más páginas.
    """

    limit: int = Field(..., ge=1, le=100, description="Number of records requested.")
    next_cursor: Optional[int] = Field(
        default=None,
        description="Cursor to resume pagination in subsequent requests, when available.",
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class UserBase(BaseModel):
    """
    Campos base compartidos por todos los schemas de usuario.

    Attributes:
        username: Nombre de usuario único, 3-32 chars, sin espacios (pattern ^\\S+$).
        email: Email válido (validado por Pydantic EmailStr).
        display_name: Nombre público opcional (máx 80 chars).
        bio: Descripción del perfil opcional (máx 280 chars, tipo tweet).
    """

    username: str = Field(..., min_length=3, max_length=32, pattern=r"^\S+$")
    email: EmailStr
    display_name: Optional[str] = Field(default=None, max_length=80)
    bio: Optional[str] = Field(default=None, max_length=280)


class UserCreate(UserBase):
    """
    Schema de creación de usuario. Body de POST /auth/register.

    Hereda username, email, display_name y bio de UserBase.
    Añade la contraseña con validación de política mínima.

    Attributes:
        password: Contraseña en texto plano, 8-128 chars.
                  Debe contener al menos una letra mayúscula.
                  Se hashea con bcrypt antes de persistir.
    """

    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_must_have_uppercase(cls, v: str) -> str:
        """Valida que la contraseña tenga al menos una letra mayúscula."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        return v


class UserUpdate(BaseModel):
    """
    Schema de actualización de usuario. Body de PUT /users/{id}.

    Todos los campos son opcionales — solo se actualizan los que se envían.
    El endpoint rechaza el request si no se envía ningún campo (400).

    Para cambiar la contraseña usar PATCH /auth/change-password,
    que verifica la contraseña anterior antes de aceptar la nueva.

    Attributes:
        username: Nuevo username, 3-32 chars. None = sin cambio.
        email: Nuevo email. None = sin cambio.
        display_name: Nuevo nombre público. None = sin cambio.
        bio: Nueva bio. None = sin cambio.
    """

    username: Optional[str] = Field(default=None, min_length=3, max_length=32)
    email: Optional[EmailStr] = None
    display_name: Optional[str] = Field(default=None, max_length=80)
    bio: Optional[str] = Field(default=None, max_length=280)


class User(OrmBase, UserBase):
    """
    Schema de respuesta completo de un usuario.

    Incluye todos los campos públicos más datos calculados al vuelo
    (karma). El campo 'posts' contiene solo los IDs de los posts
    del usuario (no los objetos completos).

    Attributes:
        id: ID único del usuario en la BD.
        created_at: Timestamp de creación de la cuenta.
        updated_at: Timestamp de la última actualización del perfil.
        posts: Lista de IDs de posts creados por el usuario.
        roles: Lista de roles asignados (ej: ["user", "mod"]).
        is_active: Indica si la cuenta está activa.
        karma: Karma total (post_karma + comment_karma), calculado al vuelo.
        post_karma: Suma de votos recibidos en posts del usuario.
        comment_karma: Suma de votos recibidos en comentarios del usuario.
    """

    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    posts: List[int] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=lambda: ["user"])
    is_active: bool = True
    karma: int = 0
    post_karma: int = 0
    comment_karma: int = 0


class UserResponse(User):
    """Alias de User. Reservado para diferenciación futura de campos públicos vs privados."""

    pass


class UserListResponse(CursorPage):
    """Response de listado paginado de usuarios. Extiende CursorPage con items."""

    items: List[User] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Boards
# ---------------------------------------------------------------------------
class BoardBase(BaseModel):
    """
    Campos base de un board (equivalente a un subreddit).

    Attributes:
        name: Nombre del board, 3-64 chars. Debe ser único en el sistema.
        description: Descripción opcional del board (máx 280 chars).
    """

    name: str = Field(..., min_length=3, max_length=64)
    description: Optional[str] = Field(default=None, max_length=280)


class BoardCreate(BoardBase):
    """Schema de creación de board. Body de POST /boards. Requiere autenticación."""

    pass


class BoardUpdate(BaseModel):
    """
    Schema de actualización de board. Body de PUT /boards/{id}.

    Todos los campos opcionales. Solo el owner o admin pueden usarlo.

    Attributes:
        name: Nuevo nombre del board, 3-64 chars. None = sin cambio.
        description: Nueva descripción. None = sin cambio.
    """

    name: Optional[str] = Field(default=None, min_length=3, max_length=64)
    description: Optional[str] = Field(default=None, max_length=280)


class Board(OrmBase, BoardBase):
    """
    Schema de respuesta de un board.

    Attributes:
        id: ID único del board.
        creator_id: ID del usuario que creó el board. None en boards legacy
                    creados antes de Sprint 2.7 (cuando no se guardaba creator_id).
        slug: Slug URL-friendly generado al crear el board.
        created_at: Timestamp de creación.
        updated_at: Timestamp de la última modificación.
        post_count: Número de posts publicados en el board, calculado al vuelo.
    """

    id: int
    creator_id: Optional[int] = None
    slug: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    post_count: Optional[int] = Field(default=None, ge=0)


class BoardListResponse(CursorPage):
    """Response de listado paginado de boards. Extiende CursorPage con items."""

    items: List[Board] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Tags and attachments (placeholders for future PRs)
# ---------------------------------------------------------------------------
class Tag(BaseModel):
    """
    Etiqueta para categorizar posts.

    Attributes:
        id: ID único de la etiqueta.
        name: Nombre de la etiqueta, 1-64 chars.
        slug: Slug URL-friendly de la etiqueta.
        description: Descripción opcional de la etiqueta (máx 280 chars).
    """

    id: int
    name: str = Field(..., min_length=1, max_length=64)
    slug: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=280)


class Attachment(BaseModel):
    """
    Archivo adjunto a un post (imagen, documento, etc.).

    Attributes:
        id: Identificador único del adjunto (string, puede ser UUID o clave de storage).
        url: URL de acceso al archivo. None si aún no se subió.
        mime_type: Tipo MIME del archivo (ej: "image/png").
        size_bytes: Tamaño del archivo en bytes (≥ 0).
    """

    id: str
    url: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Comments and replies
# ---------------------------------------------------------------------------
class CommentBase(BaseModel):
    """
    Campos base de un comentario.

    Attributes:
        body: Contenido del comentario, 1-8000 chars.
    """

    body: str = Field(..., min_length=1, max_length=8000)


class CommentCreate(CommentBase):
    """
    Schema de creación de comentario. Body de POST /comments.

    Attributes:
        post_id: ID del post al que pertenece el comentario (≥ 1).
        parent_id: ID del comentario padre para crear un reply.
                   None crea un comentario raíz (depth=0).
                   El padre debe pertenecer al mismo post.
    """

    post_id: int = Field(..., ge=1)
    parent_id: Optional[int] = Field(default=None, ge=1)


class Comment(OrmBase, CommentBase):
    """
    Schema de respuesta de un comentario, con soporte para árbol anidado.

    Los comentarios se anidan hasta 6 niveles de profundidad via el campo
    replies. build_comment_tree() convierte la lista plana de la BD en
    este árbol. Comment.model_rebuild() es necesario por la auto-referencia.

    Attributes:
        id: ID único del comentario.
        post_id: ID del post al que pertenece.
        user_id: ID del autor del comentario.
        created_at: Timestamp de creación.
        updated_at: Timestamp de la última edición.
        votes: Score neto de votos (upvotes - downvotes), calculado al vuelo.
        parent_id: ID del comentario padre. None si es comentario raíz.
        depth: Nivel de anidación (0 = raíz, 1 = reply directa, etc.).
        replies: Lista de comentarios hijo anidados (recursivo hasta 6 niveles).
    """

    id: int
    post_id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    votes: int = 0
    parent_id: Optional[int] = None
    depth: int = 0
    replies: List["Comment"] = Field(default_factory=list)


Comment.model_rebuild()


class CommentListResponse(CursorPage):
    """Response de listado paginado de comentarios como árbol anidado."""

    items: List[Comment] = Field(default_factory=list)


class Reply(OrmBase):
    """
    Schema de respuesta de un reply (comentario hijo).

    Modelo alternativo a Comment para casos donde solo se necesita
    la estructura plana de un reply sin recursividad.

    Attributes:
        id: ID del reply.
        comment_id: ID del comentario padre.
        user_id: ID del autor.
        body: Contenido del reply.
        created_at: Timestamp de creación.
        updated_at: Timestamp de la última edición.
        votes: Score neto de votos.
    """

    id: int
    comment_id: int
    user_id: int
    body: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    votes: int = 0


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------
class PostBase(BaseModel):
    """
    Campos base compartidos por los schemas de posts.

    Attributes:
        title: Título del post, 3-300 chars.
        body: Cuerpo del post, mínimo 1 char (sin límite superior en schema).
        board_id: ID del board al que pertenece el post (≥ 1).
        tags: Lista de etiquetas del post (strings). Lista vacía por defecto.
    """

    title: str = Field(..., min_length=3, max_length=300)
    body: str = Field(..., min_length=1)
    board_id: int = Field(..., ge=1)
    tags: List[str] = Field(default_factory=list)


class PostCreate(PostBase):
    """
    Schema de creación de post. Body de POST /posts.

    Hereda title, body, board_id y tags de PostBase.

    Attributes:
        attachments: Lista de adjuntos del post. Lista vacía por defecto.
    """

    attachments: List[Attachment] = Field(default_factory=list)


class PostUpdate(BaseModel):
    """
    Schema de actualización de post. Body de PUT /posts/{id}.

    Todos los campos opcionales. Solo el author o mod/admin pueden usarlo.

    Attributes:
        title: Nuevo título, 3-300 chars. None = sin cambio.
        body: Nuevo cuerpo. None = sin cambio.
        board_id: Nuevo board de destino. None = sin cambio.
        tags: Nueva lista de tags (reemplaza completa). None = sin cambio.
    """

    title: Optional[str] = Field(default=None, min_length=3, max_length=300)
    body: Optional[str] = Field(default=None, min_length=1)
    board_id: Optional[int] = Field(default=None, ge=1)
    tags: Optional[List[str]] = None


class Post(OrmBase, PostBase):
    """
    Schema de respuesta de un post con comentarios anidados.

    Attributes:
        id: ID único del post.
        user_id: ID del autor del post.
        created_at: Timestamp de creación.
        updated_at: Timestamp de la última edición.
        votes: Score neto de votos (upvotes - downvotes).
        score: Score del algoritmo 'hot' (votos / (horas + 2)^1.5).
               None si no se calculó (endpoints que no usan sort=hot).
        comment_count: Número total de comentarios del post, calculado al vuelo.
        attachments: Lista de adjuntos del post.
        comments: Árbol de comentarios anidados (ver Comment.replies).
    """

    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    votes: int = 0
    score: Optional[int] = None
    comment_count: Optional[int] = None
    attachments: List[Attachment] = Field(default_factory=list)
    comments: List[Comment] = Field(default_factory=list)


class PostListResponse(CursorPage):
    """Response de listado paginado de posts. Extiende CursorPage con items."""

    items: List[Post] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Votes, subscriptions, reports
# ---------------------------------------------------------------------------
class Vote(BaseModel):
    """
    Registro de un voto individual. Usado internamente en la BD.

    Attributes:
        id: ID único del voto.
        target_type: Tipo de entidad votada ("post" o "comment").
        target_id: ID de la entidad votada.
        user_id: ID del usuario que emitió el voto.
        value: Valor del voto (-1 downvote, 0 neutro, 1 upvote).
        created_at: Timestamp de creación del voto.
    """

    id: int
    target_type: str
    target_id: int
    user_id: int
    value: int = Field(..., ge=-1, le=1)
    created_at: datetime


class VoteSummary(BaseModel):
    """
    Resumen agregado de votos de un post o comentario.

    Retornado por POST /interactions/votes y
    GET /interactions/votes/{target_type}/{target_id}.

    Attributes:
        target_type: Tipo de entidad ("post" o "comment").
        target_id: ID de la entidad.
        score: Score neto (upvotes - downvotes).
        upvotes: Número total de upvotes.
        downvotes: Número total de downvotes.
        user_vote: Voto activo del usuario que hizo la request (-1/0/1).
                   None en el endpoint GET (público, sin usuario autenticado).
    """

    target_type: str
    target_id: int
    score: int
    upvotes: int
    downvotes: int
    user_vote: Optional[int] = None


class UserForumSubscription(BaseModel):
    """
    Suscripción de un usuario a un board.

    Placeholder para la funcionalidad de "seguir un board".
    No está implementado en ningún endpoint actualmente.

    Attributes:
        id: ID único de la suscripción.
        user_id: ID del usuario suscrito.
        board_id: ID del board al que se suscribió.
        created_at: Timestamp de la suscripción.
    """

    id: int
    user_id: int
    board_id: int
    created_at: datetime


class Report(BaseModel):
    """
    Reporte de contenido inapropiado enviado por un usuario.

    Usado en POST /moderation/reports y GET /moderation/reports.

    Attributes:
        id: ID único del reporte.
        reporter_id: ID del usuario que reportó.
        target_type: Tipo de entidad reportada ("post", "comment" o "user").
        target_id: ID de la entidad reportada.
        reason: Motivo del reporte, 3-500 chars.
        status: Estado del reporte ("pending", "resolved", "dismissed").
        created_at: Timestamp de creación del reporte.
        resolved_at: Timestamp de resolución. None si aún está pendiente.
        resolved_by: ID del mod/admin que resolvió el reporte.
        details: Contexto adicional del reporte (dict clave-valor).
    """

    id: int
    reporter_id: int
    target_type: str
    target_id: int
    reason: str = Field(..., min_length=3, max_length=500)
    status: str = Field(default="pending")
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    details: Optional[Dict[str, str]] = None


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
class UserRole(str, Enum):
    """
    Roles disponibles en el sistema (espejo de utils/roles.py para uso en schemas).

    Usada en PATCH /admin/users/{id}/role para validar el rol a asignar/quitar.
    """

    user = "user"
    mod = "mod"
    admin = "admin"


class RoleAction(str, Enum):
    """
    Acción a realizar sobre el rol de un usuario.

    Usada junto a UserRole en RoleUpdate.
    """

    add = "add"
    remove = "remove"


class RoleUpdate(BaseModel):
    """
    Body de PATCH /admin/users/{id}/role.

    Attributes:
        role: Rol a modificar (user, mod o admin).
        action: Acción a aplicar (add o remove). Default: add.
    """

    role: UserRole
    action: RoleAction = RoleAction.add


class RoleUpdateResponse(BaseModel):
    """
    Response de PATCH /admin/users/{id}/role.

    Attributes:
        user_id: ID del usuario modificado.
        username: Username del usuario modificado.
        roles: Lista completa de roles del usuario tras la modificación.
        message: Mensaje confirmando la acción realizada.
    """

    user_id: int
    username: str
    roles: List[str]
    message: str


# ---------------------------------------------------------------------------
# Auth / Tokens
# ---------------------------------------------------------------------------
class TokenPair(BaseModel):
    """
    Par de tokens retornado en login y refresh exitosos.

    Attributes:
        access_token: JWT de acceso de corta duración (default 15 min).
                      Se incluye en el header Authorization: Bearer <token>.
        refresh_token: JWT de refresh de larga duración (default 7 días).
                       Se usa en POST /auth/refresh para obtener nuevo par.
        token_type: Siempre "bearer".
        expires_in: Segundos hasta que el access_token expire.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., ge=1, description="Seconds until the access token expires.")


class RefreshTokenRequest(BaseModel):
    """
    Body de POST /auth/refresh.

    Attributes:
        refresh_token: JWT de refresh emitido en el último login.
                       Mínimo 16 chars para filtrar strings trivialmente cortos.
    """

    refresh_token: str = Field(..., min_length=16)


class TokenPayload(BaseModel):
    """
    Estructura del payload decodificado de un JWT de KLKCHAN.

    Usado internamente para tipar el resultado de decode_access_token().

    Attributes:
        sub: Subject — ID del usuario como string.
        exp: Timestamp Unix de expiración.
        roles: Lista de roles del usuario en el momento del login.
        scopes: Lista de scopes granulares (actualmente vacía en producción).
        jti: JWT ID único — usado para blacklist en logout/revocación.
        typ: Tipo de token ("access", "refresh" o "password_reset").
    """

    sub: Optional[str] = None
    exp: Optional[int] = None
    roles: List[str] = Field(default_factory=list)
    scopes: List[str] = Field(default_factory=list)
    jti: Optional[str] = None
    typ: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """
    Body de PUT /auth/change-password.

    Requiere la contraseña actual para verificar identidad antes
    de aceptar la nueva contraseña.

    Attributes:
        old_password: Contraseña actual del usuario (mín 6 chars).
        new_password: Nueva contraseña deseada (mín 8 chars).
    """

    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=8)


class LogoutRequest(BaseModel):
    """
    Body opcional de POST /auth/logout.

    Si se omite el body, solo se revoca el access token.
    Si se incluye refresh_token, también se revoca el refresh token.

    Attributes:
        refresh_token: Refresh token a revocar. None = solo revocar access token.
    """

    refresh_token: Optional[str] = None


class LogoutResponse(BaseModel):
    """Response de POST /auth/logout."""

    detail: str = "Logged out"


class ForgotPasswordRequest(BaseModel):
    """
    Body de POST /auth/forgot-password.

    Attributes:
        email: Email del usuario que olvidó su contraseña.
    """

    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """
    Response de POST /auth/forgot-password.

    El endpoint siempre retorna el mismo mensaje independientemente
    de si el email existe, para no revelar qué emails están registrados.

    Attributes:
        detail: Mensaje genérico de confirmación.
        reset_token: Token de reset. TODO: eliminar en producción —
                     en producción se envía por email, no en la respuesta.
    """

    detail: str = "If the email exists, reset instructions were sent"
    reset_token: Optional[str] = None  # TODO: eliminar en producción — enviar por email


class ResetPasswordRequest(BaseModel):
    """
    Body de POST /auth/reset-password.

    Attributes:
        token: Token de reset recibido por email (o en forgot-password response en dev).
        new_password: Nueva contraseña, 12-128 chars (más restrictivo que register).
    """

    token: str = Field(..., description="Reset token delivered over email")
    new_password: str = Field(..., min_length=12, max_length=128)


class ResetPasswordResponse(BaseModel):
    """Response de POST /auth/reset-password."""

    detail: str = "Password updated"


class VerifyEmailRequest(BaseModel):
    """
    Body de POST /auth/verify-email.

    Stub pendiente de implementación con Supabase Auth en Sprint 3.

    Attributes:
        token: Token de verificación de email, 16-4096 chars.
               No debe contener espacios. Formato: string plano o JWT (3 partes).
    """

    token: str = Field(..., min_length=16, max_length=4096, description="Verification token")

    @field_validator("token")
    @classmethod
    def token_must_not_contain_spaces(cls, value: str) -> str:
        """Valida que el token no tenga espacios y tenga 1 o 3 partes separadas por puntos."""
        if any(ch.isspace() for ch in value):
            raise ValueError("The token must not contain whitespace.")
        parts = value.split(".")
        if len(parts) not in (1, 3):
            raise ValueError("Unexpected token format.")
        return value


class ResendVerificationRequest(BaseModel):
    """
    Body de POST /auth/resend-verification.

    Stub pendiente de implementación con Supabase Auth en Sprint 3.

    Attributes:
        email: Email de la cuenta cuya verificación se quiere reenviar.
    """

    email: EmailStr


__all__ = [
    "Attachment",
    "Board",
    "RoleAction",
    "RoleUpdate",
    "RoleUpdateResponse",
    "UserRole",
    "BoardCreate",
    "BoardListResponse",
    "BoardUpdate",
    "ChangePasswordRequest",
    "Comment",
    "CommentBase",
    "CommentCreate",
    "CommentListResponse",
    "CursorPage",
    "ErrorResponse",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "LogoutRequest",
    "LogoutResponse",
    "OrmBase",
    "Post",
    "PostCreate",
    "PostListResponse",
    "PostUpdate",
    "Report",
    "ResendVerificationRequest",
    "ResetPasswordRequest",
    "ResetPasswordResponse",
    "Reply",
    "Tag",
    "TokenPair",
    "TokenPayload",
    "RefreshTokenRequest",
    "User",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    "UserForumSubscription",
    "VerifyEmailRequest",
    "Vote",
]
