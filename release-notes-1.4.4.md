# Xomacito 1.4.4 — corrección de recodificación automática

Borrador: código corregido; sin instaladores ni distribución automática hasta completar la revisión de seguridad por la detección de Defender en 1.4.3.

- Las descargas de video conservan el archivo recibido. Ya no se convierten automáticamente a H.264/AAC por estar en WEBM, MKV o usar otro códec dentro de MP4.
- Se mantienen las conversiones solicitadas mediante preset o ajustes avanzados, los recortes precisos y la exportación de audio elegida por el usuario.
- El actualizador abre el instalador visible, sin scripts PowerShell con Bypass ni cierres forzados por nombre de proceso.

La corrección afecta a Descargar y Modo rápido, que comparten el procesamiento. No promete eliminar el consumo de CPU de conversiones o recortes solicitados.

Revisión interna prevista: 4.0.44. No hay instalador validado disponible todavía.
