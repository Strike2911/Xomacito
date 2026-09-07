from copy import deepcopy

from src.core.cat_gacha import reset_economy, merge_economy, starter_cat
from src.ui.social_controller import SocialController
from test_cat_economy import make


def test_liquidation_once_preserves_cash_downloads_and_pays_every_copy():
    controller = make()
    cat = controller.catalog[0]
    old = controller.sync_snapshot()
    old.update(walletCents=731, inventory={cat.id: 3}, totalDownloads=987,
               rewardedSourceHashes=["already-counted"], downloadProgress=7)
    reset = reset_economy(old, controller.catalog)
    assert reset["walletCents"] == 731 + cat.price_cents * 3
    assert reset["resetCreditCents"] == cat.price_cents * 3
    assert reset["totalDownloads"] == 987
    assert reset["downloadProgress"] == 7
    assert reset["rewardedSourceHashes"] == ["already-counted"]
    assert sum(reset["inventory"].values()) == 1
    assert reset["inventory"][starter_cat(controller.catalog).id] == 1
    assert reset_economy(reset, controller.catalog) == reset


def test_previous_season_cannot_restore_stock_even_with_higher_revision():
    controller = make()
    old = controller.sync_snapshot()
    reset = reset_economy(old, controller.catalog)
    stale = {**old, "economyRevision": 99999999, "walletCents": 99999999}
    assert merge_economy(reset, stale)["walletCents"] == reset["walletCents"]
    merged = SocialController._merge_collection_states(reset, stale)
    assert merged["economyEpoch"] == 1
    assert merged["inventory"] == reset["inventory"]
    controller.mergeRemoteState(merged)
    assert controller.sync_snapshot()["inventory"] == reset["inventory"]


def test_startup_reset_has_backup_and_never_pays_twice():
    controller = make()
    before = deepcopy(controller.sync_snapshot())
    controller.ensureEconomyReset()
    assert controller.settings.get("cat_economy_reset_backup") == before
    after = controller.sync_snapshot()
    controller.ensureEconomyReset()
    assert controller.sync_snapshot() == after
    restored = make(after)
    restored.ensureEconomyReset()
    assert restored.state["walletCents"] == after["walletCents"]


def test_skip_is_persistent_and_avoids_building_reel():
    controller = make()
    controller.setSkipAnimation(True)
    assert controller.settings.get("skip_cat_animation") is True
    result = controller.openBox("daily")
    assert result["catId"]
    assert result["reel"] == []
    controller.finishOpening()
    controller.setSkipAnimation(False)
    controller.grantBonusRolls(2)
    assert len(controller.openBox("basic")["reel"]) == 40


def test_sale_updates_roles_without_resetting_grid():
    controller = make()
    controller.grantBonusRolls(3)
    result = controller.openBox("basic")
    controller.finishOpening()
    events = []
    controller.collection.modelReset.connect(lambda: events.append("reset"))
    controller.collection.dataChanged.connect(lambda *args: events.append("change"))
    assert controller.sellCat(result["catId"])
    assert "change" in events
    assert "reset" not in events
