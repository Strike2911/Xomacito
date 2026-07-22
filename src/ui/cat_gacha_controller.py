from __future__ import annotations

import random
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
    notificationRequested = Signal(str, str, str)

    ROLES = [
        "catId", "name", "source", "rarity", "rarityColor", "stars",
        "unlocked", "equipped", "duplicateCount",
    ]

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
        self._state = {
            "downloadProgress": self._download_progress,
            "downloadProgressRatio": self._download_progress / 10.0,
            "downloadsUntilRoll": 10 - self._download_progress,
            "earnedRolls": self._earned_rolls,
            "totalDownloads": self._total_downloads,
            "totalRolls": self._total_rolls,
            "dailyAvailable": daily_available,
            "canRoll": daily_available or self._earned_rolls > 0,
            "unlockedCount": len(self._unlocked),
            "totalCount": len(self.catalog),
            "equippedId": equipped.id,
            "equippedName": equipped.name,
            "equippedSource": self._url(equipped),
            "equippedRarity": equipped.rarity,
            "equippedColor": equipped.rarity_color,
            "equippedStars": "★" * equipped.rarity,
            "rollButtonText": (
                "Tirada diaria gratis"
                if daily_available
                else f"Usar tirada ({self._earned_rolls})"
                if self._earned_rolls
                else f"Faltan {10 - self._download_progress} descargas"
            ),
        }
        items = []
        for cat in self.catalog:
            items.append(
                {
                    "catId": cat.id,
                    "name": cat.name,
                    "source": self._url(cat),
                    "rarity": cat.rarity,
                    "rarityColor": cat.rarity_color,
                    "stars": "★" * cat.rarity,
                    "unlocked": cat.id in self._unlocked,
                    "equipped": cat.id == self._equipped_id,
                    "duplicateCount": self._duplicates.get(cat.id, 0),
                }
            )
        self.collection.replace(items)
        self.stateChanged.emit()

    def _persist(self):
        self.settings.set(
            "cat_gacha",
            {
                "schema": 1,
                "downloadProgress": self._download_progress,
                "earnedRolls": self._earned_rolls,
                "totalDownloads": self._total_downloads,
                "totalRolls": self._total_rolls,
                "lastDailyRoll": self._last_daily_roll,
                "unlockedIds": sorted(self._unlocked),
                "equippedId": self._equipped_id,
                "duplicates": dict(sorted(self._duplicates.items())),
            },
        )

    def _choose_cat(self) -> CatDefinition:
        locked = [cat for cat in self.catalog if cat.id not in self._unlocked]
        candidates = locked or list(self.catalog)
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
        result = {
            "catId": cat.id,
            "name": cat.name,
            "source": self._url(cat),
            "rarity": cat.rarity,
            "rarityColor": cat.rarity_color,
            "stars": "★" * cat.rarity,
            "isNew": is_new,
        }
        self._refresh()
        self._persist()
        self.revealRequested.emit(result)
        return result

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
        self.notificationRequested.emit("success", "Gato equipado", cat.name)
