# Recuperación por enlace de Xomacito

Xomacito usa el correo de recuperación predeterminado de Supabase, por lo que funciona
en el plan Free sin SMTP propio ni una plantilla personalizada.

1. La aplicación abre un servidor temporal en `127.0.0.1:3000` antes de solicitar el
   correo y envía esa dirección como `redirect_to`.
2. El usuario abre **Reset password** mientras Xomacito permanece abierto.
3. La página local lee la sesión de recuperación del fragmento de la URL, lo elimina
   inmediatamente del historial visible y muestra el formulario de contraseña.
4. El token y la contraseña se envían únicamente al servidor local. Xomacito actualiza
   la cuenta directamente con Supabase Auth y cierra el callback después del éxito.

La interfaz no promete un código de seis dígitos, porque Supabase Free bloquea la
edición de la plantilla y su correo predeterminado contiene `{{ .ConfirmationURL }}`.

Para que el enlace funcione, `http://localhost:3000/` debe permanecer permitido en la
configuración de redirecciones de Supabase Auth y el puerto 3000 debe estar libre.
