# Xomacito Link: arquitectura y criterios de interfaz

## Flujo

1. Xomacito crea `Videos/Xomacito` y la usa como destino común de las descargas nuevas.
2. Biblioteca Premiere acepta carpetas arrastradas, analiza de forma recursiva audio y video, conserva metadatos locales y genera miniaturas en una carpeta oculta.
3. El recortador nunca modifica el original. Crea un MP4 H.264/AAC para video o un WAV PCM de 24 bits para audio dentro de `Recortes`.
4. El panel UXP pide acceso sólo a la carpeta que el usuario elige y recuerda esa autorización mediante un token persistente.
5. El panel observa dos veces tamaño y fecha de modificación antes de autoimportar, para no leer una descarga que todavía se está escribiendo.
6. “Importar al bin” reutiliza el elemento si ya existe. “Añadir al cabezal” importa cuando hace falta y usa una transacción deshacible en la secuencia activa.

## Decisiones verificables

- Manifest UXP v5, host `premierepro` y Premiere mínimo 25.6.
- Permiso `localFileSystem: request`; no solicita red ni acceso completo al disco.
- `Project.importFiles` para importar.
- `SequenceEditor.createInsertProjectItemAction`, posición del cabezal y `Project.executeTransaction` para insertar de forma deshacible.
- No existe un servidor local ni un puerto abierto entre Xomacito y Premiere.
- El panel crea o reutiliza un bin raíz llamado `Xomacito Import` y organiza dentro de él `Video`, `Audio`, `Imágenes` y `Recortes`.
- La revisión automática conserva un registro por proyecto, espera archivos estables y consulta el proyecto completo antes de importar para evitar duplicados.

## Criterios de experiencia

- El panel enseña en orden Biblioteca → Proyecto → Autoimportar, con estado textual y una sola acción primaria en cada etapa.
- La búsqueda y los filtros Video, Audio e Imagen conservan una lista compacta para paneles estrechos.
- Se muestran nombre, tipo, duración, tamaño, resolución y códecs para favorecer reconocimiento en lugar de memoria.
- La salida MP4 o WAV se anuncia antes de procesar.
- Originales y recortes aparecen separados por carpeta; el proceso es no destructivo.
- Los botones principales y tiradores tienen áreas cómodas y estados de foco/selección visibles.
- Strike usa capas de gris y acentos apagados; los estados también incluyen texto para no depender sólo del color.

## Referencias

- [Adobe UXP: manifest](https://developer.adobe.com/premiere-pro/uxp/plugins/concepts/manifest/)
- [Adobe UXP: operaciones de archivos](https://developer.adobe.com/premiere-pro/uxp/resources/recipes/filesystem-operations/)
- [Adobe Premiere Project API](https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/project)
- [Adobe Premiere SequenceEditor API](https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/sequenceeditor)
- [Adobe: vistas y metadatos del panel Proyecto](https://helpx.adobe.com/premiere/desktop/get-started/customize-the-project-panel/customization-options-for-the-project-panel.html)
- [Watchtower: sincronización de carpetas, estabilidad y duplicados](https://manuscript.knightsoftheeditingtable.com/extensions/watchtower/what-is-it-for)
- [Mister Horse: biblioteca de usuario y previsualizaciones](https://help.misterhorse.com/hc/en-us/articles/360010189537-User-Library-Help)
- [Adobe Spectrum: fundamentos de color](https://spectrum.adobe.com/page/color-fundamentals/)
- [Adobe Spectrum: uso del color](https://spectrum.adobe.com/page/using-color/)
- [W3C WCAG 2.2: tamaño mínimo de objetivos](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
