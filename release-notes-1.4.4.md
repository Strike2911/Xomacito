# Xomacito 1.4.4 — corrección de recodificación automática

**Retirada el 23 de octubre de 2026:** usuarios reportaron bloqueos del ejecutable por Windows (error 225) también en esta versión. El archivo original se envió a Microsoft; el análisis está pendiente. No utilizar exclusiones ni desactivar la protección para ejecutar el archivo bloqueado.

- Las descargas de video conservan el archivo recibido. Ya no se convierten automáticamente a H.264/AAC por estar en WEBM, MKV o usar otro códec dentro de MP4.
- Se mantienen las conversiones solicitadas mediante preset o ajustes avanzados, los recortes precisos y la exportación de audio elegida por el usuario.
- El actualizador abre el instalador visible, sin scripts PowerShell con Bypass ni cierres forzados por nombre de proceso.

La corrección afecta a Descargar y Modo rápido, que comparten el procesamiento. No promete eliminar el consumo de CPU de conversiones o recortes solicitados.

Validación: 99 pruebas automatizadas aprobadas. El runtime y el instalador completo se analizaron con Microsoft Defender actualizado sin detecciones. La instalación y apertura de 1.4.4 en el equipo de prueba no produjeron nuevas alertas. Esto no constituye una confirmación de Microsoft sobre la detección anterior; 1.4.3 continúa retirada.

Revisión interna: 4.0.44. Para versiones antiguas, usa el instalador completo; el paquete ligero requiere una instalación existente con sus componentes.
