# Prompt Guide: TaskMaster + Coder (Cursor/CLINE) Handshake

## Purpose
Explains how LLM coder should interpret and follow `.taskmaster_ai/*.yaml` task plans.

## Structure
```
1. Parse the `.yaml` file for task overview and steps.
2. Confirm active MDCs for current context.
3. Before coding:
   - Echo the step plan
   - Ask if context or MDC guidance is unclear
4. Implement one step at a time
   - Commit early, test frequently
   - Use #task_complete inline comment when done
5. At end, self-review output against `.yaml` goals
```

## MDC Link
# MDC: task_executor
