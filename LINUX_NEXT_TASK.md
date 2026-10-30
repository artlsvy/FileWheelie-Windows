# Next: resolve the native Dolphin file-identity contract

Milestone 1 ends at the precise blocker in LINUX_STATUS.md. Do not proceed to
milestone 2 under the current instruction, or claim laptop Mouse3 parity.

KWin 6.6.6 scripted effects expose the button signal, and a compositor script can
place an owned native Wayland surface. Actual hardware capture still needs a
deliberate live test. The harder blocker is authoritative hovered-file identity:
Dolphin 25.12.3's tested AT-SPI items expose no URI. Ordinary context actions do
not implement middle-click. Do not substitute selected files or guessed paths.

The next decision is whether to authorize a specifically supported Dolphin-side
integration/extension that exports the actual clicked KFileItem URL, or revise
the interaction. A Dolphin patch, private widget hook or ABI-dependent compositor
plugin is not implicitly authorized by this checkpoint. If another documented
URI provider is proposed, test it against the installed version and active tab,
not just display names. A successful hardware event alone does not close the gate.

Use `linux-evidence/milestone-1.json` and the two bounded scripts to avoid repeating
research. Preserve the finalized Windows application and the Linux branch/plan.
No push. No packaging or converter work until a subsequent instruction expands scope.
