# Recuperación por código de Xomacito

La aplicación solicita el restablecimiento a Supabase Auth, recibe en pantalla un
código de seis dígitos y, después de validarlo, permite elegir una contraseña nueva.

Para que el correo muestre ese código, configura un SMTP propio en **Supabase →
Authentication → SMTP Settings**. Luego abre **Email Templates → Reset password** y
usa esta plantilla:

**Asunto**

```text
{{ .Token }} es tu código de Xomacito
```

**Cuerpo**

```html
<h2>Cambia tu contraseña de Xomacito</h2>
<p>Escribe este código de 6 dígitos en la aplicación:</p>
<p style="font-size: 28px; font-weight: 700; letter-spacing: 6px;">{{ .Token }}</p>
<p>El código vence pronto y solo puede utilizarse una vez.</p>
<p>Si no pediste este cambio, puedes ignorar este correo.</p>
```

No incluyas `{{ .ConfirmationURL }}` en esta plantilla: el flujo de escritorio usa
`{{ .Token }}` y valida el código dentro de Xomacito.
