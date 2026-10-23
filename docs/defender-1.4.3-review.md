# Revisión de seguridad pendiente — 1.4.3

Defender detectó Behavior:Win32/DefenseEvasion.A!ml durante la instalación el 22 de octubre de 2026. Inteligencia 1.461.155.0, motor 1.1.26100.4. La cuarentena no se ha restaurado ni se han añadido exclusiones.

La release v4.0.43 se ha devuelto a borrador para detener su distribución. No hay confirmación de falso positivo. Las pruebas funcionales y hashes no equivalen a una validación antimalware.

Correcciones de fuente pendientes de publicación: apertura directa del instalador visible; eliminación del script PowerShell con ExecutionPolicy Bypass, cierre forzado y autolimpieza; eliminación de taskkill por nombre en instalación/desinstalación; Restart Manager con consentimiento para archivos en uso.

Estas correcciones no demuestran la causa ni invalidan la detección existente. No se ha recompilado para intentar eludir el bloqueo.

Artefactos para revisión por Microsoft:
- Xomacito-1.4.3-Setup.exe: SHA256 6ec5d190fdc9ffa4166da67781a8352917c8c821c599fe779f4c874fa4a7c9a9
- Xomacito-1.4.3-Update-Light.exe: SHA256 c9f303caccdef9b631d34c76a44c72a8d95dc3802b62c1321f47dc041830b9ca

Portal oficial: https://www.microsoft.com/en-us/wdsi/filesubmission
No se ha enviado una muestra todavía. Se necesita revisión del fabricante antes de restaurar la distribución como segura.
