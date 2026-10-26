# Enable DOCX → PDF on Windows 11

This converter is already implemented. It needs the **normal LibreOffice desktop
application** and PyMuPDF in Filewheel's Python 3.14 environment. It does not need
Microsoft Word, pdf2docx or a separate Python LibreOffice package.

1. Quit Filewheel using its tray menu, not just the wheel's Done button.
2. Install LibreOffice (including Writer). Either use the
   [official Windows installer](https://www.libreoffice.org/installation-instructions/)
   from the [download page](https://www.libreoffice.org/download/), or run:

   ```powershell
   winget install --id TheDocumentFoundation.LibreOffice --exact --source winget
   ```

   This is the main application, not its SDK or HelpPack. Follow the installer or
   WinGet agreement prompts. Filewheel does not install it automatically.
3. In the updated Filewheel checkout, verify detection:

   ```powershell
   .\.venv-filewheel\Scripts\python.exe -c "from filewheel.converters.office import LibreOfficeEngine; e=LibreOfficeEngine(); print('LibreOffice:', e.executable()); print('Ready:', e.available())"
   ```

   Expect a path such as `C:\Program Files\LibreOffice\program\soffice.com` and
   `Ready: True`. If the Python dependency is missing, use the same environment:

   ```powershell
   .\.venv-filewheel\Scripts\python.exe -m pip install -e ".[desktop]"
   ```

4. Restart Filewheel so its capability registry detects the installed engine:

   ```powershell
   .\.venv-filewheel\Scripts\python.exe -m filewheel --tray
   ```

   Enable Experimental Mouse3 if using that route. Middle-click a `.docx`, then
   choose **Docs → PDF**. Send to works through the same controller/converter.

The PDF is saved beside the original DOCX. An existing name gets a numbered
suffix; the input and existing outputs are never replaced. The app uses an
isolated LibreOffice profile, bounded subprocess lifetime and PDF validation.
Fonts/layout depend on LibreOffice and the fonts installed on Windows.

If detection prints `None`, verify the full main LibreOffice application is
installed. Filewheel searches the standard Program Files locations and PATH; it
also supports a complete bundled portable tree (see PORTABLE_LIBREOFFICE.md).
A lone copied `soffice.exe` is insufficient. If `Ready` is false despite a valid
path, check the same venv's PyMuPDF installation with the command above.

If PDF is visible but conversion fails, hover the Failed status and inspect
`%LOCALAPPDATA%\Filewheel\logs\conversion-debug.log`. Macro-bearing documents and
external document resources are intentionally unsupported. PDF → editable DOCX
is a separate pdf2docx engine and does **not** require LibreOffice.

WinGet command syntax: [Microsoft install command documentation](https://learn.microsoft.com/en-us/windows/package-manager/winget/install).
