# Filewheel — Codex starter package

Private Windows 11 file converter prototype. **Current phase: headless explicit-path
launcher complete; PySide6 radial GUI preview is implemented.** Conversion is not implemented.

G0-A now includes portable contracts/tests and an opt-in Windows diagnostic
scaffold. See [diagnostic instructions and limitations](docs/DIAGNOSTIC_POC.md).
Experimental Mouse3 remains available and emits no trusted hover targets.
The [explicit-path/Send to launcher](docs/SEND_TO.md) validates one file through
the shared controller. Basic single-file headless direct/Send to is Windows-verified;
the new GUI and broader argument/removal acceptance remain queued.

## What this bundle contains
- `AGENTS.md`: current project-wide rules, replacing older versions.
- `.codex/config.toml`, `.codex/agents/*.toml`: agent settings, replacing earlier examples.
- `docs/ROADMAP.md`, `NEXT_TASK.md`, `STATUS.md`: long-lived work queue and checkpoints.
- `docs/EXPLORER_HIT_TEST.md`: first stage contract and hard gate.
- `docs/UI_SPEC.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `CONVERSION_MATRIX.md`, `TEST_PLAN.md`: design and future requirements.
- `docs/MCP_AND_REMOTE_WINDOWS.md`: optional Windows desktop testing from a Kubuntu Codex session.
- `prompts/01-kubuntu-start.md`: first Codex instruction (paste or use as source).

## Set up on Kubuntu
1. Create a new Git repo or merge the **contents** of this directory into your existing repo. Review differences before replacing existing source or docs.
2. Run `git status`, `codex --version`, and `codex mcp list`.
3. Start a **new** Codex session in the trusted repo root so project `AGENTS.md` and `.codex/config.toml` are loaded.
4. Paste `prompts/01-kubuntu-start.md` into Codex, or instruct Codex to read it and execute its scope.
5. Work/test overnight on Linux. When Windows is on, copy/checkout the same Git revision on Windows and perform real desktop validation; keep results in `docs/STATUS.md`.
6. If desired, enable optional Windows-MCP via SSH loopback tunnel, per `docs/MCP_AND_REMOTE_WINDOWS.md`. It is **not a prerequisite** for any nightly work.

## No old content needs copying
This package supersedes all prior draft `AGENTS.md`, agent TOMLs, roadmaps and first prompts from the chat. Preserve **existing application source code** if you have already implemented any; this pack supplies project guidance, not an app implementation.

## Official references
- Codex subagents: https://developers.openai.com/codex/subagents
- Codex config: https://developers.openai.com/codex/config-reference
- Microsoft UIA ElementFromPoint: https://learn.microsoft.com/en-us/windows/win32/api/uiautomationclient/nf-uiautomationclient-iuiautomation-elementfrompoint
- Microsoft low-level mouse hook: https://learn.microsoft.com/en-us/windows/win32/winmsg/lowlevelmouseproc
- Windows-MCP: https://github.com/CursorTouch/Windows-MCP

## Radial preview

Install the optional UI with `python -m pip install -e ".[ui]"` (PySide6>=6.12
for Python3.15 support). On Windows, `python -m
filewheel.platforms.windows.sendto install --mode gui` adds **Filewheel preview**
to Send to. [Commands and manual acceptance](docs/SEND_TO.md) cover staging,
removal, direct launching and pending Windows DPI/focus tests. The two-stage
radial menu only previews declared conversions and changes no files. G5's real
PNG→JPEG engine is next, followed by PDF→DOCX and MarkItDown.
