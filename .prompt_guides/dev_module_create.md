# Prompt Guide: Module Creation (Gold Standard)

## Purpose
To instruct an IDE-based LLM (Cursor, CLINE) on how to create a new COS module using the Control Center (`cc`) module as the gold-standard template.

## When to Use
- Creating a new module such as `pem`, `aic`, or `vn`
- Forking COS patterns for use in Pipeline

## Prompt Format
```
You're creating a new COS module named `<MODULE_NAME>`.
Use the `backend/cc/` module as the gold standard for structure.
Follow COS standards from `docs/foundation/`, and maintain TDD.

Create the following files:
- `<module>_main.py`
- `controller.py`, `router.py`, `schemas.py`
- `crud.py`, `services.py`, `deps.py`
- Include `<module>_manifest.yaml`, `<module>_map.yaml`
- Ensure `/health` route is implemented and tested
```

## Example Tag
# MDC: module_scaffold
