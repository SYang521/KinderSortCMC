#define AppName "KinderSort Lite"
#define AppVersion "1.2.0"
#define AppPublisher "KinderSortCMC"
#define AppExeName "KinderSort.exe"

[Setup]
AppId={{A977E0C1-8D67-4C13-91CD-4BD61B0C5385}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\KinderSortLite
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\release
OutputBaseFilename=KinderSortLiteSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExeName}
VersionInfoVersion=1.2.0.0
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
VersionInfoDescription=Offline CPU-only student photo organiser
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\KinderSort\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\KinderSort Lite"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\KinderSort Lite"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\Uninstall KinderSort Lite"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch KinderSort Lite"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  CacheDirectory: String;
  UserChoice: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    UserChoice := MsgBox(
      'KinderSort Lite may have stored reference face encodings on this device.'
      + #13#10 + #13#10
      + 'Face encodings are sensitive biometric data. The cache is stored only '
      + 'on this Windows device and is not uploaded by KinderSort Lite.'
      + #13#10 + #13#10
      + 'Do you want to delete all locally stored KinderSort Lite reference '
      + 'encoding cache files?'
      + #13#10 + #13#10
      + 'Original Reference photos, Event photos, and Output photos will not '
      + 'be deleted.',
      mbConfirmation,
      MB_YESNO
    );

    if UserChoice = IDYES then
    begin
      CacheDirectory := ExpandConstant(
        '{localappdata}\KinderSortLite\cache'
      );

      if DirExists(CacheDirectory) then
      begin
        if not DelTree(CacheDirectory, True, True, True) then
        begin
          MsgBox(
            'KinderSort Lite could not delete all local reference encoding '
            + 'cache files.'
            + #13#10 + #13#10
            + 'You can manually review this folder:'
            + #13#10
            + CacheDirectory,
            mbError,
            MB_OK
          );
        end;
      end;
    end;
  end;
end;