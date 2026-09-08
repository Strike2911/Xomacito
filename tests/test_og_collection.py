from pathlib import Path
from src.core.cat_gacha import OG_MYTHIC_IDS, ROLL_WEIGHTS, box_candidates, load_cat_catalog


def test_og_mythics_are_exactly_requested_cats():
    catalog = load_cat_catalog(Path(__file__).resolve().parents[1])
    pool = box_candidates(catalog, {"weights": ROLL_WEIGHTS, "mythicIds": OG_MYTHIC_IDS})
    assert {c.name for c in pool if c.rarity == 6} == {"GATO STRIKE", "GATO PLAYERA", "GATO ZARKING"}
    assert {c.id for c in pool if c.rarity < 6} == {c.id for c in catalog if c.rarity < 6 and not c.exclusive}


def test_unscoped_boxes_keep_their_catalog():
    catalog = load_cat_catalog(Path(__file__).resolve().parents[1])
    assert {c.id for c in box_candidates(catalog, {"weights": ROLL_WEIGHTS})} == {c.id for c in catalog if not c.exclusive}


def test_paid_daily_and_roulette_obey_collection_without_reset():
    from src.ui.cat_gacha_controller import CatGachaController
    class Settings(dict):
        def set(self,key,value,*args,**kwargs): self[key]=value
    class MythicRandom:
        def choices(self,values,**kwargs): return [max(values)]
        def choice(self,values): return values[0]
    settings=Settings(cat_gacha={"economyEpoch":1,"walletCents":500,"inventory":{"cat-cf837ae651c8":1},"unlockedIds":["cat-cf837ae651c8"],"totalDownloads":31})
    controller=CatGachaController(Path(__file__).resolve().parents[1],settings,rng=MythicRandom())
    before=controller.sync_snapshot()
    paid=controller.openBox("og")
    assert paid["catId"] in OG_MYTHIC_IDS
    assert all(item["catId"] in OG_MYTHIC_IDS for item in paid["reel"])
    assert controller.sync_snapshot()["walletCents"] == before["walletCents"]-100
    controller._opening=False
    daily=controller.openBox("daily")
    assert daily["catId"] in OG_MYTHIC_IDS
    assert controller.sync_snapshot()["walletCents"] == before["walletCents"]-100
    controller._opening=False
    assert controller.openBox("daily") == {}
    assert controller.sync_snapshot()["inventory"]["cat-cf837ae651c8"] == 1
    assert controller.sync_snapshot()["totalDownloads"] == 31
