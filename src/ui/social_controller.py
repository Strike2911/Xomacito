from __future__ import annotations

import base64
import binascii
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
from PySide6.QtCore import QObject, Property, Signal, Slot


_AUTH_CALLBACK_PAGE = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cuenta protegida · Xomacito</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, "Segoe UI", sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 24px;
      color: #edfaff; background: radial-gradient(circle at 50% 12%, #073247 0, #03131e 48%, #020a11 100%); }
    main { width: min(560px, 100%); padding: 42px; border: 1px solid #16d9ef; border-radius: 24px;
      background: rgba(4, 26, 38, .94); box-shadow: 0 24px 80px rgba(0, 0, 0, .5), 0 0 30px rgba(22, 217, 239, .13); }
    .icon { width: 66px; height: 66px; display: grid; place-items: center; margin-bottom: 24px;
      border-radius: 50%; color: #06141b; background: #9af53e; font-size: 34px; font-weight: 900; }
    small { color: #1ee6f4; font-size: 12px; font-weight: 800; letter-spacing: 1.5px; }
    h1 { margin: 10px 0 12px; font-size: clamp(28px, 6vw, 40px); }
    p { margin: 0; color: #9fc1d1; font-size: 16px; line-height: 1.55; }
    strong { color: #edfaff; }
    form { display: grid; gap: 14px; margin-top: 26px; }
    label { color: #cce8f3; font-size: 13px; font-weight: 700; }
    input { width: 100%; margin-top: 7px; padding: 14px 15px; border: 1px solid #315366; border-radius: 12px;
      color: #edfaff; background: #071d29; font: inherit; outline: none; }
    input:focus { border-color: #1ee6f4; box-shadow: 0 0 0 3px rgba(30, 230, 244, .12); }
    button { padding: 14px 18px; border: 0; border-radius: 12px; color: #05141c; background: #69e7f4;
      font: inherit; font-weight: 800; cursor: pointer; }
    button:disabled { cursor: wait; opacity: .58; }
    #status { min-height: 24px; margin-top: 14px; color: #ffcf70; font-size: 14px; }
    [hidden] { display: none !important; }
  </style>
</head>
<body>
  <main>
    <section id="verifiedView">
      <div class="icon">✓</div>
      <small>XOMACITO · CUENTA PROTEGIDA</small>
      <h1>Correo verificado</h1>
      <p><strong>La confirmación se completó correctamente.</strong><br>
        Ya puedes cerrar esta pestaña y volver a Xomacito.</p>
    </section>
    <section id="resetView" hidden>
      <div class="icon">↻</div>
      <small>XOMACITO · RECUPERAR CUENTA</small>
      <h1>Crea una contraseña nueva</h1>
      <p>El enlace ya verificó tu identidad. Elige una contraseña de al menos 8 caracteres.</p>
      <form id="resetForm">
        <label>Nueva contraseña
          <input id="password" type="password" minlength="8" maxlength="256" autocomplete="new-password" required>
        </label>
        <label>Repite la contraseña
          <input id="confirmation" type="password" minlength="8" maxlength="256" autocomplete="new-password" required>
        </label>
        <button id="submitButton" type="submit">Cambiar contraseña</button>
      </form>
      <p id="status" role="status" aria-live="polite"></p>
    </section>
  </main>
  <script>
    (() => {
      const fragment = new URLSearchParams(window.location.hash.slice(1));
      const isRecovery = fragment.get("type") === "recovery";
      const accessToken = fragment.get("access_token") || "";
      const refreshToken = fragment.get("refresh_token") || "";
      window.history.replaceState(null, "", window.location.pathname);

      if (!isRecovery || !accessToken) {
        fetch("/email-confirmed", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}"
        }).catch(() => {});
        return;
      }

      document.getElementById("verifiedView").hidden = true;
      document.getElementById("resetView").hidden = false;
      const form = document.getElementById("resetForm");
      const status = document.getElementById("status");
      const button = document.getElementById("submitButton");
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const password = document.getElementById("password").value;
        const confirmation = document.getElementById("confirmation").value;
        if (password.length < 8) {
          status.textContent = "La contraseña debe tener al menos 8 caracteres.";
          return;
        }
        if (password !== confirmation) {
          status.textContent = "Las contraseñas no coinciden.";
          return;
        }
        button.disabled = true;
        status.textContent = "Protegiendo tu cuenta…";
        try {
          const response = await fetch("/password-reset", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ access_token: accessToken, refresh_token: refreshToken, password })
          });
          const result = await response.json();
          if (!response.ok || !result.ok) throw new Error(result.message || "No se pudo cambiar la contraseña.");
          form.hidden = true;
          status.style.color = "#9af53e";
          status.textContent = "Contraseña cambiada. Ya puedes cerrar esta pestaña y volver a Xomacito.";
        } catch (error) {
          button.disabled = false;
          status.textContent = error.message || "El enlace venció. Solicita uno nuevo desde Xomacito.";
        }
      });
    })();
  </script>
</body>
</html>
""".encode("utf-8")


class _RecoveryEmailCallbackHandler(BaseHTTPRequestHandler):
    def _respond(self, status: int, body: bytes, content_type: str, *, include_body: bool = True):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if content_type.startswith("text/html"):
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                "connect-src 'self'; form-action 'none'; base-uri 'none'",
            )
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._respond(status, body, "application/json; charset=utf-8")

    def do_GET(self):
        self._respond(200, _AUTH_CALLBACK_PAGE, "text/html; charset=utf-8")

    def do_HEAD(self):
        self._respond(200, _AUTH_CALLBACK_PAGE, "text/html; charset=utf-8", include_body=False)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path == "/email-confirmed":
            callback = getattr(self.server, "xomacito_callback", None)
            if callable(callback):
                callback()
            self._json(200, {"ok": True})
            return
        if path != "/password-reset":
            self._json(404, {"ok": False, "message": "Ruta no encontrada."})
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > 16_384:
            self._json(400, {"ok": False, "message": "Solicitud inválida."})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, ValueError, TypeError):
            self._json(400, {"ok": False, "message": "Solicitud inválida."})
            return

        access_token = str(payload.get("access_token") or "")
        refresh_token = str(payload.get("refresh_token") or "")
        password = str(payload.get("password") or "")
        if not access_token or len(access_token) > 8192 or len(refresh_token) > 8192:
            self._json(400, {"ok": False, "message": "El enlace es inválido o ya venció."})
            return
        if len(password) < 8 or len(password) > 256:
            self._json(400, {"ok": False, "message": "La contraseña debe tener entre 8 y 256 caracteres."})
            return

        callback = getattr(self.server, "xomacito_password_reset", None)
        if not callable(callback):
            self._json(503, {"ok": False, "message": "Xomacito no está listo para cambiar la contraseña."})
            return
        try:
            callback(access_token, refresh_token, password)
        except (RuntimeError, requests.RequestException) as error:
            self._json(400, {"ok": False, "message": str(error) or "El enlace venció. Solicita uno nuevo."})
            return
        self._json(200, {"ok": True})

    def log_message(self, _format, *_args):
        return


class SocialController(QObject):
    """Cliente ligero de Supabase Auth/REST sin guardar contraseñas localmente."""

    stateChanged = Signal()
    notificationRequested = Signal(str, str, str)
    onboardingRequested = Signal()
    recoveryEmailRequired = Signal()
    recoveryEmailCallbackReceived = Signal()
    passwordRecoveryCompleted = Signal("QVariantMap")
    collectionStateReceived = Signal("QVariantMap")
    signupBonusGranted = Signal(int)

    RECOVERY_CALLBACK_HOST = "127.0.0.1"
    RECOVERY_CALLBACK_PORT = 3000
    CREATOR_GIFTS = {
        "mensva": {
            "campaign": "mensva-51-rolls-2026-08-25",
            "amount": 51,
            "title": "Un regalo especial para mensva",
            "message": "Strike te dejó 51 tiradas gatunas. No necesitas agregar un correo para recibirlas.",
        },
    }

    def __init__(self, project_root: str | Path, settings, pool, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.settings = settings
        self.pool = pool
        self._url, self._anon_key, self._username_domain = self._load_config()
        # Las operaciones del marcador se ejecutan desde el pool compartido.  Un
        # refresh-token de Supabase rota en cada uso, por lo que dos renovaciones
        # simultáneas podían invalidarse mutuamente y dejar una llamada aislada
        # con 401.  Este candado mantiene una única renovación en vuelo.
        self._session_lock = threading.RLock()
        self._recovery_callback_server = None
        self._recovery_callback_thread = None
        self.recoveryEmailCallbackReceived.connect(self._recovery_email_callback_received)
        self.passwordRecoveryCompleted.connect(self._password_reset_succeeded)
        self._local_cat_count: int | None = None
        self._local_equipped_cat_id = ""
        self._local_collection_state: dict = {}
        self._collection_sync_inflight = False
        self._collection_sync_queued = False
        saved_email = str(settings.get("social_email", "")).strip().lower()
        self._state = {
            "configured": bool(self._url and self._anon_key),
            "authenticated": bool(settings.get("social_access_token", "")),
            "username": str(settings.get("social_username", "")),
            "email": saved_email,
            "busy": False,
            "emailBusy": False,
            "error": "",
            "emailError": "",
            "needsRecoveryEmail": bool(
                settings.get("social_access_token", "")
                and self._account_requires_recovery_email(saved_email)
            ),
            "recoveryEmailUpdatePending": False,
            "verificationPending": False,
            "recoveryLinkSent": False,
            "recoveryEmail": "",
            "leaderboard": [],
            "currentRank": 0,
            "currentDownloads": 0,
            "currentCats": 0,
            "currentStreak": 0,
            "bestStreak": 0,
            "communityDownloads": 0,
            "communityCats": 0,
            "activePlayers": 0,
            "currentEquippedCatId": "",
        }

    def _recovery_email_redirect_url(self):
        return f"http://localhost:{self.RECOVERY_CALLBACK_PORT}/"

    def _start_recovery_callback_server(self):
        if self._recovery_callback_server is not None:
            return True
        try:
            server = ThreadingHTTPServer(
                (self.RECOVERY_CALLBACK_HOST, self.RECOVERY_CALLBACK_PORT),
                _RecoveryEmailCallbackHandler,
            )
        except OSError as error:
            print(f"No se pudo abrir el callback local de cuenta: {error}")
            self.notificationRequested.emit(
                "warning", "Página local no disponible",
                "Xomacito necesita el puerto local 3000 para recibir el enlace del correo. "
                "Cierra el programa que lo esté usando y vuelve a intentarlo.",
            )
            return False
        server.daemon_threads = True
        server.xomacito_callback = self.recoveryEmailCallbackReceived.emit
        server.xomacito_password_reset = self._password_reset_link_callback
        thread = threading.Thread(
            target=server.serve_forever,
            name="xomacito-email-confirmation",
            daemon=True,
        )
        self._recovery_callback_server = server
        self._recovery_callback_thread = thread
        thread.start()
        return True

    def _stop_recovery_callback_server(self):
        server = self._recovery_callback_server
        thread = self._recovery_callback_thread
        self._recovery_callback_server = None
        self._recovery_callback_thread = None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)

    @Slot()
    def _recovery_email_callback_received(self):
        if self._state["authenticated"]:
            self.checkRecoveryEmail()
            return
        self._stop_recovery_callback_server()
        self.notificationRequested.emit(
            "success", "Correo verificado",
            "La confirmación terminó. Inicia sesión para continuar.",
        )

    def _load_config(self):
        url = os.getenv("XOMACITO_SUPABASE_URL", "").strip().rstrip("/")
        key = (
            os.getenv("XOMACITO_SUPABASE_PUBLISHABLE_KEY", "").strip()
            or os.getenv("XOMACITO_SUPABASE_ANON_KEY", "").strip()
        )
        username_domain = os.getenv("XOMACITO_SOCIAL_USERNAME_DOMAIN", "").strip().lower()
        candidates = [
            self.project_root / "assets" / "config" / "social.json",
            Path(__file__).resolve().parents[2] / "assets" / "config" / "social.json",
        ]
        for path in candidates:
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError, TypeError):
                continue
            url = url or str(payload.get("supabase_url") or "").strip().rstrip("/")
            key = key or str(
                payload.get("supabase_publishable_key")
                or payload.get("supabase_anon_key")
                or ""
            ).strip()
            username_domain = username_domain or str(
                payload.get("username_domain") or ""
            ).strip().lower()
            if url and key:
                break
        if not username_domain and url:
            username_domain = url.removeprefix("https://").removeprefix("http://").split("/", 1)[0]
        return url, key, username_domain

    @Property("QVariantMap", notify=stateChanged)
    def state(self):
        return dict(self._state)

    def _set_state(self, **values):
        changed = False
        for key, value in values.items():
            if self._state.get(key) != value:
                self._state[key] = value
                changed = True
        if changed:
            self.stateChanged.emit()

    def _access_token(self) -> str:
        with self._session_lock:
            return str(self.settings.get("social_access_token", "")).strip()

    def _headers(self, *, authenticated=False, access_token: str | None = None):
        headers = {"apikey": self._anon_key, "Content-Type": "application/json"}
        token = access_token if authenticated and access_token is not None else (
            self._access_token() if authenticated else self._anon_key
        )
        headers["Authorization"] = f"Bearer {token}"
        return headers

    @staticmethod
    def _normalize_username(username: str):
        normalized = re.sub(r"[^a-z0-9_-]+", "-", username.strip().lower()).strip("-_")
        normalized = re.sub(r"[-_]{2,}", "-", normalized)
        if len(normalized) < 3:
            raise ValueError("La ID debe tener al menos 3 letras o números.")
        if len(normalized) > 32:
            raise ValueError("La ID puede tener como máximo 32 caracteres.")
        return normalized

    def _email_for_username(self, username: str):
        """Conserva el acceso de las IDs antiguas que usaban un correo interno."""
        normalized = self._normalize_username(username)
        if not self._username_domain:
            raise RuntimeError("El acceso social de Xomacito no está configurado.")
        return f"{normalized}@{self._username_domain}", normalized

    def _account_requires_recovery_email(self, email: str) -> bool:
        normalized = str(email or "").strip().lower()
        if not normalized:
            return True
        return bool(self._username_domain and normalized.endswith(f"@{self._username_domain}"))

    @staticmethod
    def _normalize_email(email: str):
        normalized = str(email or "").strip().lower()
        if len(normalized) > 254 or not re.fullmatch(
            r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+",
            normalized,
        ):
            raise ValueError("Escribe un correo válido.")
        return normalized

    def _store_session(self, data):
        user = dict(data.get("user") or {})
        values = {
            "social_access_token": str(data.get("access_token") or ""),
            "social_refresh_token": str(data.get("refresh_token") or ""),
        }
        if user.get("id"):
            values["social_user_id"] = str(user["id"])
        if user.get("email"):
            values["social_email"] = str(user["email"]).strip().lower()
        self.settings.update(values)

    @staticmethod
    def _token_expiring(access_token: str, *, leeway_seconds: int = 60) -> bool:
        """Indica si un JWT vence pronto sin validar ni exponer su contenido."""
        try:
            encoded_payload = access_token.split(".", 2)[1]
            encoded_payload += "=" * (-len(encoded_payload) % 4)
            payload = json.loads(base64.urlsafe_b64decode(encoded_payload).decode("utf-8"))
            return int(payload.get("exp", 0)) <= int(time.time()) + leeway_seconds
        except (IndexError, ValueError, TypeError, UnicodeDecodeError, binascii.Error):
            # Si cambia el formato del token dejamos que Supabase lo valide y
            # conservamos el reintento 401 como respaldo.
            return False

    def _refresh_session(self, *, failed_access_token: str = ""):
        """Renueva una sola vez y reutiliza una renovación ya hecha por otro hilo."""
        with self._session_lock:
            current_access_token = str(self.settings.get("social_access_token", "")).strip()
            if failed_access_token and current_access_token and current_access_token != failed_access_token:
                return True

            refresh_token = str(self.settings.get("social_refresh_token", "")).strip()
            if not refresh_token:
                return False
            try:
                response = requests.post(
                    f"{self._url}/auth/v1/token?grant_type=refresh_token",
                    headers=self._headers(),
                    json={"refresh_token": refresh_token},
                    timeout=20,
                )
            except requests.RequestException:
                return False
            data = response.json() if response.content else {}
            if response.status_code >= 400 or not data.get("access_token"):
                return False
            self._store_session(data)
            return True

    def _ensure_fresh_session(self) -> bool:
        access_token = self._access_token()
        if not access_token:
            return False
        if self._token_expiring(access_token):
            return self._refresh_session(failed_access_token=access_token)
        return True

    def request_first_run(self):
        if self._state["configured"] and not self._state["authenticated"] and not self.settings.get("social_onboarding_dismissed", False):
            self.onboardingRequested.emit()

    @Slot(str, str, str)
    def signUp(self, username, email, password):
        if not self._state["configured"] or self._state["busy"]:
            return
        self._set_state(busy=True, error="", verificationPending=False)
        self.pool.submit(
            self._signup_worker, str(username), str(email), str(password),
            on_result=self._signup_completed,
            on_error=lambda message, detail: self._auth_failed(message, detail),
        )

    def _signup_worker(self, username, email, password):
        normalized = self._normalize_username(username)
        email = self._normalize_email(email)
        if len(password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        response = requests.post(
            f"{self._url}/auth/v1/signup",
            headers=self._headers(),
            params={"redirect_to": self._recovery_email_redirect_url()},
            json={"email": email, "password": password, "data": {"username": normalized}},
            timeout=20,
        )
        data = response.json() if response.content else {}
        if response.status_code >= 400:
            raise RuntimeError(data.get("msg") or data.get("message") or "No se pudo crear la cuenta.")
        data["xomacito_username"] = normalized
        data["xomacito_email"] = email
        if not data.get("access_token"):
            data["verification_pending"] = True
        return data

    def _signup_completed(self, data):
        if data.get("verification_pending"):
            email = str(data.get("xomacito_email") or "")
            self.settings.set("social_email", email)
            self._set_state(
                busy=False, error="", email=email,
                verificationPending=True,
            )
            self._start_recovery_callback_server()
            self.notificationRequested.emit(
                "info", "Revisa tu correo",
                "Confirma la cuenta desde el mensaje recibido y luego inicia sesión.",
            )
            return
        self._auth_succeeded(data, welcome_title="Cuenta creada")

    @Slot(str, str)
    def signIn(self, username, password):
        if not self._state["configured"] or self._state["busy"]:
            return
        self._set_state(busy=True, error="")
        self.pool.submit(
            self._signin_worker, str(username), str(password),
            on_result=self._auth_succeeded,
            on_error=lambda message, detail: self._auth_failed(message, detail),
        )

    def _signin_worker(self, username, password):
        identifier = str(username or "").strip()
        if "@" in identifier:
            email = self._normalize_email(identifier)
            normalized = ""
        else:
            email, normalized = self._email_for_username(identifier)
        response = requests.post(
            f"{self._url}/auth/v1/token?grant_type=password",
            headers=self._headers(),
            json={"email": email, "password": password},
            timeout=20,
        )
        data = response.json() if response.content else {}
        if response.status_code >= 400:
            raise RuntimeError(data.get("error_description") or data.get("message") or "Correo o contraseña incorrectos.")
        data["xomacito_username"] = normalized
        data["xomacito_email"] = email
        return data

    def _auth_succeeded(self, data, *, welcome_title="Cuenta conectada"):
        user = dict(data.get("user") or {})
        username = str(data.get("xomacito_username") or user.get("user_metadata", {}).get("username") or "")
        email = str(data.get("xomacito_email") or user.get("email") or "").strip().lower()
        self._store_session(data)
        self.settings.update({
            "social_username": username,
            "social_email": email,
            "social_onboarding_dismissed": True,
        })
        self._set_state(
            authenticated=True, username=username, email=email, busy=False, error="",
            verificationPending=False, recoveryLinkSent=False, recoveryEmail="",
            needsRecoveryEmail=self._account_requires_recovery_email(email),
            recoveryEmailUpdatePending=False, emailError="",
        )
        greeting = f"Bienvenido, {username}." if username else "Tu cuenta quedó conectada."
        self.notificationRequested.emit("success", welcome_title, greeting)
        self.claimCreatorGiftIfEligible()
        self.claimAccountRollGifts()
        self.pool.submit(
            self._claim_signup_bonus_worker,
            on_result=self._signup_bonus_completed,
            on_error=lambda message, detail: print(detail or message),
        )
        if self._account_requires_recovery_email(email):
            self.recoveryEmailRequired.emit()
        self.refresh()

    @Slot()
    def claimCreatorGiftIfEligible(self):
        """Entrega regalos nominales una vez y nunca los muestra a otros usuarios."""
        if not self._state.get("authenticated"):
            return
        username = self._normalize_username(str(self._state.get("username") or ""))
        gift = self.CREATOR_GIFTS.get(username)
        if not gift:
            return
        campaign = str(gift["campaign"])
        claimed = set(self.settings.get("creator_gifts_claimed", []) or [])
        if campaign in claimed:
            return
        # Se persiste antes de emitir para que dos refrescos simultáneos no
        # puedan duplicar el premio en el mismo equipo.
        claimed.add(campaign)
        self.settings.set("creator_gifts_claimed", sorted(claimed))
        amount = max(0, int(gift["amount"]))
        if not amount:
            return
        self.signupBonusGranted.emit(amount)
        self.notificationRequested.emit(
            "success", str(gift["title"]), str(gift["message"]),
        )

    @Slot()
    def claimAccountRollGifts(self):
        """Reclama regalos privados ligados por el servidor al ID autenticado."""
        if not self._state.get("authenticated") or self._state.get("busy"):
            return
        self.pool.submit(
            self._claim_account_roll_gifts_worker,
            on_result=self._account_roll_gifts_completed,
            on_error=lambda message, detail: print(detail or message),
        )

    def _authenticated_user_request(self, method, *, json_payload=None, redirect_to=""):
        if not self._ensure_fresh_session():
            raise RuntimeError("Tu sesión venció. Vuelve a iniciar sesión.")
        access_token = self._access_token()
        request_options = {
            "headers": self._headers(authenticated=True, access_token=access_token),
            "json": json_payload,
            "timeout": 20,
        }
        if redirect_to:
            request_options["params"] = {"redirect_to": redirect_to}
        response = requests.request(
            method,
            f"{self._url}/auth/v1/user",
            **request_options,
        )
        if response.status_code == 401 and self._refresh_session(failed_access_token=access_token):
            request_options["headers"] = self._headers(authenticated=True)
            response = requests.request(
                method,
                f"{self._url}/auth/v1/user",
                **request_options,
            )
        payload = response.json() if response.content else {}
        if response.status_code >= 400:
            raise RuntimeError(
                payload.get("msg") or payload.get("message")
                or "No se pudo actualizar el correo de recuperación."
            )
        return dict(payload.get("user") or payload)

    @Slot()
    def checkRecoveryEmail(self):
        if not self._state["configured"] or not self._state["authenticated"] or self._state["emailBusy"]:
            return
        self._set_state(emailBusy=True, emailError="")
        self.pool.submit(
            self._account_email_worker,
            on_result=self._account_email_checked,
            on_error=lambda message, detail: self._email_update_failed(message, detail),
        )

    def _account_email_worker(self):
        return self._authenticated_user_request("GET")

    def _account_email_checked(self, user):
        current_email = str(dict(user or {}).get("email") or "").strip().lower()
        pending_email = str(dict(user or {}).get("new_email") or "").strip().lower()
        needs_email = self._account_requires_recovery_email(current_email)
        self.settings.set("social_email", current_email)
        self._set_state(
            email=current_email, emailBusy=False, emailError="",
            needsRecoveryEmail=needs_email,
            recoveryEmailUpdatePending=bool(needs_email and pending_email),
            recoveryEmail=pending_email,
        )
        if needs_email:
            if pending_email:
                self._start_recovery_callback_server()
            self.recoveryEmailRequired.emit()
            return
        self._stop_recovery_callback_server()
        self.pool.submit(
            self._claim_signup_bonus_worker,
            on_result=self._signup_bonus_completed,
            on_error=lambda message, detail: print(detail or message),
        )

    @Slot(str)
    def updateRecoveryEmail(self, email):
        if not self._state["authenticated"] or self._state["emailBusy"]:
            return
        try:
            normalized = self._normalize_email(email)
        except ValueError as error:
            self._email_update_failed(str(error), "")
            return
        if self._account_requires_recovery_email(normalized):
            self._email_update_failed("Usa un correo personal al que puedas acceder.", "")
            return
        self._set_state(emailBusy=True, emailError="", recoveryEmail=normalized)
        self.pool.submit(
            self._update_recovery_email_worker, normalized,
            on_result=self._recovery_email_update_requested,
            on_error=lambda message, detail: self._email_update_failed(message, detail),
        )

    def _update_recovery_email_worker(self, email):
        user = self._authenticated_user_request(
            "PUT",
            json_payload={"email": email},
            redirect_to=self._recovery_email_redirect_url(),
        )
        user["requested_email"] = email
        return user

    def _recovery_email_update_requested(self, user):
        payload = dict(user or {})
        requested_email = str(payload.get("requested_email") or "").strip().lower()
        current_email = str(payload.get("email") or "").strip().lower()
        pending_email = str(payload.get("new_email") or "").strip().lower()
        completed = current_email == requested_email and not self._account_requires_recovery_email(current_email)
        if completed:
            self._stop_recovery_callback_server()
            self.settings.set("social_email", current_email)
            self._set_state(
                email=current_email, emailBusy=False, emailError="",
                needsRecoveryEmail=False, recoveryEmailUpdatePending=False,
                recoveryEmail="",
            )
            self.pool.submit(
                self._claim_signup_bonus_worker,
                on_result=self._signup_bonus_completed,
                on_error=lambda message, detail: print(detail or message),
            )
            return
        self._set_state(
            emailBusy=False, emailError="", needsRecoveryEmail=True,
            recoveryEmailUpdatePending=True,
            recoveryEmail=pending_email or requested_email,
        )
        self._start_recovery_callback_server()
        self.notificationRequested.emit(
            "info", "Confirma tu correo",
            "Abre el mensaje de Supabase. Xomacito comprobará el cambio al volver del navegador.",
        )

    def _email_update_failed(self, message, detail):
        if detail:
            print(detail)
        self._set_state(emailBusy=False, emailError=str(message))
        self.notificationRequested.emit("error", "No se pudo guardar el correo", str(message))

    @Slot(str)
    def requestPasswordReset(self, email):
        if not self._state["configured"] or self._state["busy"]:
            return
        try:
            normalized = self._normalize_email(email)
        except ValueError as error:
            self._auth_failed(str(error), "")
            return
        if not self._start_recovery_callback_server():
            self._auth_failed(
                "No se pudo abrir la página local de recuperación. Libera el puerto 3000 e inténtalo otra vez.",
                "",
            )
            return
        self._set_state(busy=True, error="", recoveryLinkSent=False)
        self.pool.submit(
            self._password_reset_request_worker, normalized,
            on_result=self._password_reset_requested,
            on_error=self._password_reset_request_failed,
        )

    def _password_reset_request_worker(self, email):
        response = requests.post(
            f"{self._url}/auth/v1/recover",
            headers=self._headers(),
            params={"redirect_to": self._recovery_email_redirect_url()},
            json={"email": email},
            timeout=20,
        )
        if response.status_code >= 400:
            data = response.json() if response.content else {}
            message = data.get("msg") or data.get("message") or "No se pudo enviar el enlace."
            raise RuntimeError(message)
        return email

    def _password_reset_requested(self, email):
        self._set_state(
            busy=False, error="", recoveryLinkSent=True, recoveryEmail=str(email),
        )
        self.notificationRequested.emit(
            "info", "Enlace enviado",
            "Abre el mensaje de Supabase mientras Xomacito permanece abierto.",
        )

    @Slot()
    def cancelPasswordReset(self):
        self._stop_recovery_callback_server()
        self._set_state(
            busy=False, error="", recoveryLinkSent=False, recoveryEmail="",
        )

    def _password_reset_request_failed(self, message, detail):
        self._stop_recovery_callback_server()
        self._auth_failed(message, detail)

    def _password_reset_link_callback(self, access_token, refresh_token, password):
        data = self._password_reset_link_worker(access_token, refresh_token, password)
        self.passwordRecoveryCompleted.emit(data)

    def _password_reset_link_worker(self, access_token, refresh_token, password):
        update = requests.put(
            f"{self._url}/auth/v1/user",
            headers=self._headers(authenticated=True, access_token=str(access_token)),
            json={"password": str(password)},
            timeout=20,
        )
        payload = update.json() if update.content else {}
        if update.status_code >= 400:
            message = payload.get("msg") or payload.get("message")
            raise RuntimeError(message or "El enlace venció. Solicita uno nuevo desde Xomacito.")
        user = dict(payload or {})
        return {
            "access_token": str(access_token),
            "refresh_token": str(refresh_token),
            "user": user,
            "xomacito_email": str(user.get("email") or "").strip().lower(),
        }

    @Slot(str, str, str)
    def confirmPasswordReset(self, email, code, new_password):
        if not self._state["configured"] or self._state["busy"]:
            return
        try:
            normalized = self._normalize_email(email)
        except ValueError as error:
            self._auth_failed(str(error), "")
            return
        token = re.sub(r"\s+", "", str(code or ""))
        if not re.fullmatch(r"\d{6}", token):
            self._auth_failed("El código debe tener 6 dígitos.", "")
            return
        if len(str(new_password)) < 8:
            self._auth_failed("La nueva contraseña debe tener al menos 8 caracteres.", "")
            return
        self._set_state(busy=True, error="")
        self.pool.submit(
            self._password_reset_confirm_worker,
            normalized, token, str(new_password),
            on_result=self._password_reset_succeeded,
            on_error=lambda message, detail: self._auth_failed(message, detail),
        )

    def _password_reset_confirm_worker(self, email, token, new_password):
        response = requests.post(
            f"{self._url}/auth/v1/verify",
            headers=self._headers(),
            json={"email": email, "token": token, "type": "recovery"},
            timeout=20,
        )
        data = response.json() if response.content else {}
        if response.status_code >= 400 or not data.get("access_token"):
            raise RuntimeError("El código es incorrecto o venció. Solicita uno nuevo.")
        update = requests.put(
            f"{self._url}/auth/v1/user",
            headers=self._headers(authenticated=True, access_token=str(data["access_token"])),
            json={"password": new_password},
            timeout=20,
        )
        if update.status_code >= 400:
            payload = update.json() if update.content else {}
            raise RuntimeError(payload.get("msg") or payload.get("message") or "No se pudo cambiar la contraseña.")
        data["xomacito_email"] = email
        return data

    def _password_reset_succeeded(self, data):
        self._stop_recovery_callback_server()
        self._auth_succeeded(data, welcome_title="Contraseña cambiada")

    def _claim_signup_bonus_worker(self):
        if not self._ensure_fresh_session():
            return 0
        access_token = self._access_token()
        response = requests.post(
            f"{self._url}/rest/v1/rpc/claim_email_roll_reward",
            headers=self._headers(authenticated=True, access_token=access_token),
            json={},
            timeout=12,
        )
        if response.status_code == 401 and self._refresh_session(failed_access_token=access_token):
            response = requests.post(
                f"{self._url}/rest/v1/rpc/claim_email_roll_reward",
                headers=self._headers(authenticated=True), json={}, timeout=12,
            )
        if response.status_code >= 400:
            raise RuntimeError(f"No se pudo validar la recompensa ({response.status_code}).")
        payload = response.json() if response.content else 0
        return max(0, int(payload or 0))

    def _claim_account_roll_gifts_worker(self):
        if not self._ensure_fresh_session():
            return 0
        access_token = self._access_token()
        response = requests.post(
            f"{self._url}/rest/v1/rpc/claim_account_roll_gifts",
            headers=self._headers(authenticated=True, access_token=access_token),
            json={},
            timeout=12,
        )
        if response.status_code == 401 and self._refresh_session(failed_access_token=access_token):
            response = requests.post(
                f"{self._url}/rest/v1/rpc/claim_account_roll_gifts",
                headers=self._headers(authenticated=True), json={}, timeout=12,
            )
        if response.status_code >= 400:
            raise RuntimeError(f"No se pudo validar el regalo de cuenta ({response.status_code}).")
        payload = response.json() if response.content else 0
        return max(0, int(payload or 0))

    def _account_roll_gifts_completed(self, amount):
        amount = max(0, int(amount or 0))
        if not amount:
            return
        self.signupBonusGranted.emit(amount)
        self.notificationRequested.emit(
            "success", f"¡Tienes {amount} tiradas de regalo!",
            "Strike dejó este premio para tu cuenta. Ya está disponible y sólo puede reclamarse una vez.",
        )

    def _signup_bonus_completed(self, amount):
        amount = max(0, int(amount or 0))
        if not amount:
            return
        self.signupBonusGranted.emit(amount)
        self.notificationRequested.emit(
            "success", f"¡{amount} tiradas de regalo!",
            "Tu correo de recuperación quedó conectado y el premio ya está en tu colección gatuna.",
        )

    def _auth_failed(self, message, detail):
        if detail:
            print(detail)
        self._set_state(busy=False, error=str(message))
        self.notificationRequested.emit("error", "No se pudo conectar", str(message))

    @Slot()
    def signOut(self):
        self._stop_recovery_callback_server()
        self.settings.update({
            "social_access_token": "", "social_refresh_token": "",
            "social_user_id": "", "social_username": "", "social_email": "",
        })
        self._set_state(
            authenticated=False, username="", email="", leaderboard=[], error="",
            emailBusy=False, emailError="", needsRecoveryEmail=False,
            recoveryEmailUpdatePending=False,
            verificationPending=False, recoveryLinkSent=False, recoveryEmail="",
            currentRank=0, currentDownloads=0, currentCats=0,
            currentStreak=0, bestStreak=0, communityDownloads=0,
            communityCats=0, activePlayers=0, currentEquippedCatId="",
        )

    def shutdown(self):
        self._stop_recovery_callback_server()

    @Slot()
    def dismissOnboarding(self):
        self.settings.set("social_onboarding_dismissed", True)

    @Slot()
    def refresh(self):
        if not self._state["configured"] or self._state["busy"]:
            return
        self._set_state(busy=True, error="")
        self.pool.submit(
            self._leaderboard_worker,
            on_result=lambda result: self._set_state(busy=False, **result),
            on_error=lambda message, detail: self._auth_failed(message, detail),
        )

    def _leaderboard_worker(self):
        if self._state["authenticated"]:
            # El perfil remoto puede haber sido creado después de desbloquear
            # gatos. Se sincroniza antes de leer el ranking para que el usuario
            # vea su colección correcta desde la primera visita.
            if self._local_cat_count is not None:
                self._rpc("set_cat_count", {"value": self._local_cat_count})
                self._rpc("set_equipped_cat", {"value": self._local_equipped_cat_id})
            self._rpc("record_daily_activity", {})
        response = requests.post(
            f"{self._url}/rest/v1/rpc/get_xomacito_leaderboard",
            headers=self._headers(), json={}, timeout=20,
        )
        if response.status_code in {404, 405}:
            response = requests.get(
                f"{self._url}/rest/v1/profiles",
                headers=self._headers(),
                params={
                    "select": "username,downloads_count,cats_count",
                    "order": "downloads_count.desc,cats_count.desc",
                    "limit": "100",
                },
                timeout=20,
            )
        if response.status_code >= 400:
            raise RuntimeError("No se pudo cargar el scoreboard.")
        payload = response.json()
        rows = [
            {
                "rank": index + 1,
                "username": str(row.get("username") or "Jugador"),
                "downloads": int(row.get("downloads_count") or 0),
                "cats": int(row.get("cats_count") or 0),
                "streak": int(row.get("streak_days") or 0),
                "bestStreak": int(row.get("best_streak") or 0),
                "activeToday": bool(row.get("active_today", False)),
                "equippedCatId": str(row.get("equipped_cat_id") or ""),
            }
            for index, row in enumerate(payload if isinstance(payload, list) else [])
        ]
        username = str(self._state.get("username") or "")
        current = next((row for row in rows if row["username"] == username), {})
        return {
            "leaderboard": rows,
            "currentRank": int(current.get("rank") or 0),
            "currentDownloads": int(current.get("downloads") or 0),
            "currentCats": int(current.get("cats") or 0),
            "currentStreak": int(current.get("streak") or 0),
            "bestStreak": int(current.get("bestStreak") or 0),
            "communityDownloads": sum(row["downloads"] for row in rows),
            "communityCats": sum(row["cats"] for row in rows),
            "activePlayers": sum(1 for row in rows if row["activeToday"]),
            "currentEquippedCatId": str(current.get("equippedCatId") or self._local_equipped_cat_id),
        }

    def _rpc(self, name, payload):
        if not self._state["configured"] or not self._state["authenticated"]:
            return
        try:
            if not self._ensure_fresh_session():
                return
            access_token = self._access_token()
            response = requests.post(
                f"{self._url}/rest/v1/rpc/{name}",
                headers=self._headers(authenticated=True, access_token=access_token),
                json=payload,
                timeout=12,
            )
            if response.status_code == 401 and self._refresh_session(failed_access_token=access_token):
                response = requests.post(
                    f"{self._url}/rest/v1/rpc/{name}",
                    headers=self._headers(authenticated=True), json=payload, timeout=12,
                )
            if response.status_code >= 400:
                print(f"Supabase RPC {name}: {response.status_code} {response.text[:300]}")
        except requests.RequestException as error:
            print(f"Supabase RPC {name}: {error}")

    @staticmethod
    def _merge_collection_states(local_state, remote_state):
        """Une colecciones y conserva el saldo de tiradas de la revisión más nueva."""
        local = dict(local_state or {})
        remote = dict(remote_state or {})

        def strings(field, limit, length=128):
            values = []
            seen = set()
            for source in (remote.get(field, []), local.get(field, [])):
                if not isinstance(source, list):
                    continue
                for value in source:
                    value = str(value or "")[:length]
                    if not value or value in seen:
                        continue
                    seen.add(value)
                    values.append(value)
                    if len(values) >= limit:
                        return sorted(values)
            return sorted(values)

        def normalized_number(source, field, maximum=10_000_000):
            try:
                return max(0, min(maximum, int(source.get(field, 0) or 0)))
            except (TypeError, ValueError):
                return 0

        def number(field, maximum=10_000_000):
            values = []
            for source in (local, remote):
                values.append(normalized_number(source, field, maximum))
            return max(values)

        def balance_revision(source):
            if "rollBalanceRevision" in source:
                return normalized_number(source, "rollBalanceRevision")
            return normalized_number(source, "totalDownloads") + normalized_number(
                source, "totalRolls",
            )

        duplicates = {}
        for source in (remote.get("duplicates", {}), local.get("duplicates", {})):
            if not isinstance(source, dict):
                continue
            for cat_id, amount in list(source.items())[:2000]:
                cat_id = str(cat_id or "")[:128]
                if not cat_id:
                    continue
                try:
                    amount = max(0, min(1_000_000, int(amount or 0)))
                except (TypeError, ValueError):
                    continue
                duplicates[cat_id] = max(duplicates.get(cat_id, 0), amount)

        local_unlocked = local.get("unlockedIds", []) if isinstance(local.get("unlockedIds"), list) else []
        remote_unlocked = remote.get("unlockedIds", []) if isinstance(remote.get("unlockedIds"), list) else []
        try:
            local_rolls = max(0, int(local.get("totalRolls", 0) or 0))
        except (TypeError, ValueError):
            local_rolls = 0
        local_is_fresh = len(local_unlocked) <= 1 and local_rolls == 0
        local_balance_rank = (
            balance_revision(local),
            normalized_number(local, "totalRolls"),
            normalized_number(local, "totalDownloads"),
        )
        remote_balance_rank = (
            balance_revision(remote),
            normalized_number(remote, "totalRolls"),
            normalized_number(remote, "totalDownloads"),
        )
        balance_source = remote if (
            remote_balance_rank > local_balance_rank
            or (local_is_fresh and len(remote_unlocked) > 1)
        ) else local
        equipped = str(
            (remote.get("equippedId") if local_is_fresh else local.get("equippedId"))
            or remote.get("equippedId") or local.get("equippedId") or ""
        )[:128]

        return {
            "schema": 5,
            "downloadProgress": normalized_number(balance_source, "downloadProgress", 9),
            "earnedRolls": normalized_number(balance_source, "earnedRolls"),
            "totalDownloads": number("totalDownloads"),
            "totalRolls": number("totalRolls"),
            "rollBalanceRevision": balance_revision(balance_source),
            "lastDailyRoll": max(
                str(local.get("lastDailyRoll") or "")[:10],
                str(remote.get("lastDailyRoll") or "")[:10],
            ),
            "unlockedIds": strings("unlockedIds", 2000),
            "historicalUnlockedCount": number("historicalUnlockedCount", 2000),
            "equippedId": equipped,
            "duplicates": dict(sorted(duplicates.items())),
            "rewardedSourceHashes": strings("rewardedSourceHashes", 20_000, 128),
            "claimedPromotions": strings("claimedPromotions", 1000, 128),
        }

    def _collection_sync_worker(self, local_state):
        if not self._ensure_fresh_session():
            raise RuntimeError("La sesión venció. Vuelve a iniciar sesión para sincronizar tus gatitos.")
        user_id = str(self.settings.get("social_user_id", "") or "").strip()
        if not user_id:
            raise RuntimeError("La cuenta no tiene un identificador válido.")

        access_token = self._access_token()
        response = requests.get(
            f"{self._url}/rest/v1/cat_collection_states",
            headers=self._headers(authenticated=True, access_token=access_token),
            params={"user_id": f"eq.{user_id}", "select": "state", "limit": "1"},
            timeout=20,
        )
        if response.status_code == 401 and self._refresh_session(failed_access_token=access_token):
            response = requests.get(
                f"{self._url}/rest/v1/cat_collection_states",
                headers=self._headers(authenticated=True),
                params={"user_id": f"eq.{user_id}", "select": "state", "limit": "1"},
                timeout=20,
            )
        if response.status_code >= 400:
            raise RuntimeError("No se pudo descargar tu colección gatuna.")
        rows = response.json() if response.content else []
        remote_state = rows[0].get("state", {}) if isinstance(rows, list) and rows else {}
        merged = self._merge_collection_states(local_state, remote_state)

        # Antes de existir cat_collection_states, el scoreboard ya conservaba
        # un máximo histórico. Se usa sólo para reconstruir IDs faltantes de la
        # misma cuenta; el controlador nunca inventa recompensas exclusivas.
        try:
            profile = requests.get(
                f"{self._url}/rest/v1/profiles",
                headers=self._headers(authenticated=True),
                params={"id": f"eq.{user_id}", "select": "cats_count", "limit": "1"},
                timeout=20,
            )
            profile_rows = profile.json() if profile.status_code < 400 and profile.content else []
            historical_count = (
                profile_rows[0].get("cats_count", 0)
                if isinstance(profile_rows, list) and profile_rows else 0
            )
        except (requests.RequestException, ValueError, TypeError):
            historical_count = 0
        merged["historicalUnlockedCount"] = max(
            int(merged.get("historicalUnlockedCount", 0) or 0),
            max(0, min(2000, int(historical_count or 0))),
            len(merged.get("unlockedIds", [])),
        )

        headers = self._headers(authenticated=True)
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
        saved = requests.post(
            f"{self._url}/rest/v1/cat_collection_states",
            headers=headers,
            params={"on_conflict": "user_id"},
            json={
                "user_id": user_id,
                "state": merged,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            timeout=20,
        )
        if saved.status_code >= 400:
            raise RuntimeError("No se pudo guardar tu colección gatuna.")
        return merged

    def _start_collection_sync(self):
        if self._collection_sync_inflight or not self._state.get("authenticated"):
            return
        self._collection_sync_inflight = True
        self.pool.submit(
            self._collection_sync_worker,
            dict(self._local_collection_state),
            on_result=self._collection_sync_completed,
            on_error=self._collection_sync_failed,
        )

    def _collection_sync_completed(self, state):
        self._collection_sync_inflight = False
        self.collectionStateReceived.emit(dict(state or {}))
        if self._collection_sync_queued:
            self._collection_sync_queued = False
            self._start_collection_sync()

    def _collection_sync_failed(self, message, detail):
        self._collection_sync_inflight = False
        self._collection_sync_queued = False
        print(detail or message)
        self.notificationRequested.emit("warning", "Sincronización pendiente", str(message))

    @Slot("QVariantMap")
    def syncCollection(self, state):
        self._local_collection_state = dict(state or {})
        if not self._state.get("authenticated"):
            return
        if self._collection_sync_inflight:
            self._collection_sync_queued = True
            return
        self._start_collection_sync()

    @Slot(int)
    def recordDownload(self, completed_items=1):
        if self._state["authenticated"]:
            self.pool.submit(self._rpc, "increment_downloads", {"delta": max(1, int(completed_items or 1))})

    @Slot(int)
    def syncCatCount(self, count):
        self._local_cat_count = max(0, int(count or 0))
        if self._state["authenticated"]:
            self.pool.submit(self._rpc, "set_cat_count", {"value": self._local_cat_count})

    @Slot(int, str)
    def syncProfile(self, count, equipped_cat_id):
        normalized_count = max(0, int(count or 0))
        normalized_cat_id = str(equipped_cat_id or "")[:80]
        if normalized_count == self._local_cat_count and normalized_cat_id == self._local_equipped_cat_id:
            return
        self._local_cat_count = normalized_count
        self._local_equipped_cat_id = normalized_cat_id
        if self._state["authenticated"]:
            self.pool.submit(self._rpc, "set_cat_count", {"value": normalized_count})
            self.pool.submit(self._rpc, "set_equipped_cat", {"value": normalized_cat_id})
