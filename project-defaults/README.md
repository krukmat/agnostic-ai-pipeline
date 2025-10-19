# Project Defaults Skeleton

Este directorio contiene la estructura mínima que se copia automáticamente a `project/`
cuando la carpeta está vacía. Sirve para iniciar cada iteración con los paquetes y
archivos fundamentales ya creados.

Contenido actual:
- `backend-fastapi/`
  - `app/__init__.py`  → Garantiza que Python trate `app` como paquete.
  - `tests/__init__.py` → Permite añadir tests nuevos sin errores de importación.
- `web-express/`
  - `src/.gitkeep` y `tests/.gitkeep` → Reservan los directorios de frontend y pruebas.

Puedes ampliar estos defaults (por ejemplo añadiendo configuraciones base, utilidades
compartidas o mocks). Al ejecutar `make iteration` o cualquiera de los scripts que llaman
`common.ensure_dirs()`, cualquier archivo faltante se copiará desde aquí sin sobrescribir
los que ya existan en `project/`.
