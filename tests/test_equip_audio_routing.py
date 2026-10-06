from types import SimpleNamespace
from unittest.mock import Mock, patch
from src.ui.application import AppController


def test_secret_equip_uses_its_reveal_sound_instead_of_jet():
    app = SimpleNamespace(_play_cat_reveal=Mock())
    payload = {"catId": "halloween-hola", "rarity": 6, "animationStyle": "hola-haunting"}
    with patch("src.ui.application.play_gacha_equip_sound") as jet:
        AppController._play_cat_equip(app, payload)
        app._play_cat_reveal.assert_called_once_with(payload)
        jet.assert_not_called()


def test_regular_mythic_and_old_legendary_god_keep_their_jets():
    for cat_id, rarity in (("halloween-xomas", 6), ("cat-5f139ff978a3", 5)):
        app = SimpleNamespace(_play_cat_reveal=Mock())
        with patch("src.ui.application.play_gacha_equip_sound") as jet:
            AppController._play_cat_equip(app, {"catId": cat_id, "rarity": rarity})
            jet.assert_called_once_with(rarity)
            app._play_cat_reveal.assert_not_called()
