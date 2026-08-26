from __future__ import annotations

import random
import hashlib
from datetime import date
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QCoreApplication, QObject, Property, QTimer, QUrl, Signal, Slot

from src.core.cat_gacha import ROLL_WEIGHTS, CatDefinition, load_cat_catalog, starter_cat

from .list_model import ObjectListModel
from .settings_store import SettingsStore


class CatGachaController(QObject):
    stateChanged = Signal()
    revealRequested = Signal("QVariantMap")
    equippedRequested = Signal("QVariantMap")
    notificationRequested = Signal(str, str, str)

    ROLES = [
        "catId", "name", "source", "rarity", "rarityColor", "stars",
        "animationStyle", "unlocked", "equipped", "duplicateCount",
        "effectLevel", "effectName",
    ]

    EFFECT_NAMES = ("Sin aura", "Destello", "Resplandor", "Aurora", "Cósmica", "Xoma")

    def __init__(
        self,
        project_root: str | Path,
        settings: SettingsStore,
        parent=None,
        *,
        rng=None,
        today_provider: Callable[[], date] = date.today,
    ):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.settings = settings
        self.catalog = load_cat_catalog(self.project_root)
        self._by_id = {cat.id: cat for cat in self.catalog}
        self._rng = rng or random.SystemRandom()
        self._today = today_provider
        self.collection = ObjectListModel(self.ROLES, self)

        saved = settings.get("cat_gacha", {})
        if not isinstance(saved, dict):
            saved = {}
        starter = starter_cat(self.catalog)
        unlocked = {
            str(cat_id) for cat_id in saved.get("unlockedIds", [])
            if str(cat_id) in self._by_id
        }
        if not unlocked:
            unlocked.add(starter.id)
        equipped = str(saved.get("equippedId") or starter.id)
        if equipped not in unlocked or equipped not in self._by_id:
            equipped = starter.id

        duplicates = saved.get("duplicates", {})
        self._duplicates = {}
        if isinstance(duplicates, dict):
            for cat_id, amount in duplicates.items():
                if str(cat_id) not in self._by_id:
                    continue
                try:
                    self._duplicates[str(cat_id)] = max(0, int(amount))
                except (TypeError, ValueError):
                    continue
        self._unlocked = unlocked
        self._equipped_id = equipped
        self._download_progress = max(0, int(saved.get("downloadProgress", 0))) % 10
        self._earned_rolls = max(0, int(saved.get("earnedRolls", 0)))
        self._total_downloads = max(0, int(saved.get("totalDownloads", 0)))
        self._total_rolls = max(0, int(saved.get("totalRolls", 0)))
        self._last_daily_roll = str(saved.get("lastDailyRoll", ""))
        claimed_promotions = saved.get("claimedPromotions", [])
        self._claimed_promotions = {
            str(value) for value in claimed_promotions if isinstance(value, str) and value
        } if isinstance(claimed_promotions, list) else set()
        hashes = saved.get("rewardedSourceHashes", [])
        self._rewarded_source_hashes = {
            str(value) for value in hashes if isinstance(value, str) and value
        } if isinstance(hashes, list) else set()
        self._known_day = self._today().isoformat()
        self._state: dict = {}
        self._daily_timer = QTimer(self)
        self._daily_timer.setInterval(60_000)
        self._daily_timer.timeout.connect(self._refresh_day)
        if QCoreApplication.instance() is not None:
            self._daily_timer.start()
        self._refresh()
        self._persist()

    @Property("QVariantMap", notify=stateChanged)
    def state(self):
        return self._state

    @Property(QObject, constant=True)
    def model(self):
        return self.collection

    def _url(self, cat: CatDefinition) -> str:
        return QUrl.fromLocalFile(str(cat.avatar_path)).toString()

    @staticmethod
    def _animation_style(cat: CatDefinition) -> str:
        if cat.animation_style != "standard":
            return cat.animation_style
        return "celestial" if cat.rarity >= 6 else "standard"

    def _result(self, cat: CatDefinition, **extra) -> dict:
        duplicate_count = self._duplicates.get(cat.id, 0)
        effect_level = min(5, duplicate_count)
        return {
            "catId": cat.id,
            "name": cat.name,
            "source": self._url(cat),
            "rarity": cat.rarity,
            "rarityColor": cat.rarity_color,
            "stars": "★" * cat.rarity,
            "animationStyle": self._animation_style(cat),
            "duplicateCount": duplicate_count,
            "effectLevel": effect_level,
            "effectName": self.EFFECT_NAMES[effect_level],
            **extra,
        }

    def _daily_available(self) -> bool:
        return self._last_daily_roll != self._today().isoformat()

    @Slot()
    def _refresh_day(self):
        current_day = self._today().isoformat()
        if current_day != self._known_day:
            self._known_day = current_day
            self._refresh()

    def _refresh(self):
        equipped = self._by_id[self._equipped_id]
        daily_available = self._daily_available()
        visible_catalog = [
            cat for cat in self.catalog
            if not cat.exclusive or cat.id in self._unlocked
        ]
        completion_catalog = [cat for cat in self.catalog if not cat.exclusive]
        completion_unlocked = sum(cat.id in self._unlocked for cat in completion_catalog)
        self._state = {
            "downloadProgress": self._download_progress,
            "downloadProgressRatio": self._download_progress / 10.0,
            "downloadsUntilRoll": 10 - self._download_progress,
            "earnedRolls": self._earned_rolls,
            "totalDownloads": self._total_downloads,
            "totalRolls": self._total_rolls,
            "dailyAvailable": daily_available,
            "canRoll": daily_available or self._earned_rolls > 0,
            "unlockedCount": sum(cat.id in self._unlocked for cat in visible_catalog),
            "isPlatinum": completion_unlocked == len(completion_catalog),
            "themeUnlockCount": sum(
                1 for cat_id in self._unlocked
                if self._by_id[cat_id].rarity >= 5
            ),
            "totalCount": len(visible_catalog),
            "equippedId": equipped.id,
            "equippedName": equipped.name,
            "equippedSource": self._url(equipped),
            "equippedRarity": equipped.rarity,
            "equippedColor": equipped.rarity_color,
            "equippedStars": "★" * equipped.rarity,
            "equippedAnimationStyle": self._animation_style(equipped),
            "equippedEffectLevel": min(5, self._duplicates.get(equipped.id, 0)),
            "equippedEffectName": self.EFFECT_NAMES[
                min(5, self._duplicates.get(equipped.id, 0))
            ],
            "rollButtonText": (
                "Tirada diaria gratis"
                if daily_available
                else f"Usar tirada ({self._earned_rolls})"
                if self._earned_rolls
                else f"Faltan {10 - self._download_progress} descargas"
            ),
        }
        items = []
        for cat in visible_catalog:
            items.append(
                {
                    "catId": cat.id,
                    "name": cat.name,
                    "source": self._url(cat),
                    "rarity": cat.rarity,
                    "rarityColor": cat.rarity_color,
                    "stars": "★" * cat.rarity,
                    "animationStyle": self._animation_style(cat),
                    "unlocked": cat.id in self._unlocked,
                    "equipped": cat.id == self._equipped_id,
                    "duplicateCount": self._duplicates.get(cat.id, 0),
                    "effectLevel": min(5, self._duplicates.get(cat.id, 0)),
                    "effectName": self.EFFECT_NAMES[
                        min(5, self._duplicates.get(cat.id, 0))
                    ],
                }
            )
        self.collection.replace(items)
        self.stateChanged.emit()

    def _persist(self):
        self.settings.set(
            "cat_gacha",
            self.sync_snapshot(),
        )

    def sync_snapshot(self) -> dict:
        """Estado portable de la colección para restaurarlo en otra PC."""
        return {
            "schema": 3,
            "downloadProgress": self._download_progress,
            "earnedRolls": self._earned_rolls,
            "totalDownloads": self._total_downloads,
            "totalRolls": self._total_rolls,
            "lastDailyRoll": self._last_daily_roll,
            "unlockedIds": sorted(self._unlocked),
            "equippedId": self._equipped_id,
            "duplicates": dict(sorted(self._duplicates.items())),
            "rewardedSourceHashes": sorted(self._rewarded_source_hashes),
            "claimedPromotions": sorted(self._claimed_promotions),
        }

    @Slot("QVariantMap")
    def mergeRemoteState(self, remote_state):
        """Une el progreso remoto sin borrar premios obtenidos en este equipo."""
        remote = dict(remote_state or {})
        before = self.sync_snapshot()

        remote_unlocked = {
            str(cat_id) for cat_id in remote.get("unlockedIds", [])
            if str(cat_id) in self._by_id
        }
        self._unlocked.update(remote_unlocked)

        remote_duplicates = remote.get("duplicates", {})
        if isinstance(remote_duplicates, dict):
            for cat_id, amount in remote_duplicates.items():
                cat_id = str(cat_id)
                if cat_id not in self._by_id:
                    continue
                try:
                    normalized = max(0, int(amount))
                except (TypeError, ValueError):
                    continue
                self._duplicates[cat_id] = max(self._duplicates.get(cat_id, 0), normalized)

        def maximum(field, current, *, modulo=None):
            try:
                value = max(current, max(0, int(remote.get(field, 0) or 0)))
            except (TypeError, ValueError):
                value = current
            return value % modulo if modulo else value

        self._download_progress = maximum("downloadProgress", self._download_progress, modulo=10)
        self._earned_rolls = maximum("earnedRolls", self._earned_rolls)
        self._total_downloads = maximum("totalDownloads", self._total_downloads)
        self._total_rolls = maximum("totalRolls", self._total_rolls)
        self._last_daily_roll = max(self._last_daily_roll, str(remote.get("lastDailyRoll") or ""))

        for attribute, field in (
            ("_rewarded_source_hashes", "rewardedSourceHashes"),
            ("_claimed_promotions", "claimedPromotions"),
        ):
            values = remote.get(field, [])
            if isinstance(values, list):
                getattr(self, attribute).update(
                    str(value) for value in values if isinstance(value, str) and value
                )

        remote_equipped = str(remote.get("equippedId") or "")
        local_is_fresh = len(before["unlockedIds"]) <= 1 and before["totalRolls"] == 0
        if (
            remote_equipped in self._unlocked
            and remote_equipped in self._by_id
            and (local_is_fresh or self._equipped_id not in self._unlocked)
        ):
            self._equipped_id = remote_equipped

        if self.sync_snapshot() == before:
            return
        self._refresh()
        self._persist()

    def _choose_cat(self) -> CatDefinition:
        rollable = [cat for cat in self.catalog if not cat.exclusive]
        locked = [cat for cat in rollable if cat.id not in self._unlocked]
        candidates = locked or rollable
        by_rarity: dict[int, list[CatDefinition]] = {}
        for cat in candidates:
            by_rarity.setdefault(cat.rarity, []).append(cat)
        rarities = sorted(by_rarity)
        rarity = self._rng.choices(
            rarities,
            weights=[ROLL_WEIGHTS[value] for value in rarities],
            k=1,
        )[0]
        return self._rng.choice(by_rarity[rarity])

    @Slot(int)
    def recordSuccessfulDownloads(self, amount=1):
        amount = max(0, int(amount))
        if not amount:
            return
        self._total_downloads += amount
        rolls, self._download_progress = divmod(self._download_progress + amount, 10)
        self._earned_rolls += rolls
        self._refresh()
        self._persist()
        if rolls:
            pending = self._earned_rolls
            self.notificationRequested.emit(
                "success",
                f"¡{rolls} tirada{'s' if rolls != 1 else ''} gatuna{'s' if rolls != 1 else ''} conseguida{'s' if rolls != 1 else ''}!",
                f"Tienes {pending} disponible{'s' if pending != 1 else ''}. Abre Personalización para usarlas.",
            )

    @Slot(int)
    def grantBonusRolls(self, amount):
        """Añade una recompensa ya autorizada por el servidor y la persiste al instante."""
        amount = max(0, int(amount or 0))
        if not amount:
            return
        self._earned_rolls += amount
        self._refresh()
        self._persist()

    @Slot(str)
    def recordSuccessfulSource(self, source_key: str):
        source_key = str(source_key or "").strip()
        if not source_key:
            return
        fingerprint = hashlib.sha256(source_key.encode("utf-8")).hexdigest()
        if fingerprint in self._rewarded_source_hashes:
            self.notificationRequested.emit(
                "info", "Descarga repetida",
                "El archivo se descargó, pero este contenido ya contó para la colección gatuna.",
            )
            return
        self._rewarded_source_hashes.add(fingerprint)
        self.recordSuccessfulDownloads(1)

    @Slot(result="QVariantMap")
    def roll(self):
        daily_available = self._daily_available()
        if not daily_available and self._earned_rolls <= 0:
            self.notificationRequested.emit(
                "warning", "Todavía no hay tiradas", "Completa 10 descargas o vuelve mañana.",
            )
            return {}
        if daily_available:
            self._last_daily_roll = self._today().isoformat()
        else:
            self._earned_rolls -= 1

        cat = self._choose_cat()
        is_new = cat.id not in self._unlocked
        if is_new:
            self._unlocked.add(cat.id)
        else:
            self._duplicates[cat.id] = self._duplicates.get(cat.id, 0) + 1
        self._total_rolls += 1
        result = self._result(
            cat,
            isNew=is_new,
            themeUnlocked=bool(is_new and cat.rarity >= 5),
            effectUpgraded=not is_new,
        )
        self._refresh()
        self._persist()
        self.revealRequested.emit(result)
        return result

    @Slot(str, result="QVariantMap")
    def unlockPromotionalCat(self, cat_name):
        """Desbloquea una recompensa promocional local de forma persistente e idempotente."""
        wanted = str(cat_name or "").strip().casefold()
        cat = next((item for item in self.catalog if item.name.casefold() == wanted), None)
        if cat is None:
            self.notificationRequested.emit(
                "error", "Recompensa no disponible", f"No se encontró {str(cat_name or '').strip()} en la colección.",
            )
            return {}

        is_new = cat.id not in self._unlocked
        if is_new:
            self._unlocked.add(cat.id)
            self._refresh()
            self._persist()
        result = self._result(
            cat,
            isNew=is_new,
            themeUnlocked=bool(is_new and cat.rarity >= 5),
        )
        if is_new:
            self.revealRequested.emit(result)
            self.notificationRequested.emit(
                "success", f"{cat.name} {cat.rarity}★ desbloqueado", "Ya está disponible en Personalización.",
            )
        else:
            self.notificationRequested.emit(
                "info", f"{cat.name} ya es tuyo", "Puedes equiparlo desde Personalización.",
            )
        return result

    @Slot(result="QVariantMap")
    def claimZaneBirthdayReward(self):
        """Entrega una sola vez la recompensa local del cumpleaños de Zane de 2026."""
        campaign = "zane-birthday-2026"
        if self._today() != date(2026, 8, 26) or campaign in self._claimed_promotions:
            return {}
        dog = next((cat for cat in self.catalog if cat.name.casefold() == "perro zane"), None)
        if dog is None:
            return {}

        self._claimed_promotions.add(campaign)
        self._earned_rolls += 10
        is_new = dog.id not in self._unlocked
        self._unlocked.add(dog.id)
        self._refresh()
        self._persist()
        return {
            "campaign": campaign,
            "title": "¡Feliz cumpleaños, Zane!",
            "message": "Hoy celebramos a Zane con 10 rolleos y PERRO ZANE 5★, una recompensa exclusiva de este día.",
            "rewardRolls": 10,
            "cat": self._result(dog, isNew=is_new, themeUnlocked=is_new),
        }

    @Slot(str)
    def equip(self, cat_id):
        cat_id = str(cat_id)
        if cat_id not in self._unlocked or cat_id not in self._by_id:
            self.notificationRequested.emit("warning", "Gato bloqueado", "Desbloquéalo primero con una tirada.")
            return
        if cat_id == self._equipped_id:
            return
        self._equipped_id = cat_id
        cat = self._by_id[cat_id]
        self._refresh()
        self._persist()
        self.equippedRequested.emit(self._result(cat))
        self.notificationRequested.emit("success", "Gato equipado", cat.name)
