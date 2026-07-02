; DairyERP Inno Setup Script

[Setup]
AppName=Dairy ERP System
AppVersion=1.0.0
AppPublisher=Your Company Name
DefaultDirName={autopf}\DairyERP
DefaultGroupName=Dairy ERP System
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=DairyERP_Setup_v1.0.0
SetupIconFile=assets\app_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\DairyERP.exe
UninstallDisplayName=Dairy ERP System

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop shortcut"; GroupDescription: "Additional Icons:"; Flags: unchecked

[Files]
Source: "dist\DairyERP\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\reports\sales_reports"
Name: "{app}\reports\production_reports"
Name: "{app}\reports\pdf_reports"
Name: "{app}\invoices\pdf_bills"
Name: "{app}\invoices\print_bills"
Name: "{app}\backups\database_backups"

[Icons]
Name: "{group}\Dairy ERP System"; Filename: "{app}\DairyERP.exe"
Name: "{group}\Uninstall Dairy ERP"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Dairy ERP System"; Filename: "{app}\DairyERP.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DairyERP.exe"; Description: "Launch Dairy ERP System"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel2.Caption :=
    'This will install Dairy ERP System on your computer.' + #13#10 + #13#10 +
    'Default login after install:' + #13#10 +
    '  Username: admin' + #13#10 +
    '  Password: admin123' + #13#10 + #13#10 +
    'Please change your password after first login.';
end;
