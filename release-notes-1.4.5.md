# Xomacito 1.4.5 — Corrección de calidad de YouTube

**Preparación de lanzamiento: investigación de Defender todavía abierta.** Esta versión corrige la selección de calidad. No se ha confirmado una solución al bloqueo de Windows con error 225 reportado en 1.4.3 y 1.4.4. No desactives la protección ni añadas exclusiones para ejecutar un archivo bloqueado.

- YouTube usa los clientes predeterminados de yt-dlp. El cliente incrustado que limitaba algunos enlaces a 360p solo queda como alternativa ante errores de acceso.
- Modo rápido reconoce correctamente los videos verticales y prioriza resolución y FPS antes que compatibilidad de códec.
- Si se pide una resolución numérica que el sitio no ofrece, se informa antes de descargar una inferior. Se puede elegir otra calidad o Mejor disponible.
- Las preferencias nuevas usan Mejor disponible; las elecciones guardadas se conservan.
- El archivo descargado se verifica por resolución y FPS. Se mantiene la eliminación de la recodificación automática no solicitada.

Validación de la corrección: 205 pruebas aprobadas. Con el enlace reportado se descargaron muestras reales a 1440p y 1080p, ambas a unos 60 FPS, mediante copia de streams. Esto verifica ese enlace en el equipo de prueba; no garantiza el catálogo de todas las cuentas o regiones ni certifica el resultado del antivirus.

Paquetes generados el 23 de octubre de 2026. La comprobación de arranque del programa compilado terminó correctamente. El runtime y ambos instaladores pasaron los análisis locales de Defender sin detecciones; el caso de Microsoft sobre 1.4.4 sigue sin una resolución confirmada aquí.

Revisión interna: 4.0.45. El instalador completo es necesario para versiones antiguas; el ligero requiere una instalación existente con sus componentes.
