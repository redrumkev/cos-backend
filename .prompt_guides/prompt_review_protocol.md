# Prompt Guide: Prompt Self-Review Protocol

## Purpose
Instruct AI coders to pause and reflect before executing code.

## Protocol
```
1. Plan fully in memory (describe next actions)
2. Pause and review the plan:
   - Ask: Does this align with COS standards?
   - Check MDC relevance, file structure, naming
3. ONLY THEN begin execution
4. Add #reasoning: comments inline when logic is non-obvious
```

## Example Trigger
```
Before refactoring router:
> I will extract controller logic into `controller.py`.
> Confirmed `cc_module.mdc.yaml` suggests this structure.
> Proceeding.
```

## MDC Link
# MDC: review_before_action
