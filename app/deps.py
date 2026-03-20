"""
deps.py — Dependencias de autenticación y autorización — KLKCHAN.

Guards reutilizables que se inyectan en los endpoints vía FastAPI Depends().
Validan tokens JWT, verifican existencia del usuario, comprueban roles
y scopes, y extraen el usuario actual del contexto de la request.

Cadena de validación de get_current_user:
  1. OAuth2PasswordBearer extrae el Bearer token del header Authorization.
  2. get_current_payload() decodifica el JWT y verifica firma, exp y blacklist.
  3. get_current_user() busca el usuario en BD por payload['sub'].
     Si no existe → 401 (cubre el caso de usuarios eliminados/baneados).
  4. Verifica iat_cutoff para invalidar sesiones anteriores a un reset
     de contraseña o cambio de email.

Uso típico:
    @router.get("/protected")
    def endpoint(current_user: dict = Depends(get_current_user)):
        ...

    @router.delete("/admin-only", dependencies=[Depends(require_role(Role.admin))])
    def admin_endpoint():
        ...
"""
# app/deps.py
from typing import Any, Dict, Sequence
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError  # ✅ captura explícita de errores JWT

from app.utils.security import decode_access_token
from app.utils.token_blacklist import is_revoked
from app.services import get_user_by_id, get_active_terms, get_user_acceptance
from app.utils.roles import Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _unauthorized(detail: str) -> HTTPException:
    """Construye un HTTPException 401 con header WWW-Authenticate: Bearer."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_payload(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Valida y decodifica el access token JWT. Retorna el payload crudo.

    Pasos de validación:
      1. Decodifica el JWT verificando firma, exp, nbf e issuer.
      2. Verifica que el payload tenga campo 'sub'.
      3. Verifica que el JTI no esté en la blacklist de tokens revocados.

    Útil cuando el endpoint necesita el JTI del token (p.ej. logout,
    delete /users/me) sin el overhead de buscar el usuario en BD.

    Args:
        token: Bearer token extraído automáticamente del header Authorization.

    Returns:
        Payload JWT como dict con al menos: sub, exp, roles, scopes, jti.

    Raises:
        HTTPException 401: Si el token es inválido, expirado o revocado.
    """
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise _unauthorized("Token inválido o expirado")
    except Exception:
        # Fallback por si decode_access_token cambia la excepción
        raise _unauthorized("Token inválido")

    if not isinstance(payload, dict) or "sub" not in payload:
        raise _unauthorized("Token inválido")

    jti = payload.get("jti")
    if jti and is_revoked(jti):
        raise _unauthorized("Token revocado")

    return payload


async def get_current_user(
    payload: Dict[str, Any] = Depends(get_current_payload),
) -> Dict[str, Any]:
    """
    Obtiene el usuario autenticado a partir del payload del token.

    Busca el usuario en la BD por payload['sub']. Si el usuario fue
    eliminado o baneado, retorna 401 (get_user_by_id retorna None).
    Verifica iat_cutoff para rechazar tokens emitidos antes de un
    reset de contraseña o invalidación de sesión.

    No expone el hash bcrypt — el dict retornado contiene solo:
    id, username, email, posts, roles y scopes.
    Los roles y scopes provienen del JWT (no de la BD), por lo que
    reflejan el estado en el momento del login.

    Args:
        payload: Payload JWT decodificado (inyectado por get_current_payload).

    Returns:
        Dict con id, username, email, posts (list[int]), roles (list[str])
        y scopes (list[str]).

    Raises:
        HTTPException 401: Si el user_id en sub no es válido.
        HTTPException 401: Si el usuario no existe en la BD.
        HTTPException 401: Si el token fue emitido antes del iat_cutoff del usuario.
    """
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise _unauthorized("Token inválido")

    user = get_user_by_id(user_id)
    if not user:
        raise _unauthorized("Usuario no encontrado")

    # Invalidar tokens emitidos antes de un reset de contraseña
    iat_cutoff = user.get("iat_cutoff")
    if iat_cutoff and payload.get("iat", 0) <= iat_cutoff:
        raise _unauthorized("Sesión invalidada. Inicia sesión nuevamente.")

    # roles y scopes vienen del JWT; default ya lo pone create_access_token
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "posts": user.get("posts", []),
        "roles": payload.get("roles", ["user"]),
        "scopes": payload.get("scopes", []),
    }


def require_role(*accepted: Role):
    """
    Factory de dependency que verifica que el usuario tenga al menos uno de los roles indicados.

    La comparación es case-insensitive. Acepta tanto valores del enum
    Role como strings. Si el usuario no tiene ninguno de los roles
    aceptados, lanza 403 "Insufficient role".

    Uso en endpoint:
        @router.delete("/admin", dependencies=[Depends(require_role(Role.admin))])

    Uso cuando además se necesita el usuario:
        def endpoint(current_user: dict = Depends(require_role(Role.mod, Role.admin))):
            ...  # current_user ya tiene los datos del usuario

    Args:
        *accepted: Uno o más roles (Role enum o str) que se consideran autorizados.

    Returns:
        Dependency callable que retorna el dict del usuario autenticado
        si tiene el rol requerido.

    Raises:
        HTTPException 401: Si el token es inválido (propagado por get_current_user).
        HTTPException 403: Si el usuario no tiene ninguno de los roles aceptados.
    """
    # accepted puede traer Enum Role o strings; los normalizamos a str lower
    accepted_values_lc = {
        (r.value if isinstance(r, Role) else str(r)).lower() for r in accepted
    }

    def dep(user: Dict[str, Any] = Depends(get_current_user)):
        roles = user.get("roles", [])
        roles_lc = {str(r).lower() for r in roles}
        if roles_lc.isdisjoint(accepted_values_lc):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return dep


def require_terms_accepted(current_user: Dict[str, Any] = Depends(get_current_user)) -> None:
    """
    Dependency que verifica que el usuario haya aceptado los T&C vigentes.

    Si no hay T&C activos en el sistema, permite el acceso sin restricciones.
    Si hay T&C activos y el usuario no los ha aceptado, lanza 403 con código
    de error máquina TERMS_NOT_ACCEPTED para que el cliente pueda redirigir
    al flujo de aceptación.

    Uso en endpoint:
        @router.post("/accion", dependencies=[Depends(require_terms_accepted)])
        def accion_protegida(): ...

    Uso cuando además se necesita el usuario:
        def endpoint(
            _: None = Depends(require_terms_accepted),
            current_user: dict = Depends(get_current_user),
        ): ...

    Args:
        current_user: Usuario autenticado inyectado por get_current_user.

    Raises:
        HTTPException 401: Si el token es inválido (propagado por get_current_user).
        HTTPException 403: Si hay T&C activos y el usuario no los ha aceptado.
                           El detail incluye code, message y current_version.
    """
    active = get_active_terms()
    if not active:
        return  # Sin T&C activos no hay restricción

    accepted = get_user_acceptance(current_user["id"], active["id"])
    if not accepted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "TERMS_NOT_ACCEPTED",
                "message": "Debes aceptar los términos y condiciones.",
                "current_version": active["version"],
            },
        )


def require_scopes(required: Sequence[str]):
    """
    Factory de dependency que verifica que el usuario tenga todos los scopes requeridos.

    Los scopes son permisos granulares dentro de un rol. A diferencia de
    require_role() que verifica cualquiera de los roles, require_scopes()
    verifica que el usuario tenga TODOS los scopes indicados.

    Actualmente no se usa en ningún endpoint de producción. Reservado
    para control de acceso más fino en versiones futuras.

    Args:
        required: Lista de scopes que el usuario debe tener (todos).

    Returns:
        Dependency callable que retorna el dict del usuario autenticado.

    Raises:
        HTTPException 401: Si el token es inválido.
        HTTPException 403: Si al usuario le falta alguno de los scopes requeridos.
                           El detail incluye la lista de scopes faltantes.
    """
    required_set = {str(s).lower() for s in required}

    def dep(user: Dict[str, Any] = Depends(get_current_user)):
        scopes = {str(s).lower() for s in user.get("scopes", [])}
        missing = [s for s in required_set if s not in scopes]
        if missing:
            raise HTTPException(status_code=403, detail=f"Missing scopes: {missing}")
        return user

    return dep
