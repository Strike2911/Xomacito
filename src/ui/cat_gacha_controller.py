from __future__ import annotations

import random
import hashlib
import time
from datetime import date
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QCoreApplication, QObject, Property, QTimer, QUrl, Signal, Slot, QSortFilterProxyModel

from src.core.cat_gacha import (box_candidates, BOXES, DOWNLOAD_REWARD_CENTS, RARITY_NAMES, ROLL_WEIGHTS,
                                CatDefinition, economy_snapshot, merge_economy, money,
                                load_cat_catalog, starter_cat, reset_economy, ECONOMY_EPOCH)

from .list_model import ObjectListModel
from .settings_store import SettingsStore


class InventoryFilter(QSortFilterProxyModel):
    def __init__(self, source, parent):
        super().__init__(parent)
        self.search = ""
        self.rarity = 0
        self.setSourceModel(source)

    def filterAcceptsRow(self, row, parent):
        item = self.sourceModel()._items[row]
        return (item.get("quantity", 0) > 0
                and (not self.rarity or item["rarity"] == self.rarity)
                and self.search in item["name"].casefold())


class CatGachaController(QObject):
    stateChanged = Signal()
    revealRequested = Signal("QVariantMap")
    equippedRequested = Signal("QVariantMap")
    notificationRequested = Signal(str, str, str)

    ROLES = [
        "catId", "name", "source", "rarity", "rarityColor", "stars",
        "animationStyle", "unlocked", "equipped", "duplicateCount",
        "effectLevel", "effectName", "quantity", "price", "priceCents", "canSell",
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
        self._inventory_model = InventoryFilter(self.collection, self)
        self._skip_animation = bool(settings.get("skip_cat_animation", False))
        self._static_cards = {cat.id: {
            "catId": cat.id, "name": cat.name, "source": self._url(cat),
            "rarity": cat.rarity, "rarityColor": cat.rarity_color,
            "stars": "★" * cat.rarity, "animationStyle": self._animation_style(cat),
            "priceCents": cat.price_cents, "price": money(cat.price_cents),
        } for cat in self.catalog}

        saved = settings.get("cat_gacha", {})
        if not isinstance(saved, dict):
            saved = {}
        if "walletCents" not in saved and settings.get("cat_gacha_legacy_backup") is None:
            settings.set("cat_gacha_legacy_backup", saved)
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
        self._historical_unlocked_count = max(
            len(unlocked),
            self._normalized_historical_count(saved.get("historicalUnlockedCount", 0)),
        )
        self._restore_historical_unlocks(self._historical_unlocked_count)
        self._equipped_id = equipped
        self._download_progress = max(0, int(saved.get("downloadProgress", 0))) % 10
        self._earned_rolls = max(0, int(saved.get("earnedRolls", 0)))
        self._total_downloads = max(0, int(saved.get("totalDownloads", 0)))
        self._total_rolls = max(0, int(saved.get("totalRolls", 0)))
        legacy_balance_revision = self._total_downloads + self._total_rolls
        self._roll_balance_revision = max(
            0, int(saved.get("rollBalanceRevision", legacy_balance_revision) or 0),
        )
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
        migrated = economy_snapshot({**saved, "unlockedIds": sorted(self._unlocked)})
        self._wallet = migrated["walletCents"]
        self._inventory = migrated["inventory"]
        self._economy_revision = migrated["economyRevision"]
        self._economy_updated_at = migrated["economyUpdatedAt"]
        self._economy_epoch = migrated["economyEpoch"]
        self._reset_credit = migrated["resetCreditCents"]
        self._liquidated_inventory = migrated["liquidatedInventory"]
        self._opening = False
        self._repair_equipped()
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

    @Property(QObject, constant=True)
    def inventoryModel(self):
        return self._inventory_model

    @Slot(str, int)
    def setInventoryFilter(self, search, rarity):
        self._inventory_model.search = str(search).casefold().strip()
        self._inventory_model.rarity = int(rarity)
        self._inventory_model.invalidateFilter()

    @Slot(bool)
    def setSkipAnimation(self, enabled):
        if self._skip_animation == bool(enabled):
            return
        self._skip_animation = bool(enabled)
        self.settings.set("skip_cat_animation", self._skip_animation)
        self._refresh()

    @Slot()
    def ensureEconomyReset(self):
        if self._economy_epoch >= ECONOMY_EPOCH:
            return
        before = self.sync_snapshot()
        self.settings.set("cat_economy_reset_backup", before)
        reset = reset_economy(before, self.catalog)
        self.mergeRemoteState(reset)
        self._equipped_id = reset["equippedId"]
        self._refresh()
        self._persist()

    def _url(self, cat: CatDefinition) -> str:
        return QUrl.fromLocalFile(str(cat.avatar_path)).toString()

    def _normalized_historical_count(self, value) -> int:
        """Limita el contador heredado al catálogo restaurable actual."""
        try:
            requested = max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0
        restorable = sum(not cat.exclusive for cat in self.catalog) + sum(
            cat.exclusive and cat.id in self._unlocked for cat in self.catalog
        )
        return min(requested, restorable)

    def _restore_historical_unlocks(self, requested_count: int) -> int:
        """Reconstruye IDs perdidos usando el máximo histórico de la misma cuenta.

        Versiones antiguas sólo enviaban el número al scoreboard. Si la fila
        privada se creó después, el conteo sobrevivió pero no la lista de IDs.
        Los exclusivos nunca se inventan: sólo se completan gatos normales.
        """
        target = self._normalized_historical_count(requested_count)
        missing = max(0, target - len(self._unlocked))
        if not missing:
            return 0
        candidates = [
            cat for cat in self.catalog
            if not cat.exclusive and cat.id not in self._unlocked
        ]
        restored = candidates[:missing]
        self._unlocked.update(cat.id for cat in restored)
        return len(restored)

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
            "quantity": self._inventory.get(cat.id, 0),
            "priceCents": cat.price_cents,
            "price": money(cat.price_cents),
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
        self._earned_rolls = self._wallet // DOWNLOAD_REWARD_CENTS
        equipped = self._by_id[self._equipped_id]
        daily_available = self._daily_available()
        visible_catalog = [
            cat for cat in self.catalog
            if not cat.exclusive or cat.id in self._unlocked
        ]
        completion_catalog = [cat for cat in self.catalog if not cat.exclusive]
        completion_unlocked = sum(cat.id in self._unlocked for cat in completion_catalog)
        og_pool = box_candidates(self.catalog, BOXES[0])
        og_counts = {rarity: sum(cat.rarity == rarity for cat in og_pool) for rarity in RARITY_NAMES}
        self._state = {
            "skipAnimation": self._skip_animation,
            "resetCredit": money(self._reset_credit),
            "economyEpoch": self._economy_epoch,
            "wallet": money(self._wallet),
            "walletCents": self._wallet,
            "ownedCount": sum(self._inventory.values()),
            "ownedUniqueCount": sum(value > 0 for value in self._inventory.values()),
            "inventoryValue": money(sum(self._by_id[key].price_cents * value for key, value in self._inventory.items() if key in self._by_id)),
            "opening": self._opening,
            "ogFeatured": [self._result(cat) for cat in og_pool if cat.rarity == 6],
            "ogContents": [self._result(cat, odds=f"{BOXES[0]['weights'][cat.rarity] / og_counts[cat.rarity]:.4f}%") for cat in og_pool],
            "boxes": [{**{key: value for key, value in box.items() if key != "weights"},
                       "price": "Gratis" if not box["priceCents"] else money(box["priceCents"]),
                       "available": not self._opening and (daily_available if box["id"] == "daily" else self._wallet >= box["priceCents"]),
                       "odds": " · ".join(f"{RARITY_NAMES[r]} {w:g}%" for r, w in box["weights"].items())}
                      for box in BOXES],
            "downloadProgress": self._download_progress,
            "downloadProgressRatio": self._download_progress / 10.0,
            "downloadsUntilRoll": 10 - self._download_progress,
            "earnedRolls": self._earned_rolls,
            "totalDownloads": self._total_downloads,
            "totalRolls": self._total_rolls,
            "dailyAvailable": daily_available,
            "canRoll": not self._opening and (daily_available or self._wallet >= DOWNLOAD_REWARD_CENTS),
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
                    **self._static_cards[cat.id],
                    "unlocked": cat.id in self._unlocked,
                    "quantity": self._inventory.get(cat.id, 0),
                    "priceCents": cat.price_cents,
                    "price": money(cat.price_cents),
                    "canSell": self._can_sell(cat.id),
                    "equipped": cat.id == self._equipped_id,
                    "duplicateCount": self._duplicates.get(cat.id, 0),
                    "effectLevel": min(5, self._duplicates.get(cat.id, 0)),
                    "effectName": self.EFFECT_NAMES[
                        min(5, self._duplicates.get(cat.id, 0))
                    ],
                }
            )
        self.collection.reconcile(items, "catId")
        self._state["inventoryItems"] = items
        self.stateChanged.emit()

    def _persist(self):
        self.settings.set(
            "cat_gacha",
            self.sync_snapshot(),
        )

    def _advance_roll_balance_revision(self, amount=1):
        """Marca una mutación del saldo para que una copia antigua no lo reviva."""
        self._roll_balance_revision += max(1, int(amount or 1))
        self._economy_revision = max(self._economy_revision + 1, self._roll_balance_revision)
        self._economy_updated_at = time.time_ns()

    def sync_snapshot(self) -> dict:
        """Estado portable de la colección para restaurarlo en otra PC."""
        return {
            "schema": 7,
            "economyEpoch": self._economy_epoch,
            "resetCreditCents": self._reset_credit,
            "liquidatedInventory": self._liquidated_inventory,
            "walletCents": self._wallet,
            "inventory": dict(sorted(self._inventory.items())),
            "economyRevision": self._economy_revision,
            "economyUpdatedAt": self._economy_updated_at,
            "downloadProgress": self._download_progress,
            "earnedRolls": self._earned_rolls,
            "totalDownloads": self._total_downloads,
            "totalRolls": self._total_rolls,
            "rollBalanceRevision": self._roll_balance_revision,
            "lastDailyRoll": self._last_daily_roll,
            "unlockedIds": sorted(self._unlocked),
            "historicalUnlockedCount": max(
                self._historical_unlocked_count, len(self._unlocked),
            ),
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
        economy = merge_economy(before, remote)

        remote_unlocked = {
            str(cat_id) for cat_id in remote.get("unlockedIds", [])
            if str(cat_id) in self._by_id
        }
        self._unlocked.update(remote_unlocked)
        self._historical_unlocked_count = max(
            self._historical_unlocked_count,
            self._normalized_historical_count(remote.get("historicalUnlockedCount", 0)),
            len(self._unlocked),
        )
        self._restore_historical_unlocks(self._historical_unlocked_count)

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

        def normalized_number(source, field, maximum=10_000_000):
            try:
                return max(0, min(maximum, int(source.get(field, 0) or 0)))
            except (TypeError, ValueError):
                return 0

        def balance_revision(source):
            if "rollBalanceRevision" in source:
                return normalized_number(source, "rollBalanceRevision")
            # Los estados anteriores a schema 4 no tenían reloj de saldo. Esta
            # base monotónica permite restaurarlos sin otorgar tiradas gastadas.
            return normalized_number(source, "totalDownloads") + normalized_number(
                source, "totalRolls",
            )

        local_revision = self._roll_balance_revision
        remote_revision = balance_revision(remote)
        local_rank = (local_revision, self._total_rolls, self._total_downloads)
        remote_rank = (
            remote_revision,
            normalized_number(remote, "totalRolls"),
            normalized_number(remote, "totalDownloads"),
        )
        local_is_fresh = len(before["unlockedIds"]) <= 1 and before["totalRolls"] == 0
        if remote_rank > local_rank or (local_is_fresh and len(remote_unlocked) > 1):
            self._download_progress = normalized_number(remote, "downloadProgress", 9)
            self._earned_rolls = normalized_number(remote, "earnedRolls")
            self._roll_balance_revision = remote_revision

        self._total_downloads = max(
            self._total_downloads, normalized_number(remote, "totalDownloads"),
        )
        self._total_rolls = max(self._total_rolls, normalized_number(remote, "totalRolls"))
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
        if (
            remote_equipped in self._unlocked
            and remote_equipped in self._by_id
            and (local_is_fresh or self._equipped_id not in self._unlocked)
        ):
            self._equipped_id = remote_equipped

        if self.sync_snapshot() == before and economy == economy_snapshot(before):
            return
        self._wallet = economy["walletCents"]
        self._inventory = {key: value for key, value in economy["inventory"].items() if key in self._by_id}
        self._economy_revision = economy["economyRevision"]
        self._economy_updated_at = economy["economyUpdatedAt"]
        self._economy_epoch = economy["economyEpoch"]
        self._reset_credit = economy["resetCreditCents"]
        self._liquidated_inventory = economy["liquidatedInventory"]
        self._repair_equipped()
        self._refresh()
        self._persist()

    def _choose_cat(self, weights=None, box=None) -> CatDefinition:
        weights = weights or ROLL_WEIGHTS
        candidates = box_candidates(self.catalog, box or {"weights": weights})
        by_rarity: dict[int, list[CatDefinition]] = {}
        for cat in candidates:
            by_rarity.setdefault(cat.rarity, []).append(cat)
        rarities = sorted(by_rarity)
        rarity = self._rng.choices(
            rarities,
            weights=[weights[value] for value in rarities],
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
        self._wallet += rolls * DOWNLOAD_REWARD_CENTS
        self._advance_roll_balance_revision(amount)
        self._refresh()
        self._persist()
        if rolls:
            self.notificationRequested.emit(
                "success", f"+{money(rolls * DOWNLOAD_REWARD_CENTS)} virtuales",
                f"Saldo: {money(self._wallet)}. Abre Personalización para elegir una caja.",
            )

    @Slot(int)
    def grantBonusRolls(self, amount):
        """Añade una recompensa ya autorizada por el servidor y la persiste al instante."""
        amount = max(0, int(amount or 0))
        if not amount:
            return
        self._wallet += amount * DOWNLOAD_REWARD_CENTS
        self._advance_roll_balance_revision(amount)
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
        return self.openBox("daily" if self._daily_available() else "og")

    @Slot(str, result="QVariantMap")
    def openBox(self, box_id):
        free_daily = box_id == "daily"
        # Old buttons/shortcuts resolve to the current themed collection.
        resolved_id = "og" if box_id in {"daily", "basic"} else box_id
        box = next((item for item in BOXES if item["id"] == resolved_id), None)
        if not box or self._opening:
            return {}
        if (free_daily and not self._daily_available()) or (not free_daily and self._wallet < box["priceCents"]):
            self.notificationRequested.emit("warning", "Caja no disponible", "Completa descargas, vende gatos o vuelve mañana por tu regalo diario.")
            return {}
        cat = self._choose_cat(box["weights"], box)
        if free_daily:
            self._last_daily_roll = self._today().isoformat()
        else:
            self._wallet -= box["priceCents"]
        self._advance_roll_balance_revision()
        self._inventory[cat.id] = self._inventory.get(cat.id, 0) + 1
        is_new = cat.id not in self._unlocked
        self._unlocked.add(cat.id)
        if not is_new:
            self._duplicates[cat.id] = self._duplicates.get(cat.id, 0) + 1
        self._total_rolls += 1
        self._opening = True
        reel = [] if self._skip_animation else [self._result(self._choose_cat(box["weights"], box)) for _ in range(40)]
        if reel:
            reel[34] = self._result(cat)
        result = self._result(cat, isNew=is_new, themeUnlocked=bool(is_new and cat.rarity >= 5),
                              effectUpgraded=not is_new, boxName=box["name"], reel=reel, winningIndex=34)
        self._refresh()
        self._persist()
        self.revealRequested.emit(result)
        return result

    @Slot()
    def finishOpening(self):
        if self._opening:
            self._opening = False
            self._refresh()

    def _repair_equipped(self):
        # Zero is an explicit sale tombstone. Only legacy discoveries without
        # an inventory entry need restoring; sold cats must stay at zero.
        if self._economy_epoch < ECONOMY_EPOCH:
            for cat_id in self._unlocked:
                self._inventory.setdefault(cat_id, 1 + self._duplicates.get(cat_id, 0))
        if self._inventory.get(self._equipped_id, 0) <= 0:
            owned = [key for key, value in self._inventory.items() if value > 0 and key in self._by_id]
            if not owned:
                starter = starter_cat(self.catalog)
                self._inventory[starter.id] = 1
                self._unlocked.add(starter.id)
                owned = [starter.id]
            self._equipped_id = owned[0]

    def _can_sell(self, cat_id):
        count = self._inventory.get(cat_id, 0)
        return count > 0 and sum(self._inventory.values()) > 1 and (cat_id != self._equipped_id or count > 1)

    @Slot(str, result=bool)
    def sellCat(self, cat_id):
        if self._opening or cat_id not in self._by_id or not self._can_sell(cat_id):
            return False
        cat = self._by_id[cat_id]
        self._inventory[cat_id] -= 1
        self._wallet += cat.price_cents
        self._advance_roll_balance_revision()
        self._refresh()
        self._persist()
        self.notificationRequested.emit("success", "Gato vendido", f"{cat.name} · +{money(cat.price_cents)} virtuales")
        return True

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
            self._inventory[cat.id] = self._inventory.get(cat.id, 0) + 1
            self._advance_roll_balance_revision()
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
        self._wallet += 10 * DOWNLOAD_REWARD_CENTS
        self._advance_roll_balance_revision(10)
        is_new = dog.id not in self._unlocked
        self._unlocked.add(dog.id)
        self._inventory[dog.id] = self._inventory.get(dog.id, 0) + 1
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
        if self._inventory.get(cat_id, 0) <= 0 or cat_id not in self._by_id:
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
