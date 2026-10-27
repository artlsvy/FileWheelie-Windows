; Compile with pinned Inno Setup 6.7.3. All payloads are local; no downloads.
#ifndef PayloadDir
  #define PayloadDir SourcePath + "..\build\installer-payload\Filewheel"
#endif

[Setup]
AppId={{B2EA8B48-3A15-476B-8991-62B9764C4907}
AppName=Filewheel
AppVersion=0.1.0
AppPublisher=Filewheel
AppVerName=Filewheel 0.1.0
VersionInfoVersion=0.1.0.0
DefaultDirName={localappdata}\Programs\Filewheel
DefaultGroupName=Filewheel
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
WizardStyle=modern dynamic windows11
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\Filewheel.exe
SetupIconFile={#SourcePath}Filewheel.ico
SourceDir={#PayloadDir}
OutputDir={#SourcePath}..\releases
OutputBaseFilename=FilewheelSetup
Compression=lzma2/normal
SolidCompression=no
DiskSpanning=no
AppMutex=Local\Filewheel.Desktop
SetupMutex=Local\Filewheel.Setup
CloseApplications=no
RestartApplications=no
ChangesAssociations=no
Uninstallable=yes

[Tasks]
Name: "login"; Description: "Start Filewheel when I sign in to Windows"; Flags: unchecked
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
Name: "sendto"; Description: "Add Filewheel to Explorer's Send to menu"

[Files]
Source: "Filewheel.exe"; DestDir: "{app}"; Flags: ignoreversion; BeforeInstall: ShowComponent('Installing Filewheel...')
Source: "DEPENDENCIES.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "_internal\*"; DestDir: "{app}\_internal"; Excludes: "\tools\libreoffice\*,\tools\pandoc\*"; Flags: ignoreversion recursesubdirs createallsubdirs; BeforeInstall: ShowComponent('Installing private Python, Qt and conversion libraries...')
Source: "_internal\tools\libreoffice\*"; DestDir: "{app}\_internal\tools\libreoffice"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: NeedOffice; BeforeInstall: ShowComponent('Installing private LibreOffice for Office-to-PDF...')
Source: "_internal\tools\pandoc\*"; DestDir: "{app}\_internal\tools\pandoc"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: NeedPandoc; BeforeInstall: ShowComponent('Installing private Pandoc for document conversion...')

[Icons]
Name: "{group}\Filewheel"; Filename: "{app}\Filewheel.exe"; Parameters: "--tray"; WorkingDir: "{app}"
Name: "{group}\Uninstall Filewheel"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Filewheel"; Filename: "{app}\Filewheel.exe"; Parameters: "--tray"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Windows\SendTo\Filewheel"; Filename: "{app}\Filewheel.exe"; Parameters: "--gui --"; WorkingDir: "{app}"; Tasks: sendto; Check: CanCreateSendTo

[Run]
Filename: "{app}\Filewheel.exe"; Parameters: "--tray"; Description: "Launch Filewheel"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\installation.ini"

[Code]
const
  RunKey = 'Software\Microsoft\Windows\CurrentVersion\Run';
var
  DependencyPage: TWizardPage;
  Inventory: TNewMemo;
  ReuseTools: TNewCheckBox;
  PandocPath, OfficePath: String;
  PandocVersion, OfficeVersion: String;
  Detected, TasksVisited: Boolean;

procedure ShowComponent(Text: String);
begin
  WizardForm.StatusLabel.Caption := Text;
end;

function OwnedStartupCommand(): String;
begin
  Result := '"' + ExpandConstant('{app}\Filewheel.exe') + '" --tray';
end;

function StartupOwned(Value: String): Boolean;
begin
  Result := (CompareText(Value, OwnedStartupCommand()) = 0) or
    (CompareText(Value, ExpandConstant('{app}\Filewheel.exe') + ' --tray') = 0);
end;

function CanCreateSendTo(): Boolean;
var Link: String;
begin
  Link := ExpandConstant('{userappdata}\Microsoft\Windows\SendTo\Filewheel.lnk');
  { Preserve a pre-existing shortcut; previous Setup ownership remains in its log. }
  Result := not FileExists(Link);
end;

function SupportedVersion(Line, Prefix: String; Major, Minor: Integer): Boolean;
var Text, Digits: String; Index, Dot, FoundMajor, FoundMinor: Integer;
begin
  Result := False;
  if Pos(Prefix, Line) <> 1 then exit;
  Text := Copy(Line, Length(Prefix) + 1, Length(Line));
  Digits := '';
  for Index := 1 to Length(Text) do begin
    if ((Text[Index] >= '0') and (Text[Index] <= '9')) or (Text[Index] = '.') then
      Digits := Digits + Text[Index]
    else break;
  end;
  Dot := Pos('.', Digits);
  if Dot = 0 then exit;
  FoundMajor := StrToIntDef(Copy(Digits, 1, Dot - 1), -1);
  Delete(Digits, 1, Dot);
  Dot := Pos('.', Digits);
  if Dot > 0 then Digits := Copy(Digits, 1, Dot - 1);
  FoundMinor := StrToIntDef(Digits, -1);
  Result := (FoundMajor > Major) or ((FoundMajor = Major) and (FoundMinor >= Minor));
end;

function Probe(Path, Prefix: String; Major, Minor: Integer; var Version: String): Boolean;
var Code, Index: Integer; Output: TExecOutput;
begin
  Result := False;
  if Length(Path) < 3 then exit;
  if (Path[2] <> ':') or ((Path[3] <> '\') and (Path[3] <> '/')) then exit;
  if not FileExists(Path) then exit;
  { Do not reuse the installation being updated as an external dependency. }
  if Pos(Lowercase(AddBackslash(ExpandConstant('{app}'))), Lowercase(Path)) = 1 then exit;
  try
    if not ExecAndCaptureOutput(Path, '--version', ExtractFileDir(Path),
        SW_HIDE, ewWaitUntilTerminated, Code, Output) then exit;
    if (Code <> 0) or Output.Error then exit;
    for Index := 0 to GetArrayLength(Output.StdOut) - 1 do begin
      if SupportedVersion(Output.StdOut[Index], Prefix, Major, Minor) then begin
        Version := Output.StdOut[Index];
        Result := True;
        exit;
      end;
    end;
  except
    Log('Installed tool version probe failed; using private fallback.');
  end;
end;

procedure TryPandoc(Path: String);
begin
  if (PandocPath = '') and Probe(Path, 'pandoc ', 3, 1, PandocVersion) then PandocPath := Path;
end;

procedure TryOffice(Path: String);
begin
  if (OfficePath = '') and
      FileExists(ExtractFileDir(Path) + '\soffice.bin') and
      FileExists(ExtractFileDir(Path) + '\fundamental.ini') and
      Probe(Path, 'LibreOffice ', 7, 6, OfficeVersion) then OfficePath := Path;
end;

procedure DetectTools();
var Search, Part, InstallPath: String; Separator: Integer;
begin
  PandocPath := ''; OfficePath := '';
  TryPandoc(ExpandConstant('{localappdata}\Pandoc\pandoc.exe'));
  TryPandoc(ExpandConstant('{autopf}\Pandoc\pandoc.exe'));
  TryOffice(ExpandConstant('{autopf}\LibreOffice\program\soffice.com'));
  TryOffice(ExpandConstant('{commonpf32}\LibreOffice\program\soffice.com'));
  if RegQueryStringValue(HKLM64, 'Software\LibreOffice\UNO\InstallPath', '', InstallPath) then
    TryOffice(AddBackslash(InstallPath) + 'soffice.com');
  if RegQueryStringValue(HKCU, 'Software\LibreOffice\UNO\InstallPath', '', InstallPath) then
    TryOffice(AddBackslash(InstallPath) + 'soffice.com');
  if RegQueryStringValue(HKLM32, 'Software\LibreOffice\UNO\InstallPath', '', InstallPath) then
    TryOffice(AddBackslash(InstallPath) + 'soffice.com');
  Search := GetEnv('PATH') + ';';
  while Search <> '' do begin
    Separator := Pos(';', Search);
    Part := RemoveQuotes(Trim(Copy(Search, 1, Separator - 1)));
    Delete(Search, 1, Separator);
    { Ignore relative PATH entries: Setup's current directory is not a tool source. }
    if (Length(Part) > 2) and (Part[2] = ':') and
        ((Part[3] = '\') or (Part[3] = '/')) then begin
      TryPandoc(AddBackslash(Part) + 'pandoc.exe');
      TryOffice(AddBackslash(Part) + 'soffice.com');
    end;
  end;
end;

function NeedOffice(): Boolean;
begin
  Result := (OfficePath = '') or not ReuseTools.Checked;
end;

function NeedPandoc(): Boolean;
begin
  Result := (PandocPath = '') or not ReuseTools.Checked;
end;

procedure RefreshInventory(Sender: TObject);
var Text: String;
begin
  Text := 'FILEWHEEL + PRIVATE RUNTIME' + #13#10 +
    'Python 3.14, Qt / PySide6 6.12, image / PDF / Office / Markdown libraries' + #13#10 +
    'Pillow, PyMuPDF, pillow-heif, pdf2docx, MarkItDown, Pandas, NumPy, ' +
    'OpenCV, Magika / ONNX Runtime, python-docx, python-pptx, openpyxl, comtypes.' + #13#10 +
    'Full pinned component list is installed as DEPENDENCIES.txt.' + #13#10 +
    'Installed inside Filewheel. No global Python or Qt changes.' + #13#10#13#10;
  if NeedOffice() then
    Text := Text + 'LIBREOFFICE: private bundled copy will be installed.'
  else Text := Text + 'LIBREOFFICE: reuse ' + OfficeVersion + #13#10 + OfficePath;
  Text := Text + #13#10#13#10;
  if NeedPandoc() then
    Text := Text + 'PANDOC: private bundled copy will be installed.'
  else Text := Text + 'PANDOC: reuse ' + PandocVersion + #13#10 + PandocPath;
  Inventory.Text := Text + #13#10#13#10 +
    'All fallbacks are included in this installer. No internet connection required.';
end;

procedure InitializeWizard();
begin
  DependencyPage := CreateCustomPage(wpSelectDir, 'Included components',
    'Compatible installed tools are reused; missing tools are included.');
  Inventory := TNewMemo.Create(DependencyPage);
  Inventory.Parent := DependencyPage.Surface;
  Inventory.SetBounds(0, 0, DependencyPage.SurfaceWidth, DependencyPage.SurfaceHeight - ScaleY(48));
  Inventory.ReadOnly := True;
  Inventory.ScrollBars := ssVertical;
  ReuseTools := TNewCheckBox.Create(DependencyPage);
  ReuseTools.Parent := DependencyPage.Surface;
  ReuseTools.SetBounds(0, DependencyPage.SurfaceHeight - ScaleY(36), DependencyPage.SurfaceWidth, ScaleY(30));
  ReuseTools.Caption := 'Use compatible installed tools (recommended)';
  ReuseTools.Checked := True;
  ReuseTools.OnClick := @RefreshInventory;
end;

procedure CurPageChanged(CurPageID: Integer);
var Value: String;
begin
  if CurPageID = DependencyPage.ID then begin
    WizardForm.StatusLabel.Caption := 'Checking installed conversion tools...';
    DetectTools(); Detected := True;
    ReuseTools.Enabled := (OfficePath <> '') or (PandocPath <> '');
    RefreshInventory(nil);
  end;
  if (CurPageID = wpSelectTasks) and not TasksVisited then begin
    TasksVisited := True;
    if RegQueryStringValue(HKCU, RunKey, 'Filewheel', Value) and StartupOwned(Value) then
      WizardSelectTasks('login');
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Value: String;
begin
  Result := '';
  if not Detected then DetectTools();
  if not TasksVisited and RegQueryStringValue(HKCU, RunKey, 'Filewheel', Value) and StartupOwned(Value) then
    WizardSelectTasks('login');
  { Recheck availability immediately before copying. A removed tool needs fallback. }
  if (OfficePath <> '') and not FileExists(OfficePath) then OfficePath := '';
  if (PandocPath <> '') and not FileExists(PandocPath) then PandocPath := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var Text, Value, SelectedOffice, SelectedPandoc: String;
begin
  if CurStep = ssPostInstall then begin
    SelectedOffice := ''; SelectedPandoc := '';
    if not NeedOffice() then SelectedOffice := OfficePath;
    if not NeedPandoc() then SelectedPandoc := PandocPath;
    Text := '[Dependencies]' + #13#10 + 'LibreOfficePath=' + SelectedOffice + #13#10 +
      'PandocPath=' + SelectedPandoc + #13#10;
    if not SaveStringToFile(ExpandConstant('{app}\installation.ini'), Utf8Encode(Text), False) then
      RaiseException('Could not save Filewheel dependency selection.');
    if not RegQueryStringValue(HKCU, RunKey, 'Filewheel', Value) or StartupOwned(Value) then begin
      if WizardIsTaskSelected('login') then
        RegWriteStringValue(HKCU, RunKey, 'Filewheel', OwnedStartupCommand())
      else if StartupOwned(Value) then RegDeleteValue(HKCU, RunKey, 'Filewheel');
    end else if WizardIsTaskSelected('login') then
      MsgBox('An existing Filewheel startup entry belongs to another location and was preserved. ' +
        'You can change Start on login from the Filewheel tray menu.', mbInformation, MB_OK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var Value: String;
begin
  if CurUninstallStep = usUninstall then begin
    if RegQueryStringValue(HKCU, RunKey, 'Filewheel', Value) and StartupOwned(Value) then
      RegDeleteValue(HKCU, RunKey, 'Filewheel');
  end;
end;
