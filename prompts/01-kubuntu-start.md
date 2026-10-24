You are working on my Kubuntu development host via Codex CLI. Windows 11 is the target environment, but the Windows tower can be powered off while Unsnooze resumes the session overnight.

Read AGENTS.md, docs/STATUS.md, docs/NEXT_TASK.md, docs/ROADMAP.md, docs/EXPLORER_HIT_TEST.md, docs/ARCHITECTURE.md and docs/DECISIONS.md. Inspect current repository code before changing anything.

CURRENT TASK: Execute docs/NEXT_TASK.md (G0-A) in a bounded way. The most important requirement is identifying the exact file **under a middle-click in Explorer**, not the selected file. Treat UIA `ElementFromPoint` → Shell item mapping as an unproven technical risk and fail closed on uncertainty.

Use a single researcher subagent only if API research has independent value; use implementer for scoped code and reviewer for defects. Avoid parallel edits. Write cross-platform fake-based tests, an isolated Windows diagnostic scaffold, and log what Windows verification is still required. No converters and no radial UI yet.

Run tests available on Kubuntu, provide evidence, and update docs/STATUS.md and docs/NEXT_TASK.md before finishing. Never claim Windows success or wait for Windows-MCP if the Windows tower is offline.
