from datetime import date
from pathlib import Path
from test_cat_economy import Store
from src.core.cat_gacha import BOXES, box_candidates, load_cat_catalog
from src.ui.cat_gacha_controller import CatGachaController

ROOT = Path(__file__).resolve().parents[1]

def make(store=None, day=date(2026,10,6)):
    return CatGachaController(ROOT, store or Store(), today_provider=lambda: day)

def test_collections_are_separate_and_secret_hidden():
    cats = load_cat_catalog(ROOT)
    og, night = (box_candidates(cats, b) for b in BOXES)
    assert not ({c.id for c in og} & {c.id for c in night})
    assert len(night) == 67
    assert {c.name for c in night if c.rarity == 6} == {'GATO XOMAS','GATO MEGAS','GATO SPIKE','GATO MAGO','BLACK BULL'}
    c = make()
    assert not any(x['catId'] == 'halloween-hola' for x in c.state['inventoryItems'])
    assert next(x for x in cats if x.id == 'cat-655d97e229cb').name == 'GATO FOLLADOR'

def test_first_october_roll_persists_once_and_does_not_spoil_reel():
    c = make()
    assert c.openBox('night') == {}  # Insufficient balance does not consume gift.
    result = c.openBox('daily')
    assert result['catId'] == 'halloween-hola'
    assert all(x['catId'] != 'halloween-hola' for x in result['reel'])
    assert c._inventory['halloween-hola'] == 1
    restored = make(c.settings)
    restored.grantBonusRolls(1)
    assert restored.openBox('night')['catId'] != 'halloween-hola'
    assert 'halloween-first-roll-2026-10' in restored.sync_snapshot()['claimedPromotions']

def test_campaign_has_exact_month_boundaries():
    for day in (date(2026,9,30),date(2026,11,1),date(2027,10,1)):
        assert make(day=day).openBox('daily')['catId'] != 'halloween-hola'
    for day in (date(2026,10,1),date(2026,10,31)):
        assert make(day=day).openBox('daily')['catId'] == 'halloween-hola'


def test_secret_sound_waits_for_reveal_and_only_fires_once():
    for skip in (False, True):
        controller = make()
        controller.setSkipAnimation(skip)
        completed = []
        controller.revealCompleted.connect(completed.append)
        result = controller.openBox("daily")
        assert result["catId"] == "halloween-hola"
        assert not completed
        controller.finishOpening()
        controller.finishOpening()
        assert len(completed) == 1
        assert completed[0]["animationStyle"] == "hola-haunting"


def test_new_catalog_assets_sounds_and_displayed_odds():
    from src.core.notification_sound import gacha_sound_path
    cats = [cat for cat in load_cat_catalog(ROOT) if cat.collection == "night"]
    assert len(cats) == 68
    for cat in cats:
        assert cat.image_path.is_file()
        assert cat.avatar_path.is_file()
    for style in ("xomas-solar", "megas-storm", "hola-haunting"):
        assert gacha_sound_path(6, style).is_file()
    contents = make().state["nightContents"]
    assert len(contents) == 67
    assert not any(cat["catId"] == "halloween-hola" for cat in contents)
    assert abs(sum(float(cat["odds"].strip("%")) for cat in contents) - 100) < 0.01


def test_rebalance_keeps_weights_and_moves_existing_ids():
    cats = load_cat_catalog(ROOT)
    og, night = (box_candidates(cats, box) for box in BOXES)
    from collections import Counter
    assert Counter(cat.rarity for cat in night) == {1:27, 2:17, 3:11, 4:5, 5:2, 6:5}
    assert BOXES[0]["weights"] == BOXES[1]["weights"]
    assert any(cat.name == "PERRO ZANE" for cat in og)
    assert not any(cat.name == "PERRO ZANE" for cat in night)
    assert next(cat for cat in night if cat.id == "cat-e78cf17a3656").rarity == 6
