# COS MDC Changelog

This file tracks meaningful changes to `.mdc.yaml` rules in `.cursor/rules/`.

> ⚠️ **Note:** This changelog is structured to be compact. After 3–5 changes, entries are summarized ("compacted") while retaining all critical context. Use this file to understand key evolutions in the MDC rule system — no excessive verbosity.

---

### 📅 2025-04-02 — MDC Version Lock v1.0

- 🔐 Versioned all `.mdc.yaml` rules to `version: 1.0`
- ✅ Added standard frontmatter to all MDCs:
  ```yaml
  # ---
  # name: <short_id>
  # version: 1.0
  # created: 2025-04-02
  # applies_to: ["*.py"]
  # trigger: "agent_requested" or "always"
  # summary: <1-line description>
  # ---
  ```
- 🧠 Unified description formatting for all `pattern:` sections.
- 📦 `mem0_module.mdc.yaml` created and finalized.
- 🏗️ Identified `.projectrules.yaml` legacy files for future deprecation.

---

### 🔜 Upcoming (Planned)
- Scaffold `.taskmaster/` plan YAMLs
- Begin `.prompt_guides/` with core prompt formats
- Automate MDC linking/tagging process for file headers

---

End of compact changelog section.

---
