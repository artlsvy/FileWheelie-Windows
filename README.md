# Filewheel

Convert files straight from Windows File Explorer. Middle-click a file, choose
an output format from the wheel, and let Filewheel create a converted copy.
Your original file stays in place.

This project was fully **vibecoded with OpenAI Codex**. It was created as an
experiment to see what Codex could build, from the app itself to its installer.

## A look at the app

These are real UI captures with transparent backgrounds.

| Choose a format | Track a conversion | See more details |
| --- | --- | --- |
| ![Filewheel selection wheel](assets/ui/wheel.png) | ![Compact conversion progress](assets/ui/progress.png) | ![Expanded conversion progress](assets/ui/expanded.png) |

## Download and install

**[Download Filewheel v0.2 for Windows](https://github.com/artlsvy/fileconverter/releases/download/v0.2/FilewheelSetup.exe)**

1. Quit any older copy of Filewheel.
2. Open **FilewheelSetup.exe** and follow the installer.
3. Launch Filewheel from the Start menu or the installer's Finish page.

You need **Windows 11 on an Intel or AMD 64-bit PC**. Everything needed is
included. You do not need to install Python or download extra tools.
If compatible LibreOffice or Pandoc installations are found, Filewheel can use
those instead of installing its own copies.

## Use it

1. Find a file in File Explorer.
2. Middle-click it with your mouse, or use a touchpad gesture set to middle-click.
3. Choose a category, then a file format.
4. Follow the progress indicator until the conversion finishes.

If Filewheel asks you to confirm a file, check that the displayed path is right.
You can also right-click a file and choose **Show more options > Send to > Filewheel**
if you selected that option during installation.

Filewheel handles pictures, PDFs, Word documents, presentations, spreadsheets,
Markdown and text files. The wheel only shows conversions available for that file.

## Tray menu

Find Filewheel beside the Windows clock. You may need to open the hidden icons.

- **Enable wheel** turns mouse and touchpad activation on or off.
- **Start on login** starts Filewheel when you sign in to Windows.
- **Quit Filewheel** closes the app.

Mouse and touchpad activation are on by default. Start on login is optional.

## Your files stay on your PC

Conversions work locally. No account, internet connection or uploads are needed.
To uninstall, open **Windows Settings > Apps > Installed apps > Filewheel**.

[Installer and build notes](INSTALL.md)
