# Xomacito 1.2.9 — Mac Version DMG + Windows

Esta release reúne el instalador completo de macOS y la actualización ligera original de Windows. Ambos corresponden a Xomacito 1.2.9 (revisión interna 4.0.28).

## Descargas

| Archivo | Sistema | Uso |
| --- | --- | --- |
| `Xomacito-1.2.9-arm64.dmg` | Apple Silicon (M1 o posterior), macOS 26 o posterior | Instalación completa de Mac |
| `Xomacito-1.2.9-Update-Light.exe` | Windows 10/11 de 64 bits | Actualización de una instalación existente |

**Mac:** abre el DMG, arrastra Xomacito a Applications y abre la aplicación desde Aplicaciones. Incluye Python y las herramientas multimedia; Homebrew no es necesario. Los modelos de IA opcionales se descargan al solicitarlos. No incluye una compilación para Mac Intel.

El paquete de Mac utiliza firma local y no está notarizado por Apple. Si macOS bloquea la primera apertura tras descargarlo, intenta abrir la copia en Aplicaciones y autorízala desde Ajustes del Sistema → Privacidad y seguridad → Abrir igualmente. No es necesario desactivar Gatekeeper.

**Windows:** el `.exe` se conserva exactamente como fue publicado en esta release; es una actualización ligera, no un instalador completo. Para instalar por primera vez, instala el [paquete completo Xomacito 1.2](https://github.com/Strike2911/Xomacito/releases/download/v4.0.19/Xomacito-1.2-Setup.exe) y después ejecuta la actualización 1.2.9.

## Trabajo para macOS

- Empaquetado nativo de Python, Qt/QML, FFmpeg, Deno, Poppler, Ghostscript y bibliotecas de imagen.
- Corrección del conflicto de HarfBuzz en las conversiones PDF.
- Verificación de recursos activa también en la aplicación optimizada.
- Detección del mínimo de macOS exigido por los componentes nativos.
- Validación del runtime, firma local y estructura/integridad del DMG.

## Cambios de Xomacito 1.2.9

- Corrige el falso aviso «Video unavailable» de YouTube mediante un reintento con los clientes predeterminados de yt-dlp.
- El reintento conserva formato, calidad, destino y cookies; se aplica también a las vistas previas.
- Retira el gato siamés; conserva el clásico y el naranja y migra la selección anterior al clásico.

El archivo `Xomacito-1.2.9-SHA256.txt` contiene las sumas SHA-256 de las dos descargas.
