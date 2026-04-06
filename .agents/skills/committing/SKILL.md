---
name: committing
description: Use for granular version control with concise reporting and strict adherence to commands.
---

# Committing

## Overview
This skill defines a disciplined approach to version control: focus on the immediate context, propose granular commits based on actual changes, and remain strictly passive regarding execution until explicitly commanded.

## When to Use
- After completing a set of changes that form a logical unit.
- When the user asks to summarize, group, or name changes for commits (e.g., "напиши названия для текущих изменений").
- **NEVER** use to automatically execute a commit unless the user explicitly said "commit", "закомить", or "do it".

## Guidance for Interaction

### 1. Fresh Context (Anti-Bloat)
Act based on the **now**. Focus on the current task and the immediate previous messages. Avoid over-analyzing the entire conversation history or project-wide goals unless strictly necessary for the current diff.

| ❌ The "Analysis Wall" (Avoid) | ✅ The "Direct Result" (Do) |
|------------------------------|----------------------------|
| "Based on my analysis, I recommend splitting... Option 1: ... Option 2: ... This will improve security by..." | "Commit Suggestion: `feat: add stable device masking`. Implements deterministic session fingerprints based on session ID." |

### 2. Granular Proposals
Propose splitting changes into small, logical batches (e.g., 1-2 files per commit). Use the following detailed format:

**[Number]. [Section Name]**
- **Files**: [List of files]
- **What changed**:
  - [Bullet points of specific deltas]
- **Commit Suggestion**: `[Conventional Message]`

**Call to Action**: End the entire proposal batch with exactly: `**Закомитить?**` (or `**Commit?**`).

### 3. Commit Naming Rules
Names should be based on the **specific delta** of the changes:
- Use **Conventional Commits** (e.g., `feat:`, `fix:`, `refactor:`, `style:`, `docs:`).
- Describe what was *changed* (e.g., "add timeout to API requests"), not the *intent* (e.g., "improve stability").
- Ignore old naming patterns if they no longer fit the current state of the code.

### 4. Passive Execution (Safety first)
- **Wait for Command**: Even if the work is perfect, do NOT run `git commit` until you see a direct instruction like "commit" or "закомить".
- **Shell Reliability**: On Windows, use `cmd /c git add <file>` followed by `powershell -Command "git commit -m '...'"` (or pipe the message) to avoid quote-stripping issues.

### 5. Concise Post-Commit Reporting
After a successful commit, report **ONLY** what was specifically accomplished in that exact execution.
- **DO**: State the commit hash, the message, and a 1-sentence summary of the CURRENT changes.
- **DON'T**: Provide a meta-analysis of the project's evolution or summarize what we've done over the last hour.

**Template:** `Committed: [Hash] — [Message]. [Specific changes done in THIS turn].`

### 6. Discovery Procedures (Windows Reliability)
When asked for commit names or status on Windows, if standard tools appear silent:
- **Mandatory**: Use `cmd /c` prefix for discovery (e.g., `cmd /c git status`, `cmd /c git diff`). Standard calls without this prefix often return empty buffers.
- Immediately try `cmd /c git status -s` to see a summary of modified files.
- Check staged files with `cmd /c git diff --cached --name-only`.
- Check un-staged changes with `cmd /c git diff --name-only`.
- Do **NOT** redirect output to temporary files unless strictly necessary for debugging; instead, use `command_status` with a longer wait or the `cmd /c` prefix to ensure the buffer is captured.
- Focus strictly on files relevant to the current task to avoid bloat.

## Common Mistakes to Avoid
- **"The Wall of Text"**: Summarizing previous conversation steps in the final response.
- **Automatic Committing**: Assuming that "job is done" equals "I should commit now".
- **Vague Naming**: Using messages like "update files" instead of "refactor login logic in server_app.py".
