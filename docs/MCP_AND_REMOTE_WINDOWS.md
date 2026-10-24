# Optional Windows desktop QA while Codex runs on Kubuntu

## Recommendation
**Keep Windows-MCP out of required project config.** There is no overnight Windows access when the tower is powered off. Start/enable it only for **live, interactive Windows UI tests**. Core development uses Linux tests/mocks.

## MCP choice
- Windows-MCP (https://github.com/CursorTouch/Windows-MCP): useful for UI inspection, clicking and screenshots; **does not itself solve point→file identity**. It operates on the Windows desktop and may require it to be unlocked/interactive.
- OpenAI Docs MCP (https://developers.openai.com/mcp): optional for Codex configuration questions.
- Context7 (https://github.com/upstash/context7): optional for library docs. Not necessary for source/tests; don't install redundant filesystem or online conversion MCPs.
- Online conversion MCPs are counterproductive; runtime is intended to stay local.

## Secure loopback SSH reverse tunnel (no public server)
Prerequisites: normal Windows → Kubuntu `ssh ares-unix` works, `ssh` reverse forwarding allowed by Ubuntu SSHD; run Codex on Kubuntu; Windows 11 tower is on, logged in, and interactive. Commands below run in **different terminals**.

**Windows PowerShell terminal A**, with `uvx` installed and the Windows-MCP Python 3.14+ runtime available:
```powershell
uvx windows-mcp serve --transport streamable-http --host 127.0.0.1 --port 8000
```
**Windows PowerShell terminal B**:
```powershell
ssh -N -o ExitOnForwardFailure=yes -R 127.0.0.1:8765:127.0.0.1:8000 ares-unix
```
This forwards the **Kubuntu** endpoint `127.0.0.1:8765` to the **Windows** loopback server `127.0.0.1:8000` inside encrypted SSH. No router port-forward, Tailscale exposure, or `0.0.0.0` bind required. Endpoints disappear when Windows/tunnel is off. Ensure the SSH server permits TCP forwarding. Do not expose the Windows-MCP server on an untrusted network.

**Kubuntu**, optional user-local `~/.codex/config.toml` section (NOT in repo):
```toml
[mcp_servers.windows_mcp]
url = "http://127.0.0.1:8765/mcp"
enabled = false
startup_timeout_sec = 5
tool_timeout_sec = 30
```
Only when Windows server and tunnel are up, set `enabled = true`, restart Codex session and inspect `codex mcp list`. Set it back to `false` before overnight sessions. A loopback-only HTTP service is acceptable **because transport is inside SSH**, but anyone with access to the tunneled local port during the session may be able to call tools. Keep the endpoint user-controlled; prefer server authentication if sharing your Unix account.

### Caveats
- A Windows-MCP command cannot run on Linux and control the Windows PC via stdio. The server must run **on Windows**, and Codex must use the forwarded HTTP endpoint.
- Windows-MCP is a powerful computer-control tool (filesystem/PowerShell/Registry); grant only permissions needed for QA and avoid unsupervised Windows operation.
- Desktop input injection may not work on a locked Windows session; Windows-MCP's own control policies can also defer actions while a human is using the PC.
- This transport is **optional** and should not be activated by Unsnooze when Windows is offline. Never make Codex's primary task depend on it.
- The CLI and transport flags are confirmed by the project's documentation at time of this package; verify with `uvx windows-mcp --help` if an update changes them.

## Simpler alternative for early stages
Do Windows tests manually. Commit Linux source, `git pull` on Win11 (or access same repo with Git/VS Code), run the Windows diagnostic POC, and write a short evidence report back to the repo. This is sufficient for the entire G1/G2 investigation and may be less fragile than remote GUI automation.
