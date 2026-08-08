from __future__ import annotations

import json
import os
import re
from pathlib import Path

import requests
from PySide6.QtCore import QObject, Property, Signal, Slot


class SocialController(QObject):
    """Cliente ligero de Supabase Auth/REST sin guardar contraseñas localmente."""

    stateChanged = Signal()
    notificationRequested = Signal(str, str, str)
    onboardingRequested = Signal()

    def __init__(self, project_root: str | Path, settings, pool, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.settings = settings
        self.pool = pool
        self._url, self._anon_key, self._username_domain = self._load_config()
        self._state = {
            "configured": bool(self._url and self._anon_key),
            "authenticated": bool(settings.get("social_access_token", "")),
            "username": str(settings.get("social_username", "")),
            "busy": False,
            "error": "",
            "leaderboard": [],
            "currentRank": 0,
            "currentDownloads": 0,
            "currentCats": 0,
            "currentStreak": 0,
            "bestStreak": 0,
            "communityDownloads": 0,
            "communityCats": 0,
            "activePlayers": 0,
        }

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

    def _headers(self, *, authenticated=False):
        headers = {"apikey": self._anon_key, "Content-Type": "application/json"}
        token = str(self.settings.get("social_access_token", "")) if authenticated else self._anon_key
        headers["Authorization"] = f"Bearer {token}"
        return headers

    def _email_for_username(self, username: str):
        normalized = re.sub(r"[^a-z0-9_-]+", "-", username.strip().lower()).strip("-_")
        normalized = re.sub(r"[-_]{2,}", "-", normalized)
        if len(normalized) < 3:
            raise ValueError("La ID debe tener al menos 3 letras o números.")
        if len(normalized) > 32:
            raise ValueError("La ID puede tener como máximo 32 caracteres.")
        if not self._username_domain:
            raise RuntimeError("El acceso social de Xomacito no está configurado.")
        return f"{normalized}@{self._username_domain}", normalized

    def _store_session(self, data):
        user = dict(data.get("user") or {})
        values = {
            "social_access_token": str(data.get("access_token") or ""),
            "social_refresh_token": str(data.get("refresh_token") or ""),
        }
        if user.get("id"):
            values["social_user_id"] = str(user["id"])
        self.settings.update(values)

    def _refresh_session(self):
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

    def request_first_run(self):
        if self._state["configured"] and not self._state["authenticated"] and not self.settings.get("social_onboarding_dismissed", False):
            self.onboardingRequested.emit()

    @Slot(str, str)
    def signUp(self, username, password):
        if not self._state["configured"] or self._state["busy"]:
            return
        self._set_state(busy=True, error="")
        self.pool.submit(
            self._signup_worker, str(username), str(password),
            on_result=self._auth_succeeded,
            on_error=lambda message, detail: self._auth_failed(message, detail),
        )

    def _signup_worker(self, username, password):
        email, normalized = self._email_for_username(username)
        if len(password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        response = requests.post(
            f"{self._url}/auth/v1/signup",
            headers=self._headers(),
            json={"email": email, "password": password, "data": {"username": normalized}},
            timeout=20,
        )
        data = response.json() if response.content else {}
        if response.status_code >= 400:
            raise RuntimeError(data.get("msg") or data.get("message") or "No se pudo crear la ID.")
        if not data.get("access_token"):
            raise RuntimeError("La cuenta fue creada, pero Supabase exige confirmar el correo. Desactiva esa confirmación para las IDs de Xomacito.")
        data["xomacito_username"] = normalized
        return data

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
        email, normalized = self._email_for_username(username)
        response = requests.post(
            f"{self._url}/auth/v1/token?grant_type=password",
            headers=self._headers(),
            json={"email": email, "password": password},
            timeout=20,
        )
        data = response.json() if response.content else {}
        if response.status_code >= 400:
            raise RuntimeError(data.get("error_description") or data.get("message") or "ID o contraseña incorrectos.")
        data["xomacito_username"] = normalized
        return data

    def _auth_succeeded(self, data):
        user = dict(data.get("user") or {})
        username = str(data.get("xomacito_username") or user.get("user_metadata", {}).get("username") or "")
        self._store_session(data)
        self.settings.update({
            "social_username": username,
            "social_onboarding_dismissed": True,
        })
        self._set_state(authenticated=True, username=username, busy=False, error="")
        self.notificationRequested.emit("success", "ID conectada", f"Bienvenido, {username}.")
        self.refresh()

    def _auth_failed(self, message, detail):
        if detail:
            print(detail)
        self._set_state(busy=False, error=str(message))
        self.notificationRequested.emit("error", "No se pudo conectar", str(message))

    @Slot()
    def signOut(self):
        self.settings.update({
            "social_access_token": "", "social_refresh_token": "",
            "social_user_id": "", "social_username": "",
        })
        self._set_state(
            authenticated=False, username="", leaderboard=[], error="",
            currentRank=0, currentDownloads=0, currentCats=0,
            currentStreak=0, bestStreak=0, communityDownloads=0,
            communityCats=0, activePlayers=0,
        )

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
        }

    def _rpc(self, name, payload):
        if not self._state["configured"] or not self._state["authenticated"]:
            return
        try:
            response = requests.post(
                f"{self._url}/rest/v1/rpc/{name}",
                headers=self._headers(authenticated=True), json=payload, timeout=12,
            )
            if response.status_code == 401 and self._refresh_session():
                response = requests.post(
                    f"{self._url}/rest/v1/rpc/{name}",
                    headers=self._headers(authenticated=True), json=payload, timeout=12,
                )
            if response.status_code >= 400:
                print(f"Supabase RPC {name}: {response.status_code} {response.text[:300]}")
        except requests.RequestException as error:
            print(f"Supabase RPC {name}: {error}")

    @Slot(int)
    def recordDownload(self, completed_items=1):
        if self._state["authenticated"]:
            self.pool.submit(self._rpc, "increment_downloads", {"delta": max(1, int(completed_items or 1))})

    @Slot(int)
    def syncCatCount(self, count):
        if self._state["authenticated"]:
            self.pool.submit(self._rpc, "set_cat_count", {"value": max(0, int(count or 0))})
