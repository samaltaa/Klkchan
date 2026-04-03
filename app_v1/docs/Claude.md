# REGLA PERMANENTE DE FLUJO DE TRABAJO — KLKCHAN

Por favor añade lo siguiente al archivo CLAUDE.md en la raíz
del proyecto (crearlo si no existe):

## Git — Política de commits

**Claude NO debe hacer commits ni push bajo ninguna circunstancia.**

Esto incluye:

- git commit
- git push
- git add + commit
- Commits automáticos al finalizar tareas
- Commits de "limpieza" o "fix menor"

El desarrollador revisa y hace todos los commits manualmente.

Al finalizar cada tarea Claude debe:

1. Mostrar el resumen de cambios realizados
2. Listar los archivos modificados/creados/eliminados
3. Sugerir el mensaje de commit (como texto para copiar)
4. Detenerse ahí — nunca ejecutar git add/commit/push
