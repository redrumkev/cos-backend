# COS `.cursor/rules/` – MDC System

This folder houses **Modular Development Context (MDC)** rules for Cursor/CLINE.

Each `.mdc.yaml` file documents a **pattern, convention, or rule** that the AI should follow when developing COS.

## Purpose

- Guides Cursor/CLINE AI to write code the **COS way**
- Makes repeated actions (e.g., creating modules, logging, tests) **consistent**
- Powers **low-token context awareness** for agents, improving speed and quality

## Naming Convention

- `cc_module.mdc.yaml`: for the `cc` module
- `main_app_entrypoint.mdc.yaml`: for `cos_main.py`
- `test_pattern.mdc.yaml`: reusable test scaffolding
- `mem0_module.mdc.yaml`: rules for working with `mem0`

## Rule Types

- `always`: attach to all prompts
- `agent_requested`: loaded on demand (default for most)
- `manual`: tag explicitly in the prompt
- `autoattached`: matched by file pattern (e.g. *.test.py)

## Tagging MDCs in files

To enable agent context linking:
```
# MDC: cc_module
```
Tagging helps human readers and makes prompt chaining with CLINE or Task Master more effective.

## Deprecation Note

The legacy cursor/rules/*.projectrules.yaml format is being deprecated. These rules are being refactored into MDCs as .mdc.yaml files, providing clearer structure, modularity, and direct integration with cursor-aware development.

All context, rules, and patterns from cursor/rules will eventually live here in .cursor/rules/, enabling a single-point-of-truth for agentic development alignment.

## Upcoming Task Master Directory

Rules are complemented by .taskmaster/ YAML plans that orchestrate feature execution. Example:

- .taskmaster/cc_test_plan.yaml

- .taskmaster/cursor_memory_refactor.yaml


Together, MDC + Task Master = Dynamic Dev Alignment System (DDAS)
Let's go!
