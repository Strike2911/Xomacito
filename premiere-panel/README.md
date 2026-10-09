# Xomacito Link 1.6 para Adobe Premiere

Vista compacta centrada en la conexión; **Explorar archivos** abre la biblioteca bajo demanda, sin escanear todas las carpetas al iniciar.

Panel UXP para Premiere 25.6 o posterior. Controles Spectrum nativos, lista con selección múltiple y páginas de 40 archivos. El diseño usa flex; no depende de CSS Grid ni de contenido anidado dentro de botones nativos.

## Conectar
1. Instala o actualiza `Xomacito-Link.ccx` desde **Biblioteca > Conectar Premiere**.
2. Reinicia Premiere y abre **Ventana > Plugins UXP > Xomacito Link**.
3. Vincula la misma carpeta principal que aparece en Biblioteca de Xomacito. Se conserva el permiso.
4. Abre un proyecto: su nombre y conexión aparecen automáticamente. El indicador no exige activar autoimportación.

## Trabajar
- **A Premiere / Importar selección:** envía hasta 500 archivos por lote, incluidos medios vinculados en otras carpetas. El panel organiza Video, Audio, Imágenes y Recortes dentro de `Xomacito Import` y reutiliza medios ya importados.
- **Descargas al cabezal:** opción desactivada inicialmente. Al habilitarla junto con autoimportación, los nuevos resultados individuales se insertan en V1/A1. **Incluir imágenes** controla si las imágenes también se insertan o sólo se importan. Una secuencia cerrada genera un aviso; el archivo permanece disponible en Xomacito.
- **Al cabezal:** inserta un solo archivo en V1/A1 de la secuencia activa, desplazando el material posterior. Usa Deshacer en Premiere para revertir la inserción.
- **Importar nuevas descargas:** recibe eventos de finalización de Modo rápido, Descargar, Cola y Estudio. No escanea Descargas ni importa su contenido anterior. En Modo rápido también se conserva el envío explícito por trabajo. Los resultados no compatibles se omiten.
- **Enviar selección de Premiere a Xomacito:** selecciona medios en el panel Proyecto de Premiere y pulsa este botón. Se vinculan sus originales en Biblioteca, sin copiarlos. Secuencias, carpetas y medios generados sin archivo se omiten; la app confirma cuántos archivos siguen disponibles.
- Para fragmentos, usa **Crear subclip** en Biblioteca y envía el archivo resultante. No crea subclips nativos de Premiere.

## Transporte y compatibilidad
Mensajes locales en `.xomacito-link` dentro de la biblioteca, sin puertos ni permisos de red. Protocolo 2 con lotes, identificación del proyecto por GUID y confirmaciones; mantiene recepción del protocolo 1. La app nueva también admite el panel anterior para envíos manuales.

Las solicitudes caducan a los 120 segundos. Se marcan antes de modificar Premiere para impedir repetir una inserción después de un cierre inesperado. Un fallo parcial informa cuántos elementos completó. No se reintentan automáticamente acciones con resultado incierto.

Mantén el panel visible y Xomacito abierto para los envíos automáticos y de vuelta. Si cambias la carpeta principal, vuelve a vincularla en el panel. No se anuncia conexión si no hay proyecto abierto.

## Desarrollo y validación
`python scripts/build_premiere_panel.py` genera el CCX reproducible en Windows y macOS. Para desarrollo, carga `manifest.json` en UXP Developer Tool 2.2 o posterior.

`node tests/test_premiere_bridge.cjs` comprueba lotes, confirmaciones, repetición, caducidad, GUID y secuencia en un host simulado. `tests/test_quick_workflow.py` verifica ambos sentidos del transporte. La compatibilidad de formatos y el renderizado de Spectrum requieren validación en Premiere.

Referencias de diseño funcional: [DowP](https://github.com/MarckDP/DowP), especialmente su gestor de integraciones y su importador CEP (envíos de archivos terminados, lotes y retorno de selecciones). Xomacito conserva su implementación UXP y su transporte local. No implementa aquí la integración de DowP con otros editores.

[CSS en UXP](https://developer.adobe.com/premiere-pro/uxp/resources/recipes/css-styling/) · [Spectrum](https://developer.adobe.com/premiere-pro/uxp/uxp-api/reference-spectrum/) · [ProjectUtils](https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/projectutils/)
