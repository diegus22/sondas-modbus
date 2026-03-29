[Setup]
AppName=Configurador de Sondas Aviot
AppVersion=3.4
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
Source: "drivers\CH341SER.EXE"; DestDir: "{app}\drivers"; Flags: ignoreversion

[Icons]
Name: "{group}\Configurador de Sondas Aviot"; Filename: "{app}\Configurador_Sondas_Aviot.exe"
Name: "{autodesktop}\Configurador Sondas Aviot"; Filename: "{app}\Configurador_Sondas_Aviot.exe"

[Run]
; Siempre abre la app (con splash de instrucciones)
Filename: "{app}\Configurador_Sondas_Aviot.exe"; Flags: postinstall nowait skipifsilent
; Solo abre el driver si NO esta instalado
Filename: "{app}\drivers\CH341SER.EXE"; Flags: postinstall skipifsilent waituntilterminated; Check: not IsDriverInstalled

[Code]
function IsDriverInstalled: Boolean;
begin
  // Detecta driver CH340 en el registro de Windows
  Result := RegKeyExists(HKLM, 'SYSTEM\CurrentControlSet\Services\CH341SER')
         or RegKeyExists(HKLM, 'SYSTEM\CurrentControlSet\Services\CH341SER_A64');
end;
