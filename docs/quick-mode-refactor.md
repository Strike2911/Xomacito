# Revisión del modo rápido — 22 de octubre de 2026

## Alcance y decisiones

La revisión se centra en la cola rápida y su interfaz. Conserva los motores de
descarga, recorte, conversión y envío a Premiere. No es una reescritura de toda la
aplicación ni una reducción del tamaño de FFmpeg o de los modelos de IA.

- `quick_options.py` define las preferencias, opciones visibles, clasificación de
  entradas y captura de ajustes por trabajo. QML consume esas mismas opciones.
- `quick_runner.py` contiene la ejecución de un trabajo. `QuickController` mantiene
  la cola, el historial y la coordinación con la búsqueda.
- Descargar e Historial comparten lista y presentación; las acciones siguen siendo
  específicas de cada vista. El historial no reduce el ancho del área de trabajo.
- La barra acepta enlaces o una búsqueda de texto. Los lotes de enlaces malformados
  no se convierten silenciosamente en búsquedas. Playlist exige un solo enlace.
- Miniatura tiene un único selector y migra las preferencias antiguas. Cada tarea
  conserva una copia de sus recortes y solo sus opciones de ejecución.
- El destino visible y Abrir carpeta usan la misma resolución de etiquetas que la
  cola. Cambiar una etiqueta no modifica un trabajo que ya está en marcha.

## Trabajo eliminado y rendimiento

Se retira el motor de consola y su estado, conexiones y métodos: la pantalla ya
había desaparecido, pero seguían inicializándose. Se conserva el catálogo de gatos
y las herramientas multimedia. Las claves antiguas de preferencias no se borran
del archivo del usuario.

La edición del campo de entrada deja de guardar preferencias por cada tecla. Los
resúmenes de progreso leen columnas escalares, sin copiar las listas de archivos
de todos los trabajos. El modelo compartido y el controlador no emiten cambios
cuando los valores son idénticos. Cancelar todo actualiza el resumen una sola vez
para los trabajos pendientes.

Microbenchmark local: 500 filas con 20 rutas de salida por fila, 200 lecturas del
progreso: copia completa 0,600 s; lectura de columna 0,019 s. Mide únicamente ese
acceso al modelo, no una mejora de velocidad de Internet ni de descarga.

## Validación

150 pruebas ejecutadas: cola, búsqueda/caché, preferencias, cancelación, vista
previa de búsqueda, configuración, dependencias, biblioteca, colección y QML.
La prueba de la nueva pantalla abre Qt real en un proceso aislado con preferencias
temporales, comprueba geometría a 960/1280/1600 píxeles, entrada por teclado,
historial, destino por etiqueta y cierre de búsquedas con resultados tardíos.

La prueba no descarga contenido de servicios externos ni importa archivos en una
instancia real de Premiere. Esas integraciones se conservan y no se atribuye a
esta revisión una validación nueva de sus servicios remotos.
