# Estudio y economía de gatos

Esta revisión corresponde a Xomacito 1.2 (versión interna 4.0.19). El instalador completo se genera como `release/Xomacito-1.2-Setup.exe`. También puede ejecutarse desde el código con `Probar-Xomacito.cmd` y el Python de desarrollo local. Compilar o instalar localmente no publica la versión en GitHub.

## Estudio

Importación por archivo, arrastre, portapapeles o enlace. Removedor de fondo, mejora de resolución y conversión. Vista previa junto a los ajustes, con nombre, formato y carpeta de salida accesibles. Comparador antes/después al terminar, arrastrable y compatible con las flechas del teclado.

Los resultados se relacionan con el ID del archivo: nombres repetidos y cambios de selección no mezclan imágenes. Las vistas previas raster conservan transparencia y orientación EXIF y no cargan los motores de IA.

Descarga, Cola y Estudio comparten dos sprites originales, estela arcoíris, posición proporcional y respeto al ajuste de animaciones. Estudio reserva el 100% para la finalización.

## Moneda virtual

El símbolo `$` representa saldo de juego. No hay compras, pagos ni retiros de dinero real. Cada 10 fuentes válidas descargadas se conceden $1.00. Se conservan el contador existente y sus hashes para evitar volver a premiar el mismo contenido. Los bonos existentes se convierten a $1.00 por tirada autorizada.

| Caja | Precio | Probabilidades |
|---|---:|---|
| Regalo diario | Gratis, una vez al día | Común 48%, peculiar 28%, raro 15%, épico 7%, legendario 1.8%, mítico 0.2% |
| Callejera | $1.00 | Común 48%, peculiar 28%, raro 15%, épico 7%, legendario 1.8%, mítico 0.2% |
| Estelar | $5.00 | Peculiar 15%, raro 35%, épico 30%, legendario 17%, mítico 3% |
| Celestial | $15.00 | Raro 10%, épico 25%, legendario 45%, mítico 20% |

Cada apertura entrega una copia; puede repetirse aunque falten gatos por descubrir. El resultado se decide y persiste antes de iniciar la ruleta. Omitir la animación no cambia el premio. Los exclusivos promocionales quedan fuera de las cajas.

| Rareza | Venta por copia |
|---|---:|
| Común | $0.10–$0.25 |
| Peculiar | $0.30–$0.55 |
| Raro | $0.70–$1.40 |
| Épico | $2.00–$4.00 |
| Legendario | $6.00–$10.00 |
| Mítico | $20.00–$35.00 |

Cada ID tiene un valor estable dentro de su rareza. Una prueba calcula el retorno esperado con el catálogo real y verifica que es menor que el precio de cada caja pagada. Las cajas caras mejoran las probabilidades de rarezas altas. Precios y pesos están centralizados en `src/core/cat_gacha.py`.

## Inventario y migración

- Cajas y Mis gatos son apartados separados, con búsqueda y filtro por rareza.
- El inventario muestra cantidades, precio por copia, valor total, equipamiento y venta individual.
- La última copia equipada se protege; se puede equipar otro gato para venderla.
- Los descubrimientos y auras se conservan al vender; las cantidades representan las copias actuales.
- El scoreboard clasifica por descargas de la Temporada 1. La base de datos conserva el total histórico y resta una base de inicio; usuarios con igual cantidad comparten puesto. Las cajas, ventas y saldo no suman puntos. El contador de gatos muestra copias actuales.
- El schema 6 convierte tiradas pendientes a saldo y desbloqueos/duplicados a cantidades. Guarda el estado heredado en `cat_gacha_legacy_backup`.
- Saldo e inventario se sincronizan como un bloque con revisión y desempate estable. Una cantidad cero marca una venta y evita reconstruir esa copia desde un máximo histórico.
- Se conserva el mecanismo existente de snapshots. Ante operaciones simultáneas sin sincronizar en varios equipos, prevalece una revisión económica completa; no es un sistema de transacciones entre dispositivos. Usar una sesión a la vez para abrir/vender.
- La migración `season_1_compensated_cat_reset` se aplicó al servidor el 6 de septiembre de 2026. Guarda perfiles y colecciones anteriores en un esquema privado y protege la compensación frente a escrituras de aplicaciones antiguas.

## Conversión de temporada

Schema 7 y `economyEpoch: 1` venden todas las copias anteriores por su precio individual, añaden ese valor al saldo existente y regalan un gato inicial. Se conservan historial de descargas, fuentes ya recompensadas, descubrimientos y auras. El reinicio es idempotente; volver a abrir o sincronizar no vuelve a pagar.

En la aplicación de la migración había 37 cuentas: se convirtieron las 22 colecciones presentes en el servidor por un total de $1,867.86 virtuales; las otras 15 quedaron pendientes hasta sincronizar su inventario local. No se inventan rarezas a partir de un conteo. Se preservaron las 1,610 descargas históricas y el nuevo marcador empezó en cero.

## Fluidez y aperturas

La cuadrícula usa un modelo filtrado de Qt: vender actualiza roles y retira solo las filas necesarias, sin reconstruir todas las tarjetas. Se reutilizan metadatos del catálogo, los efectos de tarjetas fuera de pantalla se detienen y la sincronización agrupa cambios con 700 ms de espera, evitando solicitudes idénticas. El saldo sigue guardándose de forma atómica en disco.

«Omitir animación» es un botón activable en Cajas y en el resultado. La preferencia se guarda por dispositivo y evita incluso construir la tira de la ruleta cuando está activa; el premio y su persistencia siguen siendo los mismos.

## Verificación

Pruebas de migración, sincronización obsoleta, descargas duplicadas, venta, aperturas dobles, probabilidades y retorno esperado. Asociación de resultados y controles Qt con ratón/teclado a 960×680. Regresiones de Descarga, Cola, cuentas y Qt.

Se ejecutó el removedor real con `birefnet-general.onnx` en CPU sobre una fotografía del catálogo. Produjo un PNG RGBA con transparencia y el comparador correcto al 100%.
