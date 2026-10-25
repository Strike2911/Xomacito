# Revisión de seguridad — 1.4.3 y 1.4.4

## Resultado final aportado el 25 de octubre de 2026

El propietario compartió las capturas del caso **42c3617b-35eb-4d4a-860e-4e5885ca7aa8**: determinación final **Not malware**, sin detección actual en Cloud ni Client (definiciones 1.461.171.0). El analista confirma que los archivos enviados no cumplen los criterios de malware ni de aplicaciones potencialmente no deseadas y que se retiró la detección. La muestra original 1.4.4 corresponde al SHA256 `009f40663451ff706a6f5792a563553353b628b746b2b9fd8abf38473991a645`.

Se registra esa resolución en `windows-security-review.json`. Se limita a la muestra investigada: no certifica compilaciones posteriores ni significa que todos los equipos hayan actualizado sus firmas. 1.4.3 y 1.4.4 siguen retiradas y sus tags permanecen bloqueados. No se han desactivado protecciones ni añadido exclusiones.

Las secciones siguientes conservan la cronología y el estado conocido en cada fecha.

Estado al 23 de octubre de 2026: ambas publicaciones están retiradas. Microsoft recibió el ejecutable original 1.4.4 para investigación; el análisis está pendiente. La validación local del 22 de octubre no reprodujo los bloqueos reportados por otros usuarios. Las secciones siguientes conservan la cronología, no certifican la seguridad del programa.

Defender detectó Behavior:Win32/DefenseEvasion.A!ml durante la instalación el 22 de octubre de 2026. Inteligencia 1.461.155.0, motor 1.1.26100.4. La cuarentena no se ha restaurado ni se han añadido exclusiones.

La release v4.0.43 se ha devuelto a borrador para detener su distribución. No hay confirmación de falso positivo. Las pruebas funcionales y hashes no equivalen a una validación antimalware.

Correcciones de fuente pendientes de publicación: apertura directa del instalador visible; eliminación del script PowerShell con ExecutionPolicy Bypass, cierre forzado y autolimpieza; eliminación de taskkill por nombre en instalación/desinstalación; Restart Manager con consentimiento para archivos en uso.

Estas correcciones no demuestran la causa ni invalidan la detección existente. No se ha recompilado para intentar eludir el bloqueo.

Artefactos para revisión por Microsoft:
- Xomacito-1.4.3-Setup.exe: SHA256 6ec5d190fdc9ffa4166da67781a8352917c8c821c599fe779f4c874fa4a7c9a9
- Xomacito-1.4.3-Update-Light.exe: SHA256 c9f303caccdef9b631d34c76a44c72a8d95dc3802b62c1321f47dc041830b9ca

Portal oficial: https://www.microsoft.com/en-us/wdsi/filesubmission
No se ha enviado una muestra todavía. Se necesita revisión del fabricante antes de restaurar la distribución como segura.

## Validación local de 1.4.4 — 22 de octubre de 2026

Se incorporaron las correcciones descritas al código de 1.4.4, junto con la eliminación de la conversión de video no solicitada. Las pruebas automatizadas relevantes aprobaron (99). Tras actualizar las definiciones de Defender a 1.461.158.0, se analizaron el runtime, el instalador completo y el ligero sin detecciones. El instalador completo terminó correctamente y la aplicación instalada abrió como Xomacito 1.4.4, sin nuevos eventos de detección 1116 durante esa comprobación. No se desactivó Defender ni se añadieron exclusiones.

Estos resultados corresponden al equipo de prueba; no son un dictamen de Microsoft ni invalidan la detección de 1.4.3, que permanece retirada.

- Xomacito-1.4.4-Setup.exe: SHA256 87963d0fa085b4e71d520a65195a8cbc5fb86f59a0b63d9b95d423c20c980b0e
- Xomacito-1.4.4-Update-Light.exe: SHA256 9cea70d3f5c6526bb5727019ce996eb0bb690e44fe564cd5191dce60dbe4f22a

## Reapertura y envío a Microsoft — 23 de octubre de 2026

Se recibió una captura de 1.4.4 al terminar la actualización ligera: ShellExecute error 225 para el ejecutable instalado. El texto no identifica por sí solo la amenaza; no se presupone que la detección sea igual a la de 1.4.3 ni que sea un falso positivo.

Se retiró v4.0.44 y se verificó que el endpoint público de actualización vuelve a v4.0.42. No se recomienda reinstalar una versión bloqueada. No se recompiló ni modificó el binario para intentar evitar el bloqueo.

Con autorización del propietario se envió a Microsoft Security Intelligence el ejecutable original (17.496.531 bytes; SHA256 009f40663451ff706a6f5792a563553353b628b746b2b9fd8abf38473991a645), acompañado de los antecedentes y del comportamiento del actualizador. El portal confirmó la recepción con estado Submitted / Pending. La firma Authenticode del ejecutable es inexistente; eso no demuestra la causa del error 225. No hay certificado de firma disponible en el almacén del usuario.

La publicación queda suspendida en `scripts/publish_release.py` mediante `docs/windows-security-review.json` hasta documentar la resolución de esta investigación. Se conserva el instalador original para reproducibilidad; una prueba funcional o un análisis local limpio no cierran por sí solos el incidente.

## Publicación de la corrección de calidad 1.4.5 — 23 de octubre de 2026

Se consultó el caso 42c3617b-35eb-4d4a-860e-4e5885ca7aa8: estado In progress, dictamen final Pending, detección actual No malware detected tanto en Cloud como en Client (definiciones 1.461.171.0). No hay dictamen final que confirme falso positivo ni una corrección del error 225 en todos los equipos.

Después de informarle que el dictamen seguía pendiente, el propietario pidió publicar la actualización 1.4.5. Se registra una excepción limitada a v4.0.45 y los SHA-256 exactos de sus tres archivos en `windows-security-review.json`. La investigación permanece abierta y 1.4.3/1.4.4 continúan retiradas. Las notas de publicación explican expresamente esta limitación.

El runtime y ambos instaladores 1.4.5 se analizaron localmente sin detecciones. Se comprobó el arranque compilado y la corrección de calidad con muestras reales de 1440p y 1080p a unos 60 FPS. Esta versión contiene cambios funcionales de calidad; no se alteró el empaquetado para eludir detecciones ni se desactivó ninguna protección del sistema.
