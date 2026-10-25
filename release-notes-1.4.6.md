# Xomacito 1.4.6 — Videos preparados para Premiere

- Nueva opción **Premiere · alta calidad** en Modo rápido y Descargar. Comprueba los códecs reales y prepara una copia compatible cuando hace falta, conservando resolución, FPS y el original.
- En Biblioteca, **Preparar para Premiere** permite convertir videos VP9/AV1 ya descargados. Un archivo MP4 no necesariamente contiene un códec que Premiere admita.
- La preparación se puede cancelar y limita los hilos del codificador y su prioridad en Windows. Una conversión 4K sigue consumiendo CPU y tarda; la interfaz lo indica.
- Los archivos compatibles pasan sin recodificar. SDR de 8 bits utiliza H.264 de alta calidad; HDR/10 bits o transparencia utiliza ProRes y requiere más espacio. La conversión no es sin pérdida.
- La cola contempla videos verticales y evita alternativas silenciosas de menor resolución. Si la calidad solicitada no está disponible, informa del problema.
- **Xomacito Link 1.6.1** explica qué archivos requieren preparación. La autoimportación no inicia conversiones por su cuenta.

Para usar el panel actualizado: Biblioteca → Conectar Premiere → Instalar / actualizar; después reinicia Premiere.

Validación de la corrección: 500 pruebas aprobadas, 2 omitidas y pruebas del puente JavaScript aprobadas. El Short reportado se preparó como H.264 a 2160 × 3840 y 60 FPS, conservando sus 4.097 fotogramas y el audio AAC estéreo. La importación dentro de Premiere real sigue pendiente: el equipo de prueba mostró un aviso de recuperación al iniciarlo.

Microsoft clasificó la muestra original 1.4.4 enviada como **Not malware** y retiró su detección, según el resultado final aportado por el propietario. Esto se refiere a esa muestra; no es una certificación de todos los archivos o equipos. Las versiones 1.4.3 y 1.4.4 permanecen retiradas.

Revisión interna: **4.0.46**. El instalador completo permite actualizar versiones antiguas, incluida 3.3. El paquete ligero requiere una instalación existente con sus componentes. Esta publicación contiene los paquetes para Windows.
