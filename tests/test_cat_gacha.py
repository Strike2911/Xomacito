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

        self.assertEqual(len(catalog), 105)
        self.assertEqual(len(payload["cats"]), 105)
        self.assertIn("GATITO PENSATIVO", {cat.name for cat in catalog})
        self.assertIn("GATO DIOS", {cat.name for cat in catalog})
        self.assertEqual(Counter(cat.rarity for cat in catalog), {1: 46, 2: 29, 3: 17, 4: 9, 5: 4})
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


if __name__ == "__main__":
    unittest.main()
