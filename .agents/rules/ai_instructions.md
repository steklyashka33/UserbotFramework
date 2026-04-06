---
trigger: always_on
---

# Architecture & Repository Standards

1.  **Mandatory Knowledge Check**: Before any architectural changes, core logic refactoring, or new feature implementations, you MUST read and follow the **[.agents/KNOWLEDGE_BASE.md](.agents/KNOWLEDGE_BASE.md)**. This ensures all modifications align with the project's distributed architecture (Manager ↔ Userbot ↔ Bot).
2.  **Project-Specific Skills**: Always utilize the specialized skills located in **[.agents/skills](.agents/skills)** (e.g., the `committing` skill) to perform repository management tasks. These skills contain optimized procedures and patterns specific to this codebase.
3.  **Dual Language Documentation**: When modifying README files, you MUST update both the English (**README.md**) and Russian (**README.ru.md**) versions to maintain synchronization. Never leave one version outdated.