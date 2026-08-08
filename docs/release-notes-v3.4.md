# Xomacito 3.4 — ¡Rachas de Comunidad Update!

La comunidad ahora tiene un scoreboard más claro, competitivo y seguro, con progreso personal y rachas de actividad.

## Novedades

- Nuevo scoreboard con podio para el top 3, ranking completo y resumen de la comunidad.
- Rachas de actividad representadas con fuego, sin publicar las fechas exactas de conexión.
- Tarjeta personal con posición, descargas, gatos desbloqueados y progreso hacia el siguiente puesto.
- Registro diario y lectura del ranking mediante funciones seguras de Supabase.
- Mejor encuadre de BLACK BULL: rostro y sombrero quedan centrados dentro del aro de rareza.
- El instalador vuelve a incluir el lanzador liviano para que Xomacito abra con mayor rapidez.

## Privacidad y seguridad

- Las contraseñas siguen gestionadas por Supabase Auth y no se guardan dentro de Xomacito.
- El cliente sólo contiene la clave pública de Supabase; no incluye claves administrativas.
- Las fechas de actividad permanecen privadas. El ranking recibe únicamente la racha calculada.

## Verificación

- 114 pruebas automatizadas superadas.
- Lanzador, aplicación empaquetada e instalador verificados en Windows.
- SHA-256 del instalador: `D7D239DF32F5E99BAF4015F9657E35619C6A54FF938FCC1C90AD0BE81D84FA9A`
