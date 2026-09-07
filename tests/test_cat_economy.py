"""Regression coverage for virtual boxes, stock, migration and stale cloud writes."""
import random
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.cat_gacha import BOXES, economy_snapshot, merge_economy
from src.ui.cat_gacha_controller import CatGachaController
from src.ui.social_controller import SocialController

ROOT = Path(__file__).resolve().parents[1]

class Store:
    def __init__(self, saved=None):
        self.data = {"cat_gacha": deepcopy(saved or {})}
    def get(self, key, default=None):
        return deepcopy(self.data.get(key, default))
    def set(self, key, value):
        self.data[key] = deepcopy(value)

def make(saved=None, seed=41):
    return CatGachaController(ROOT, Store(saved), rng=random.Random(seed), today_provider=lambda: date(2026, 9, 6))

def test_migration_preserves_downloads_tickets_duplicates_and_original_backup():
    initial = make()
    cat = initial.catalog[0]
    legacy = {"schema": 5, "totalDownloads": 128, "downloadProgress": 8,
              "earnedRolls": 7, "totalRolls": 12, "unlockedIds": [cat.id],
              "equippedId": cat.id, "duplicates": {cat.id: 3}}
    controller = make(legacy)
    assert controller.state["walletCents"] == 700
    assert controller.state["totalDownloads"] == 128
    assert controller.state["downloadProgress"] == 8
    assert controller._inventory[cat.id] == 4
    assert controller.settings.get("cat_gacha_legacy_backup") == legacy
    restored = make(controller.sync_snapshot())
    assert restored.state["walletCents"] == 700
    assert restored._inventory[cat.id] == 4

def test_unique_downloads_credit_once_across_restart():
    controller = make()
    for index in range(10):
        controller.recordSuccessfulSource(f"youtube:{index}")
    assert controller.state["walletCents"] == 100
    restored = make(controller.sync_snapshot())
    for index in range(10):
        restored.recordSuccessfulSource(f"youtube:{index}")
    assert restored.state["walletCents"] == 100
    assert restored.state["totalDownloads"] == 10

def test_box_charge_winner_and_reentrant_guard_are_atomic():
    controller = make()
    controller.grantBonusRolls(5)
    result = controller.openBox("rare")
    assert result
    assert controller.state["walletCents"] == 0
    assert result["reel"][result["winningIndex"]]["catId"] == result["catId"]
    assert controller.openBox("daily") == {}
    assert controller.state["totalRolls"] == 1
    assert controller._inventory[result["catId"]] >= 1
    restored = make(controller.sync_snapshot())
    assert restored.state["walletCents"] == 0
    assert restored._inventory[result["catId"]] >= 1
    assert not restored.state["opening"]

def test_daily_box_does_not_spend_wallet_and_cannot_repeat():
    controller = make()
    controller.grantBonusRolls(2)
    assert controller.openBox("daily")
    controller.finishOpening()
    assert controller.state["walletCents"] == 200
    assert controller.openBox("daily") == {}
    assert controller.openBox("missing") == {}
    assert controller.openBox("mythic") == {}
    assert controller.state["walletCents"] == 200

def test_sell_last_unequipped_copy_stays_sold_after_restart_and_cloud_merge():
    controller = make()
    cat = next(cat for cat in controller.catalog if cat.id != controller.state["equippedId"])
    controller.unlockPromotionalCat(cat.name)
    stale = controller.sync_snapshot()
    downloads = controller.state["totalDownloads"]
    discovered = controller.state["unlockedCount"]
    assert controller.sellCat(cat.id)
    sold = controller.sync_snapshot()
    assert sold["inventory"][cat.id] == 0
    assert sold["walletCents"] == cat.price_cents
    controller.mergeRemoteState(stale)
    assert controller._inventory[cat.id] == 0
    merged = SocialController._merge_collection_states(sold, stale)
    restored = make(merged)
    assert restored._inventory[cat.id] == 0
    assert restored.state["walletCents"] == cat.price_cents
    assert restored.state["unlockedCount"] == discovered
    assert restored.state["totalDownloads"] == downloads
    assert not restored.sellCat(cat.id)

def test_last_equipped_copy_is_protected_but_duplicate_can_be_sold():
    controller = make()
    equipped = controller.state["equippedId"]
    assert not controller.sellCat(equipped)
    controller._inventory[equipped] = 2
    assert controller.sellCat(equipped)
    assert controller._inventory[equipped] == 1
    assert not controller.sellCat(equipped)

def test_spent_balance_is_not_revived_by_legacy_or_modern_stale_snapshot():
    controller = make()
    controller.grantBonusRolls(3)
    stale = controller.sync_snapshot()
    controller.openBox("basic")
    controller.finishOpening()
    controller.mergeRemoteState(stale)
    assert controller.state["walletCents"] == 200
    legacy = {k: v for k, v in stale.items() if k not in ("walletCents", "inventory", "economyRevision", "economyUpdatedAt")}
    legacy["schema"] = 5
    controller.mergeRemoteState(legacy)
    assert controller.state["walletCents"] == 200

def test_economy_merge_is_commutative_idempotent_and_keeps_zero_stock():
    a = {"walletCents": 100, "inventory": {"one": 1}, "economyRevision": 5, "economyUpdatedAt": 100}
    b = {"walletCents": 135, "inventory": {"one": 0}, "economyRevision": 6, "economyUpdatedAt": 101}
    assert merge_economy(a, b) == merge_economy(b, a) == economy_snapshot(b)
    assert merge_economy(b, b) == economy_snapshot(b)

def test_prices_are_stable_rarity_bands_and_box_odds_sum_to_100():
    controller = make()
    for rarity in range(1, 6):
        assert max(cat.price_cents for cat in controller.catalog if cat.rarity == rarity) < min(cat.price_cents for cat in controller.catalog if cat.rarity == rarity + 1)
    for box in BOXES:
        assert abs(sum(box["weights"].values()) - 100) < 0.0001
    fresh = make()
    assert [cat.price_cents for cat in controller.catalog] == [cat.price_cents for cat in fresh.catalog]

def test_paid_draws_can_repeat_before_collection_is_complete():
    controller = make()
    controller.grantBonusRolls(2)
    cat = next(cat for cat in controller.catalog if not cat.exclusive)
    controller._choose_cat = lambda weights=None: cat
    first = controller.openBox("basic")
    controller.finishOpening()
    second = controller.openBox("basic")
    assert first["isNew"]
    assert not second["isNew"]
    assert controller._inventory[cat.id] == 2

def test_scoreboard_ranks_downloads_only_with_shared_ties():
    controller = SocialController(ROOT, Store(), Mock())
    response = Mock(status_code=200)
    response.json.return_value = [
        {"username": "Z", "downloads_count": 50, "cats_count": 149},
        {"username": "A", "downloads_count": 50, "cats_count": 1},
        {"username": "B", "downloads_count": 40, "cats_count": 150},
    ]
    with patch("src.ui.social_controller.requests.post", return_value=response):
        result = controller._leaderboard_worker()
    assert [(row["username"], row["rank"]) for row in result["leaderboard"]] == [("A", 1), ("Z", 1), ("B", 3)]
    assert result["communityDownloads"] == 140

def test_paid_box_expected_resale_is_below_price():
    controller = make()
    for box in BOXES:
        if not box["priceCents"]:
            continue
        expected = 0
        for rarity, weight in box["weights"].items():
            prices = [cat.price_cents for cat in controller.catalog if cat.rarity == rarity and not cat.exclusive]
            expected += sum(prices) / len(prices) * weight / 100
        assert 0 < expected < box["priceCents"], (box["id"], expected)
