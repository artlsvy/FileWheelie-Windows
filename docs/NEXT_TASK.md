# Continue G11 then G12 (G9/G10 implemented)

G9-A/B committed5f656a3/9878e9f. G10 core/Qttray/consent implemented and checked,
with trustedResolveralwaysNone and explicitconfirmeduserpath source. NativeWin
hook/COM/tray/startup acceptance remains pending, does not block next stages.

Next G11: integrate prepared packaging artifacts with app.main/IPC/singleinstance,
frozen Send to/resource paths/self-test; spec/build WindowsPython3.14 only. Packaging
artifacts ownedbyimplementer are ready; root owns application and integration.
Then G12 bundledLibreOffice full-tree locator and tests; don't copy justsoffice.exe.
Build actualWindowsbinary onWindows only; noLinuxcrossbuildclaims. Preservehistory,
source/outputs anddiagnostics. Nootherconversionformats. Complete bothremaining
stages and docs/commits without waitingWindows or furtherprompts.
