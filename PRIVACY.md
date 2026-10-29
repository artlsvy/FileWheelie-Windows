# Privacy policy

Filewheel is a local Windows file converter. It does not require an account and
does not send your files, file names, usage data, or diagnostics to Filewheel's
maintainer. It has no analytics or cloud conversion service.

When you choose a file, Filewheel reads it on your PC and saves the converted
copy locally. The original file is preserved. It stores your wheel and accent
color preferences in `%LOCALAPPDATA%\Filewheel\preferences.json`. Conversion
failures can create rotating diagnostic logs in `%LOCALAPPDATA%\Filewheel\logs`;
these may contain file paths, error messages, and technical details. Optional
diagnostic capture runs only when explicitly enabled and may record file names.
These files stay on your PC unless you choose to share them.

You can remove the local preferences and logs after quitting Filewheel by
deleting `%LOCALAPPDATA%\Filewheel`. Windows and GitHub may handle download or
security-check data under their own policies; that activity is outside
Filewheel's control.

For privacy questions, open an issue at
https://github.com/artlsvy/fileconverter/issues.
