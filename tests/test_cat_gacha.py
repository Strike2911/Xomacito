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

        self.assertEqual(len(catalog), 144)
        self.assertEqual(len(payload["cats"]), 144)
        self.assertIn("GATITO PENSATIVO", {cat.name for cat in catalog})
        self.assertIn("GATO DIOS", {cat.name for cat in catalog})
        self.assertIn("GATO XOMACITO", {cat.name for cat in catalog})
        self.assertEqual(
            Counter(cat.rarity for cat in catalog),
            {1: 61, 2: 36, 3: 28, 4: 9, 5: 7, 6: 3},
        )
        expected_rarities = {
            "GATO DIOS": 5,
            "GATO DETECTIVE": 5,
            "GATO RARO": 3,
            "GATO PIXELART": 5,
            "JORGE": 3,
            "GATO CONDUCTOR": 3,
            "GATO INTELIGENTE": 3,
            "GATO MAGO": 6,
            "GATO PLAYERA": 6,
            "GATO ZARKING": 6,
        }
        by_name = {cat.name.casefold(): cat for cat in catalog}
        for name, rarity in expected_rarities.items():
            self.assertEqual(by_name[name.casefold()].rarity, rarity)
        self.assertEqual(by_name["gato mago"].animation_style, "arcane-mage")
        self.assertEqual(by_name["gato playera"].animation_style, "playera-prismatic")
        self.assertEqual(by_name["gato zarking"].animation_style, "zarking-cyber")
        self.assertTrue(all(cat.name == cat.name.upper() for cat in catalog))
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

            self.assertEqual(result["name"], "GATO MAGO")
            self.assertEqual(result["rarity"], 6)
            self.assertEqual(result["stars"], "★★★★★★")
            self.assertEqual(result["animationStyle"], "arcane-mage")
            self.assertAlmostEqual(rng.weights[6], 0.2)

            controller.equip(result["catId"])
            self.assertEqual(equipped[0]["animationStyle"], "arcane-mage")
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


if __name__ == "__main__":
    unittest.main()
