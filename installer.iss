[Setup]
AppName=Configurador de Sondas Aviot
AppVersion=2.1
AppPublisher=Ingeniatic Desarrollo S.L.
AppPublisherURL=https://aviot.es
DefaultDirName={autopf}\Configurador Sondas Aviot
DefaultGroupName=Aviot
OutputBaseFilename=Instalador_Sondas_Aviot
SetupIconFile=aviot.ico
UninstallDisplayIcon={app}\Configurador_Sondas_Aviot.exe
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist\Configurador_Sondas_Aviot.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "drivers\CH341SER.EXE"; DestDir: "{app}\drivers"; Flags: ignoreversion; Check: not IsDriverInstalled

[Icons]
Name: "{group}\Configurador de Sondas Aviot"; Filename: "{app}\Configurador_Sondas_Aviot.exe"
Name: "{autodesktop}\Configurador Sondas Aviot"; Filename: "{app}\Configurador_Sondas_Aviot.exe"

[Run]
Filename: "{app}\drivers\CH341SER.EXE"; Description: "Instalar driver USB (CH340)"; Flags: postinstall skipifsilent; Check: not IsDriverInstalled
Filename: "{app}\Configurador_Sondas_Aviot.exe"; Description: "Abrir Configurador de Sondas"; Flags: postinstall nowait skipifsilent

[Code]
function IsDriverInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := RegKeyExists(HKLM, 'SYSTEM\CurrentControlSet\Services\CH341SER');
end;
