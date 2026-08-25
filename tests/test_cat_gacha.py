import json
import os
import random
import tempfile
import unittest
from collections import Counter
from datetime import date
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.core.cat_gacha import load_cat_catalog
from src.ui.cat_gacha_controller import CatGachaController
from src.ui.settings_store import SettingsStore


ROOT = Path(__file__).resolve().parents[1]


class CatGachaTests(unittest.TestCase):
    def test_real_collection_keeps_names_and_stable_random_rarities(self):
        catalog_path = ROOT / "assets" / "cat-collection" / "catalog.json"
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog = load_cat_catalog(ROOT)

        self.assertEqual(len(catalog), 150)
        self.assertEqual(len(payload["cats"]), 150)
        self.assertIn("GATITO PENSATIVO", {cat.name for cat in catalog})
        self.assertIn("GATO DIOS", {cat.name for cat in catalog})
        self.assertIn("GATO XOMACITO", {cat.name for cat in catalog})
        self.assertEqual(
            Counter(cat.rarity for cat in catalog),
            {1: 61, 2: 36, 3: 28, 4: 9, 5: 11, 6: 5},
        )
        expected_rarities = {
            "GATO DIOS": 5,
            "GATO DETECTIVE": 5,
            "GATO RARO": 3,
            "GATO SPIKE": 5,
            "GATO STRIKE": 6,
            "GATO ALE": 5,
            "RYKOZIO": 5,
            "JORGE": 3,
            "GATO CONDUCTOR": 3,
            "GATO INTELIGENTE": 3,
            "GATO MAGO": 6,
            "GATO PLAYERA": 6,
            "GATO ZARKING": 6,
            "BLACK BULL": 6,
            "PERRO ZANE": 5,
            "Frido": 5,
        }
        by_name = {cat.name.casefold(): cat for cat in catalog}
        for name, rarity in expected_rarities.items():
            self.assertEqual(by_name[name.casefold()].rarity, rarity)
        self.assertEqual(by_name["gato mago"].animation_style, "arcane-mage")
        self.assertEqual(by_name["gato playera"].animation_style, "playera-prismatic")
        self.assertEqual(by_name["gato zarking"].animation_style, "zarking-cyber")
        self.assertEqual(by_name["black bull"].animation_style, "blackbull-noir")
        self.assertEqual(by_name["gato strike"].animation_style, "strike-apex")
        self.assertTrue(all(cat.name == cat.name.upper() for cat in catalog if cat.name != "Frido"))
        self.assertTrue(by_name["perro zane"].exclusive)
        self.assertFalse(by_name["frido"].exclusive)
        for cat in catalog:
            self.assertTrue(cat.image_path.is_file())
            self.assertTrue(cat.avatar_path.is_file())
        with Image.open(catalog[0].avatar_path) as avatar:
            self.assertEqual(avatar.size, (384, 384))
            self.assertEqual(avatar.mode, "RGBA")
            self.assertEqual(avatar.getpixel((0, 0))[3], 0)

    def test_daily_roll_and_every_ten_downloads_are_persistent(self):
        today = date(2026, 7, 22)
        with tempfile.TemporaryDirectory() as appdata, patch.dict(os.environ, {"APPDATA": appdata}):
            store = SettingsStore("XomacitoGachaTest")
            controller = CatGachaController(
                ROOT,
                store,
                rng=random.Random(2911),
                today_provider=lambda: today,
            )
            self.assertTrue(controller.state["dailyAvailable"])
            self.assertEqual(controller.state["unlockedCount"], 1)

            controller.recordSuccessfulDownloads(9)
            self.assertEqual(controller.state["downloadProgress"], 9)
            self.assertEqual(controller.state["earnedRolls"], 0)
            controller.recordSuccessfulDownloads(1)
            self.assertEqual(controller.state["downloadProgress"], 0)
            self.assertEqual(controller.state["earnedRolls"], 1)

            daily = controller.roll()
            self.assertTrue(daily["isNew"])
            self.assertFalse(controller.state["dailyAvailable"])
            self.assertEqual(controller.state["earnedRolls"], 1)
            earned = controller.roll()
            self.assertTrue(earned["isNew"])
            self.assertEqual(controller.state["earnedRolls"], 0)
            self.assertEqual(controller.roll(), {})

            controller.equip(earned["catId"])
            restored = CatGachaController(
                ROOT,
                SettingsStore("XomacitoGachaTest"),
                rng=random.Random(2),
                today_provider=lambda: today,
            )
            self.assertEqual(restored.state["equippedId"], earned["catId"])
            self.assertEqual(restored.state["unlockedCount"], 3)
            self.assertFalse(restored.state["dailyAvailable"])

    def test_server_authorized_signup_rolls_are_added_and_persisted(self):
        today = date(2026, 8, 21)
        with tempfile.TemporaryDirectory() as appdata, patch.dict(os.environ, {"APPDATA": appdata}):
            store = SettingsStore("XomacitoEmailBonusTest")
            controller = CatGachaController(ROOT, store, today_provider=lambda: today)

            controller.grantBonusRolls(10)
            self.assertEqual(controller.state["earnedRolls"], 10)

            restored = CatGachaController(
                ROOT,
                SettingsStore("XomacitoEmailBonusTest"),
                today_provider=lambda: today,
            )
            self.assertEqual(restored.state["earnedRolls"], 10)

    def test_duplicate_rolls_after_platinum_upgrade_a_visible_persistent_aura(self):
        today = date(2026, 8, 21)

        class FirstCatRng:
            def choices(self, values, weights, k):
                return [values[0]]

            def choice(self, values):
                return values[0]

        with tempfile.TemporaryDirectory() as appdata, patch.dict(os.environ, {"APPDATA": appdata}):
            store = SettingsStore("XomacitoAuraUpgradeTest")
            controller = CatGachaController(
                ROOT, store, rng=FirstCatRng(), today_provider=lambda: today,
            )
            controller._unlocked = set(controller._by_id)
            controller._last_daily_roll = today.isoformat()
            controller._earned_rolls = 2
            controller._refresh()
            controller._persist()

            first = controller.roll()
            second = controller.roll()
            self.assertFalse(first["isNew"])
            self.assertTrue(first["effectUpgraded"])
            self.assertEqual(first["effectLevel"], 1)
            self.assertEqual(first["effectName"], "Destello")
            self.assertEqual(second["effectLevel"], 2)
            self.assertEqual(second["effectName"], "Resplandor")
            self.assertTrue(controller.state["isPlatinum"])

            restored = CatGachaController(
                ROOT, SettingsStore("XomacitoAuraUpgradeTest"),
                rng=FirstCatRng(), today_provider=lambda: today,
            )
            upgraded = next(
                item for item in restored.collection.items()
                if item["catId"] == second["catId"]
            )
            self.assertEqual(upgraded["duplicateCount"], 2)
            self.assertEqual(upgraded["effectLevel"], 2)
            self.assertEqual(upgraded["effectName"], "Resplandor")

    def test_six_star_cat_emits_custom_unlock_and_equip_animation(self):
        today = date(2026, 7, 28)

        class SixStarRng:
            def choices(self, rarities, weights, k):
                self.weights = dict(zip(rarities, weights))
                return [6]

            def choice(self, values):
                return values[0]

        with tempfile.TemporaryDirectory() as appdata, patch.dict(os.environ, {"APPDATA": appdata}):
            rng = SixStarRng()
            controller = CatGachaController(
                ROOT,
                SettingsStore("XomacitoSixStarGachaTest"),
                rng=rng,
                today_provider=lambda: today,
            )
            equipped = []
            controller.equippedRequested.connect(lambda result: equipped.append(dict(result)))
            result = controller.roll()

            self.assertEqual(result["name"], "BLACK BULL")
            self.assertEqual(result["rarity"], 6)
            self.assertEqual(result["stars"], "★★★★★★")
            self.assertEqual(result["animationStyle"], "blackbull-noir")
            self.assertAlmostEqual(rng.weights[6], 0.2)

            controller.equip(result["catId"])
            self.assertEqual(equipped[0]["animationStyle"], "blackbull-noir")
            self.assertEqual(controller.state["equippedRarity"], 6)

    def test_only_unique_media_sources_advance_download_progress(self):
        today = date(2026, 7, 28)
        with tempfile.TemporaryDirectory() as appdata, patch.dict(os.environ, {"APPDATA": appdata}):
            store = SettingsStore("XomacitoUniqueGachaTest")
            controller = CatGachaController(ROOT, store, today_provider=lambda: today)

            controller.recordSuccessfulSource("youtube:video-a")
            controller.recordSuccessfulSource("youtube:video-a")
            controller.recordSuccessfulSource("youtube:video-b")
            self.assertEqual(controller.state["downloadProgress"], 2)
            self.assertEqual(controller.state["totalDownloads"], 2)

            restored = CatGachaController(
                ROOT,
                SettingsStore("XomacitoUniqueGachaTest"),
                today_provider=lambda: today,
            )
            restored.recordSuccessfulSource("youtube:video-a")
            self.assertEqual(restored.state["downloadProgress"], 2)
            restored.recordSuccessfulSource("youtube:video-c")
            self.assertEqual(restored.state["downloadProgress"], 3)

    def test_smooth_motion_reward_unlocks_black_bull_once_and_persists(self):
        today = date(2026, 8, 1)
        with tempfile.TemporaryDirectory() as appdata, patch.dict(os.environ, {"APPDATA": appdata}):
            store = SettingsStore("XomacitoBlackBullRewardTest")
            controller = CatGachaController(ROOT, store, today_provider=lambda: today)

            first = controller.unlockPromotionalCat("BLACK BULL")
            self.assertEqual(first["name"], "BLACK BULL")
            self.assertEqual(first["rarity"], 6)
            self.assertEqual(first["animationStyle"], "blackbull-noir")
            self.assertTrue(first["isNew"])
            self.assertTrue(first["themeUnlocked"])

            repeated = controller.unlockPromotionalCat("BLACK BULL")
            self.assertFalse(repeated["isNew"])
            self.assertEqual(controller.state["unlockedCount"], 2)

            restored = CatGachaController(
                ROOT,
                SettingsStore("XomacitoBlackBullRewardTest"),
                today_provider=lambda: today,
            )
            self.assertEqual(restored.state["unlockedCount"], 2)

    def test_zane_birthday_reward_is_exclusive_to_august_26_and_idempotent(self):
        current_day = [date(2026, 8, 25)]
        with tempfile.TemporaryDirectory() as appdata, patch.dict(os.environ, {"APPDATA": appdata}):
            store = SettingsStore("XomacitoZaneBirthdayTest")
            controller = CatGachaController(
                ROOT, store, rng=random.Random(2911), today_provider=lambda: current_day[0],
            )
            dog = next(cat for cat in controller.catalog if cat.name == "PERRO ZANE")
            self.assertTrue(dog.exclusive)
            self.assertNotIn(dog.id, controller._unlocked)
            self.assertNotIn(dog.id, {item["catId"] for item in controller.collection.items()})
            self.assertEqual(controller.claimZaneBirthdayReward(), {})

            current_day[0] = date(2026, 8, 26)
            reward = controller.claimZaneBirthdayReward()
            self.assertEqual(reward["rewardRolls"], 10)
            self.assertEqual(reward["cat"]["name"], "PERRO ZANE")
            self.assertTrue(reward["cat"]["isNew"])
            self.assertEqual(controller.state["earnedRolls"], 10)
            self.assertIn(dog.id, controller._unlocked)
            self.assertEqual(controller.claimZaneBirthdayReward(), {})
            self.assertEqual(controller.state["earnedRolls"], 10)

            restored = CatGachaController(
                ROOT, SettingsStore("XomacitoZaneBirthdayTest"), today_provider=lambda: current_day[0],
            )
            self.assertEqual(restored.claimZaneBirthdayReward(), {})
            self.assertIn(dog.id, restored._unlocked)
            self.assertEqual(restored.state["earnedRolls"], 10)

            current_day[0] = date(2026, 8, 27)
            self.assertEqual(restored.claimZaneBirthdayReward(), {})


if __name__ == "__main__":
    unittest.main()
