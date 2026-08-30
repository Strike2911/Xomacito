import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.core.daily_icon import daily_cat_assets
from src.ui.download_controller import DownloadController, editor_mp4_fallback_options, reveal_in_file_manager
from src.ui.media_logic import build_media_choices, is_editor_mp4_selection, normalize_info, preferred_merge_container
from src.ui.application import normalize_clipboard_url
from src.ui.presets import ALPHA_PRESET, BUILT_IN_PRESETS, resolve_recode_parameters
from src.ui.settings_store import SettingsStore
from src.ui.social_controller import SocialController
from src.ui.theme import ThemeController


ROOT = Path(__file__).resolve().parents[1]


class QtMigrationTests(unittest.TestCase):
    def test_scoreboard_exposes_progress_podium_and_activity_streaks(self):
        qml = (ROOT / "src/ui/qml/pages/ScoreboardPage.qml").read_text(encoding="utf-8")
        self.assertIn("La Liga de Xomacito", qml)
        self.assertIn("Tu progreso personal", qml)
        self.assertIn("PODIO DE LA SEMANA", qml)
        self.assertIn("racha diaria", qml)
        self.assertIn("activeToday", qml)
        self.assertIn("bestStreak", qml)

    def test_streak_migration_is_server_driven_and_does_not_expose_activity_dates(self):
        migration = (ROOT / "supabase/migrations/202608080002_add_activity_streaks.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("security definer", migration.lower())
        self.assertIn("actor uuid := (select auth.uid())", migration)
        self.assertIn("last_active_on = current_date - 1", migration)
        self.assertIn("revoke all on table public.profile_activity from anon, authenticated", migration)
        leaderboard_signature = migration.split("returns table", 1)[1].split(")", 1)[0]
        self.assertNotIn("last_active_on", leaderboard_signature)

    def test_social_scoreboard_uses_public_supabase_config_and_safe_ids(self):
        class MemorySettings:
            def __init__(self):
                self.values = {}

            def get(self, key, default=None):
                return self.values.get(key, default)

            def set(self, key, value):
                self.values[key] = value

            def update(self, values):
                self.values.update(values)

        social = SocialController(ROOT, MemorySettings(), object())
        email, username = social._email_for_username("  Mi..ID__Prueba  ")
        self.assertEqual(username, "mi-id-prueba")
        self.assertEqual(email, "mi-id-prueba@rvtoyahqxpduhrwemfyv.supabase.co")
        self.assertTrue(social.state["configured"])
        self.assertTrue(social._anon_key.startswith("sb_publishable_"))
        self.assertNotIn("service_role", social._anon_key)
        self.assertEqual(social._normalize_email("  Papu@Example.COM "), "papu@example.com")

    def test_email_reward_migration_is_private_idempotent_and_authenticated(self):
        migration = (ROOT / "supabase/migrations/202608210001_add_email_signup_reward.sql").read_text(
            encoding="utf-8"
        ).lower()
        self.assertIn("private.email_signup_rewards", migration)
        self.assertIn("primary key references auth.users", migration)
        self.assertIn("on conflict (user_id) do nothing", migration)
        self.assertIn("security definer", migration)
        self.assertIn("actor uuid := (select auth.uid())", migration)
        self.assertIn("revoke all on function public.claim_email_signup_bonus() from public, anon", migration)
        self.assertIn("grant execute on function public.claim_email_signup_bonus() to authenticated", migration)

        reward_upgrade = (ROOT / "supabase/migrations/202608210002_raise_email_reward_to_100.sql").read_text(
            encoding="utf-8"
        ).lower()
        self.assertIn("target_reward constant integer := 100", reward_upgrade)
        self.assertIn("for update", reward_upgrade)
        self.assertIn("return target_reward - already_awarded", reward_upgrade)
        self.assertIn("revoke all on function public.claim_email_roll_reward() from public, anon", reward_upgrade)

        reward_correction = (ROOT / "supabase/migrations/20260821091211_lower_email_reward_to_15.sql").read_text(
            encoding="utf-8"
        ).lower()
        self.assertIn("target_reward constant integer := 15", reward_correction)
        self.assertIn("for update", reward_correction)
        self.assertIn("return target_reward - already_awarded", reward_correction)
        self.assertNotIn("where rolls_awarded > 15", reward_correction)

    def test_email_account_and_recovery_controls_are_present(self):
        qml = (ROOT / "src/ui/qml/Main.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "socialEmailField"', qml)
        self.assertNotIn('objectName: "socialRecoveryCodeField"', qml)
        self.assertIn("Crear y recibir 15", qml)
        self.assertIn("requestPasswordReset", qml)
        self.assertIn("cancelPasswordReset", qml)
        self.assertIn("Enviar enlace", qml)
        self.assertIn("recoveryLinkSent", qml)
        self.assertIn("Popup.CloseOnEscape", qml)
        self.assertIn('objectName: "recoveryEmailRequiredPopup"', qml)
        self.assertIn('objectName: "recoveryAccountEmailField"', qml)
        self.assertIn("ACTUALIZACIÓN DE CUENTA OBLIGATORIA", qml)
        self.assertIn("Guardar y recibir 15", qml)
        self.assertIn("Comprobar correo", qml)

    def test_social_keeps_local_cat_count_until_an_authenticated_sync(self):
        class MemorySettings:
            def __init__(self):
                self.values = {}

            def get(self, key, default=None):
                return self.values.get(key, default)

            def set(self, key, value):
                self.values[key] = value

            def update(self, values):
                self.values.update(values)

        social = SocialController(ROOT, MemorySettings(), object())
        social.syncCatCount(14)
        self.assertEqual(social._local_cat_count, 14)

    def test_social_detects_a_token_that_needs_refreshing(self):
        def token_with_expiry(expiry):
            payload = base64.urlsafe_b64encode(
                json.dumps({"exp": expiry}).encode("utf-8")
            ).decode("ascii").rstrip("=")
            return f"header.{payload}.signature"

        self.assertTrue(SocialController._token_expiring(token_with_expiry(int(time.time()) - 1)))
        self.assertFalse(SocialController._token_expiring(token_with_expiry(int(time.time()) + 3600)))

    def test_strike_is_the_default_theme_and_legacy_name_migrates(self):
        with tempfile.TemporaryDirectory() as appdata, patch.dict(os.environ, {"APPDATA": appdata}):
            store = SettingsStore("XomacitoStrikeThemeTest")
            theme = ThemeController(ROOT, store)
            self.assertIn("Strike", theme.availableThemes)
            self.assertEqual(theme.themeName, "Strike")
            self.assertEqual(theme.colors["background"].lower(), "#0d0d0f")
            self.assertNotEqual(theme.colors["primary"].lower(), "#63718d")

            store.update({"selected_theme_accent": "codex_black", "theme_selection_explicit": True})
            migrated = ThemeController(ROOT, store)
            self.assertEqual(migrated.themeName, "Strike")
            self.assertEqual(store.get("selected_theme_accent"), "Strike")

    def test_guided_tour_is_contextual_skippable_and_repeatable(self):
        main = (ROOT / "src/ui/qml/Main.qml").read_text(encoding="utf-8")
        overlay = (ROOT / "src/ui/qml/components/TutorialOverlay.qml").read_text(encoding="utf-8")
        settings = (ROOT / "src/ui/qml/pages/SettingsPage.qml").read_text(encoding="utf-8")
        self.assertEqual(main.count('"target": "page"'), 7)
        self.assertIn('"target": "navigation"', main)
        self.assertIn('objectName: "guidedTutorialButton"', main)
        self.assertIn("onGuidedTourRequested", main)
        self.assertIn("tutorialQuietTicks < 4", main)
        self.assertIn("updatePopup.visible || noticePopup.visible", main)
        self.assertIn("|| !window.active", main)
        self.assertIn('objectName: "guidedTutorialOverlay"', overlay)
        self.assertIn("function startPage", overlay)
        self.assertIn('text: tutorial.pageOnly ? "Cerrar" : "Omitir"', overlay)
        self.assertIn("font.pixelSize: 21", overlay)
        self.assertIn("font.pixelSize: 14", overlay)
        self.assertIn("font.pixelSize: 13", overlay)
        self.assertIn('objectName: "repeatGuidedTourButton"', settings)

    def test_zane_birthday_popup_is_modal_and_blocks_the_guided_tour(self):
        main = (ROOT / "src/ui/qml/Main.qml").read_text(encoding="utf-8")
        application = (ROOT / "src/ui/application.py").read_text(encoding="utf-8")
        self.assertIn('objectName: "zaneBirthdayPopup"', main)
        self.assertIn("CELEBRACIÓN ESPECIAL · 26 DE AGOSTO", main)
        self.assertIn("+10 ROLLEOS · PERRO ZANE 5★", main)
        self.assertIn("zaneBirthdayPopup.visible", main)
        avatar = (ROOT / "src" / "ui" / "qml" / "components" / "CatAvatar.qml").read_text(
            encoding="utf-8",
        )
        self.assertIn('readonly property bool zanePortrait:', avatar)
        self.assertIn('root.zanePortrait ? avatarFrame.width * 0.15', avatar)
        self.assertIn("claimZaneBirthdayReward", application)

    def test_guided_tour_opens_advances_and_remembers_this_update(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, Q_ARG, QMetaObject, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "2.1", "4.0.2")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("mediaLibraryController", controller.media_library),
    ("settingsController", controller.config), ("catController", controller.cats),
    ("socialController", controller.social), ("presetStore", controller.presets),
    ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1280)
window.setProperty("height", 720)
tutorial = window.findChild(QObject, "guidedTutorialOverlay")
coach = window.findChild(QObject, "guidedTutorialCoachCard")
assert tutorial is not None and coach is not None
tutorial.setProperty("stepIndex", 5)
tutorial.setProperty("pageOnly", True)
assert QMetaObject.invokeMethod(tutorial, "startFull", Qt.DirectConnection)
assert tutorial.property("stepIndex") == 0
assert tutorial.property("pageOnly") is False
QTest.qWait(260)
assert bool(tutorial.property("visible")), (
    tutorial.property("opened"), tutorial.property("visible"), tutorial.property("stepIndex")
)
assert tutorial.property("stepIndex") == 0
assert float(coach.property("y")) >= 0
assert float(coach.property("y")) + float(coach.property("height")) <= 720
assert QMetaObject.invokeMethod(tutorial, "advance", Qt.DirectConnection)
QTest.qWait(80)
assert tutorial.property("stepIndex") == 1
assert QMetaObject.invokeMethod(tutorial, "omit", Qt.DirectConnection)
QTest.qWait(80)
assert tutorial.property("opened") is False
assert controller.settings.get("guided_tour_seen_version") == "4.0.2"
assert QMetaObject.invokeMethod(tutorial, "startPage", Qt.DirectConnection, Q_ARG("QVariant", 2))
QTest.qWait(80)
assert tutorial.property("pageOnly") is True
assert tutorial.property("stepIndex") == 3
assert controller.page == 2
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=25, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_selected_theme_survives_a_full_settings_restart(self):
        with tempfile.TemporaryDirectory() as appdata, patch.dict(os.environ, {"APPDATA": appdata}):
            first_store = SettingsStore("XomacitoThemePersistenceTest")
            first_theme = ThemeController(ROOT, first_store)
            first_theme.setCatThemeUnlocks(9)
            first_theme.setTheme("coffee_noir")

            second_store = SettingsStore("XomacitoThemePersistenceTest")
            second_theme = ThemeController(ROOT, second_store)
            self.assertEqual(second_theme.themeName, "coffee_noir")
            self.assertTrue(second_store.get("theme_selection_explicit"))

    def test_release_notice_does_not_open_collection_platinum_celebration(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QMetaObject, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.core.app_updater import release_notice_for_version
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "2.7")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("mediaLibraryController", controller.media_library),
    ("settingsController", controller.config),
    ("catController", controller.cats),
    ("presetStore", controller.presets), ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1280)
window.setProperty("height", 720)
controller.releaseNoticeRequested.emit(release_notice_for_version("2.7"))
QTest.qWait(650)
notice = window.findChild(QObject, "releaseNoticePopup")
platinum = window.findChild(QObject, "platinumCelebrationPopup")
assert notice is not None and notice.property("opened") is True, (
    notice, None if notice is None else notice.property("opened")
)
assert platinum is not None and platinum.property("opened") is False, (
    platinum, None if platinum is None else platinum.property("opened")
)
assert QMetaObject.invokeMethod(window, "finishReleaseNotice", Qt.DirectConnection)
QTest.qWait(900)
assert notice.property("opened") is False, notice.property("opened")
assert platinum.property("opened") is False, platinum.property("opened")
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_release_20_notice_is_styled_and_fits_1280x720(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.core.app_updater import release_notice_for_version
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "2.1")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("mediaLibraryController", controller.media_library),
    ("settingsController", controller.config),
    ("catController", controller.cats),
    ("presetStore", controller.presets), ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1280)
window.setProperty("height", 720)
controller.releaseNoticeRequested.emit(release_notice_for_version("2.1"))
QTest.qWait(650)
popup = window.findChild(QObject, "releaseNoticePopup")
splash = window.findChild(QObject, "releaseSplash")
assert popup is not None and popup.property("opened") is True
assert popup.property("y") >= 0
assert popup.property("y") + popup.property("height") <= 720
assert splash.property("text") == "LA XOMACITO KILLER UPDATE!!"
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_download_page_fits_1280x720_without_main_scroll(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QPointF, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "2.1")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("mediaLibraryController", controller.media_library),
    ("settingsController", controller.config),
    ("catController", controller.cats),
    ("presetStore", controller.presets), ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1280)
window.setProperty("height", 720)
QTest.qWait(220)

def geometry(name):
    item = window.findChild(QObject, name)
    assert item is not None, name
    point = QQuickItem.mapToScene(item, QPointF(0, 0))
    return point.y(), float(item.property("height"))

names = ["downloadSourceCard", "downloadPrimaryGrid", "downloadFooterCard", "downloadProgress"]
blocks = [geometry(name) for name in names]
for index, (y, height) in enumerate(blocks):
    assert y >= 0 and y + height <= 720.5, (names[index], y, height)
for current, following in zip(blocks, blocks[1:]):
    assert current[0] + current[1] <= following[0] + 0.5, (current, following)
assert blocks[1][1] >= 260, blocks
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_clipboard_url_validation_matches_auto_paste_contract(self):
        self.assertEqual(
            normalize_clipboard_url("  https://www.youtube.com/watch?v=xomacito  "),
            "https://www.youtube.com/watch?v=xomacito",
        )
        self.assertEqual(normalize_clipboard_url("ftp://example.test/video"), "")
        self.assertEqual(normalize_clipboard_url("texto https://example.test/video"), "")

    def test_clipboard_links_are_routed_to_the_active_page(self):
        script = r'''
from pathlib import Path
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
controller = AppController(app, Path.cwd(), "2.1")

app.clipboard().setText("https://example.test/video")
QTest.qWait(220)
assert controller.download.state["url"] == "https://example.test/video"

controller.setPage(1)
app.clipboard().setText("https://example.test/playlist")
QTest.qWait(220)
assert controller.batch.state["url"] == "https://example.test/playlist"

controller.setPage(3)
app.clipboard().setText("https://example.test/image")
QTest.qWait(220)
assert controller.image_studio.state["url"] == "https://example.test/image"

app.clipboard().setText("esto no es un enlace")
QTest.qWait(220)
assert controller.image_studio.state["url"] == "https://example.test/image"
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_qml_application_loads_offscreen(self):
        script = """
from pathlib import Path
from PySide6.QtCore import QTimer
import src.ui.application as application
application.AppController.showStartupMessages = lambda self: QTimer.singleShot(450, self.app.quit)
raise SystemExit(application.run_qt_app(Path.cwd(), '2.1'))
"""
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertNotIn("QQmlApplicationEngine failed", result.stderr)

    def test_recovery_email_prompt_is_mandatory_and_login_dialog_is_compact(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QMetaObject, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "2.1")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("mediaLibraryController", controller.media_library),
    ("settingsController", controller.config),
    ("catController", controller.cats), ("socialController", controller.social),
    ("presetStore", controller.presets), ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1280)
window.setProperty("height", 720)
controller.social._set_state(
    authenticated=True,
    needsRecoveryEmail=True,
    emailBusy=False,
    recoveryEmailUpdatePending=False,
)
assert QMetaObject.invokeMethod(window, "requestRecoveryEmailRequirement", Qt.DirectConnection)
QTest.qWait(360)
recovery = window.findChild(QObject, "recoveryEmailRequiredPopup")
field = window.findChild(QObject, "recoveryAccountEmailField")
save = window.findChild(QObject, "recoveryEmailSaveButton")
assert recovery is not None and recovery.property("opened") is True
assert field is not None and save is not None
assert float(recovery.property("height")) <= 455
QTest.keyClick(window, Qt.Key_Escape)
QTest.qWait(120)
assert recovery.property("opened") is True

assert QMetaObject.invokeMethod(recovery, "close", Qt.DirectConnection)
controller.social._set_state(authenticated=False, needsRecoveryEmail=False)
assert QMetaObject.invokeMethod(window, "requestSocialOnboarding", Qt.DirectConnection)
QTest.qWait(360)
login = window.findChild(QObject, "socialOnboardingPopup")
assert login is not None and login.property("opened") is True
login.setProperty("flow", "login")
QTest.qWait(120)
assert float(login.property("height")) <= 450
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_cat_collection_page_and_reveal_fit_1280x720(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "2.1")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("mediaLibraryController", controller.media_library),
    ("settingsController", controller.config),
    ("catController", controller.cats), ("presetStore", controller.presets),
    ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1280)
window.setProperty("height", 720)
QTest.qWait(120)
assert list(controller.pages) == [
    "Descargar", "Cola", "Biblioteca", "Estudio", "Personalización", "Scoreboard", "Configuración"
]
nav_row = window.findChild(QQuickItem, "navigationBar")
assert nav_row is not None
nav_buttons = sorted(
    [item for item in nav_row.childItems() if item.property("text") in list(controller.pages)],
    key=lambda item: float(item.property("x")),
)
assert len(nav_buttons) == 7
nav_widths = [float(button.property("width")) for button in nav_buttons]
assert max(nav_widths) - min(nav_widths) < 1.5
last_nav = nav_buttons[-1]
assert float(nav_row.property("width")) - (
    float(last_nav.property("x")) + float(last_nav.property("width"))
) < 1.5
controller.setPage(4)
QTest.qWait(650)
assert window.findChild(QObject, "catCollectionGrid") is not None
assert window.findChild(QObject, "catRollButton") is not None
personalization_button = nav_buttons[4]
assert personalization_button.property("showRollBadge") is False
controller.cats.recordSuccessfulDownloads(20)
QTest.qWait(180)
assert personalization_button.property("showRollBadge") is True
assert int(personalization_button.property("pendingCatRolls")) == 2
result = controller.cats.roll()
assert result
QTest.qWait(650)
popup = window.findChild(QObject, "catRevealPopup")
assert popup is not None and popup.property("opened") is True
assert popup.property("y") >= 0
assert popup.property("y") + popup.property("height") <= 720
card = window.findChild(QObject, "catRevealCard")
assert card is not None
assert float(card.property("width")) <= float(popup.property("width"))
assert float(card.property("height")) <= float(popup.property("height"))
QTest.qWait(1600)
assert float(popup.property("revealProgress")) > 0.99
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=25, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_black_bull_reward_is_readable_without_a_misleading_theme_badge(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "3.2")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("mediaLibraryController", controller.media_library),
    ("settingsController", controller.config),
    ("catController", controller.cats),
    ("presetStore", controller.presets), ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1280)
window.setProperty("height", 720)
QTest.qWait(180)
assert controller.page == 0
promo_avatar = window.findChild(QObject, "smoothMotionBlackBullAvatar")
assert promo_avatar is not None
assert float(promo_avatar.property("width")) >= 68
assert "cat-cf837ae651c8-avatar.webp" in str(promo_avatar.property("source"))
result = controller.claimSmoothMotionBlackBull()
assert result["name"] == "BLACK BULL" and result["themeUnlocked"] is True
QTest.qWait(3300)
popup = window.findChild(QObject, "catRevealPopup")
card = window.findChild(QObject, "catRevealCard")
equip = window.findChild(QObject, "catRevealEquipButton")
cont = window.findChild(QObject, "catRevealContinueButton")
assert popup is not None and popup.property("opened") is True
assert float(popup.property("width")) >= 600
assert float(popup.property("height")) >= 500
assert card is not None and float(card.property("width")) >= 340
assert equip is not None and equip.property("visible") is True
assert cont is not None and cont.property("visible") is True
assert controller.page == 0
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=25, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        qml = (ROOT / "src/ui/qml/pages/CatGachaPage.qml").read_text(encoding="utf-8")
        self.assertNotIn("DESBLOQUEADO CON BLACK BULL", qml)

    def test_strike_reveal_finishes_smoothly_without_the_old_reward_badge(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "1.0.5", "4.0.5")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("mediaLibraryController", controller.media_library),
    ("settingsController", controller.config), ("catController", controller.cats),
    ("socialController", controller.social), ("presetStore", controller.presets),
    ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1280)
window.setProperty("height", 720)
controller.setPage(4)
QTest.qWait(180)
cat = next(item for item in controller.cats.catalog if item.name == "GATO STRIKE")
result = controller.cats._result(cat, isNew=True, themeUnlocked=True)
controller.cats.revealRequested.emit(result)
QTest.qWait(2700)
popup = window.findChild(QObject, "catRevealPopup")
card = window.findChild(QObject, "catRevealCard")
assert popup is not None and popup.property("opened") is True
assert float(popup.property("revealProgress")) >= 0.99
assert card is not None and abs(float(card.property("rotation"))) < 0.01
assert window.findChild(QObject, "catThemeRewardBadge") is None
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_qml_controls_reach_python_controllers(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QMetaObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "2.1")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("mediaLibraryController", controller.media_library),
    ("settingsController", controller.config),
    ("catController", controller.cats),
    ("presetStore", controller.presets), ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1380)
window.setProperty("height", 850)
QTest.qWait(180)

def open_combo(item):
    point = QQuickItem.mapToScene(
        item, QPointF(item.property("width") / 2, item.property("height") / 2)
    )
    QTest.mouseClick(
        window, Qt.LeftButton, Qt.NoModifier, QPoint(round(point.x()), round(point.y()))
    )
    QTest.qWait(60)

download_mode = window.findChild(QObject, "downloadModeCombo")
assert download_mode is not None
open_combo(download_mode)
QTest.keyClick(window, Qt.Key_End)
QTest.keyClick(window, Qt.Key_Return)
QTest.qWait(120)
assert controller.download.state["mode"] == "Solo Audio"

advanced_button = window.findChild(QObject, "advancedToolsButton")
advanced_popup = window.findChild(QObject, "advancedToolsPopup")
assert advanced_button is not None and advanced_popup is not None
assert QMetaObject.invokeMethod(advanced_popup, "open", Qt.DirectConnection)
QTest.qWait(220)
assert advanced_popup.property("opened") is True
QTest.keyClick(window, Qt.Key_Escape)
QTest.qWait(180)
assert advanced_popup.property("opened") is False

trim_popup = window.findChild(QObject, "downloadTrimPopup")
trim_button = window.findChild(QObject, "openTrimButton")
trim_preview = window.findChild(QObject, "downloadTrimPreview")
volume_down = window.findChild(QObject, "trimVolumeDownButton")
volume_up = window.findChild(QObject, "trimVolumeUpButton")
folder_button = window.findChild(QObject, "trimOutputFolderButton")
assert trim_popup is not None and trim_button is not None
assert trim_preview is not None and volume_down is not None and volume_up is not None
assert folder_button is not None
assert QMetaObject.invokeMethod(trim_popup, "open", Qt.DirectConnection)
QTest.qWait(120)
assert trim_popup.property("opened") is True
QTest.keyClick(window, Qt.Key_Escape)
QTest.qWait(120)

controller.setPage(6)
QTest.qWait(120)
controller.theme.setCatThemeUnlocks(9)
theme_combo = window.findChild(QObject, "themeCombo")
assert theme_combo is not None
open_combo(theme_combo)
QTest.keyClick(window, Qt.Key_Home)
QTest.keyClick(window, Qt.Key_Down)
QTest.keyClick(window, Qt.Key_Down)
QTest.keyClick(window, Qt.Key_Down)
QTest.keyClick(window, Qt.Key_Return)
QTest.qWait(260)
assert controller.theme.themeName == "forest_moss"
assert controller.config.state["theme"] == "forest_moss"
assert controller.theme.colors["primary"].lower() == "#67875a"

probe = QQmlComponent(engine)
probe.setData(b"""import QtQuick
QtObject {
    Component.onCompleted: {
        settingsController.setValue("compactMode", true)
        downloadController.setOption("keepOriginal", false)
        batchController.setValue("fastMode", true)
        imageController.setOption("resizeEnabled", true)
    }
}""", QUrl())
probe_object = probe.create()
assert probe_object is not None, probe.errors()
QTest.qWait(80)
assert controller.config.state["compactMode"] is True
assert controller.download.options["keepOriginal"] is False
assert controller.batch.state["fastMode"] is True
assert controller.image_studio.options["resizeEnabled"] is True
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=25, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_daily_avatar_has_a_sharp_circular_ui_asset(self):
        selected = daily_cat_assets(ROOT)
        self.assertTrue(selected.ui_path.is_file())
        with Image.open(selected.ui_path) as image:
            self.assertEqual(image.size, (768, 768))
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.getpixel((0, 0))[3], 0)

    def test_black_bull_avatar_is_centered_inside_its_mythic_ring(self):
        avatar = ROOT / "assets" / "cat-collection" / "cat-cf837ae651c8-avatar.webp"
        self.assertTrue(avatar.is_file())
        with Image.open(avatar) as image:
            rgba = image.convert("RGBA")
            self.assertEqual(rgba.size, (384, 384))
            self.assertEqual(rgba.getpixel((0, 0))[3], 0)
            bounds = rgba.getchannel("A").getbbox()
            self.assertIsNotNone(bounds)
            left, top, right, bottom = bounds
            self.assertGreaterEqual(left, 18)
            self.assertGreaterEqual(top, 22)
            self.assertLessEqual(right, 366)
            self.assertLessEqual(bottom, 370)

    def test_qml_mutation_slots_are_qvariant_compatible(self):
        for relative in (
            "src/ui/settings_controller.py", "src/ui/download_controller.py",
            "src/ui/batch_controller.py", "src/ui/image_controller.py",
            "src/ui/media_library_controller.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("@Slot(str, object)", source)
            self.assertIn('@Slot(str, "QVariant")', source)

    def test_all_seven_pages_are_persistent_and_have_tools(self):
        main = (ROOT / "src" / "ui" / "qml" / "Main.qml").read_text(encoding="utf-8")
        self.assertIn("StackLayout", main)
        self.assertIn('objectName: "platinumCelebrationPopup"', main)
        self.assertIn("¡PLATINASTE XOMACITO!", main)
        self.assertIn("platinum_duality", main)
        self.assertIn("platinumCelebration", main)
        for page in ("DownloadPage", "QueuePage", "MediaLibraryPage", "ImageStudioPage", "SettingsPage", "CatGachaPage", "ScoreboardPage"):
            self.assertEqual(main.count(page), 1)

        download = (ROOT / "src" / "ui" / "qml" / "pages" / "DownloadPage.qml").read_text(encoding="utf-8")
        self.assertNotIn('objectName: "downloadContentScroll"', download)
        advanced_popup = download.index("id: advanced")
        only_scroll = download.index("contentItem: ScrollView")
        self.assertGreater(only_scroll, advanced_popup, "Sólo las herramientas emergentes pueden desplazarse")
        for label in ("Subtítulos", "Recodificación", "Fotogramas", "Reescalado"):
            self.assertIn(label, download)
        self.assertIn('text: options.fragmentEnabled ? "Recorte ✓" : "Recortar"', download)
        self.assertIn("WaveformTrimmer", download)
        self.assertIn("PremiereTimeline", download)
        self.assertIn('objectName: "trimPremiereTimeline"', download)
        self.assertIn("trimFilmstripSource", download)
        self.assertIn("trimPreviewVideo", download)
        self.assertIn("prepareTrimFilmstrip()", download)
        self.assertIn('page.setTrimBoundary("startTime", value)', download)
        self.assertIn('page.setTrimBoundary("endTime", value)', download)
        self.assertIn("trimPopup.previewActivated = true", download)
        self.assertIn("onSeekRequested: function(value) { page.seekTrimPreview(value) }", download)
        self.assertIn("preciseClockText", download)
        self.assertIn('playbackError = "Preparando una vista previa estable…"', download)
        self.assertIn("id: trimPlaybackStartDelay", download)
        self.assertIn("trimPlaybackStartDelay.restart()", download)
        self.assertIn("trimPlayer.position = startMs", download)
        self.assertIn("property bool mediaLoadSeekPending: false", download)
        self.assertIn("if (trimPopup.mediaLoadSeekPending)", download)
        self.assertIn("Boolean(viewState.localFile) || Boolean(viewState.trimPreviewFallback)", download)
        self.assertNotIn("trimPopup.fallbackRequested && trimPopup.previewActivated", download)
        self.assertIn("muted: page.trimUserMuted", download)
        premiere = (ROOT / "src" / "ui" / "qml" / "components" / "PremiereTimeline.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "premierePlayhead"', premiere)
        self.assertIn("signal seekRequested(real value)", premiere)
        self.assertIn("id: zoomRail", premiere)
        self.assertIn("id: scrubRail", premiere)
        self.assertIn("anchors.top: zoomRail.bottom", premiere)
        self.assertIn("parent: zoomRail", premiere)
        self.assertIn("y: zoomRail.height", premiere)
        self.assertIn("property real zoomFactor: 1", premiere)
        self.assertIn("from: 1; to: 16; stepSize: 1", premiere)
        self.assertIn("sourceClipRect: root.sourceCropRect(frameProbe.sourceSize.width, frameProbe.sourceSize.height)", premiere)
        self.assertIn("id: frameProbe", premiere)
        self.assertIn("id: timeGrid", premiere)
        self.assertIn('text: "DESPLAZAR"', premiere)
        self.assertIn("id: viewportSlider", premiere)
        self.assertIn("root.panBy(direction * root.viewportDuration * 0.12)", premiere)
        self.assertIn("width: 7; height: parent.height; radius: 3.5", premiere)
        self.assertIn("property real interactivePlayhead: playhead", premiere)
        self.assertIn("root.requestScrub(root.xToTime(mouse.x))", premiere)
        self.assertIn("root.outPoint - 0.20", premiere)
        video_range = (ROOT / "src" / "ui" / "qml" / "components" / "VideoRangeSelector.qml").read_text(encoding="utf-8")
        self.assertIn('root.clock(root.inPoint) + "  —  " + root.clock(root.outPoint)', video_range)
        self.assertIn('property url fallbackSource: ""', video_range)
        self.assertIn("width: 30", video_range)
        self.assertIn("filmstripSource", video_range)
        self.assertIn("Generando fotogramas", video_range)
        waveform = (ROOT / "src" / "ui" / "qml" / "components" / "WaveformTrimmer.qml").read_text(encoding="utf-8")
        self.assertIn("acceptedModifiers: Qt.NoModifier", waveform)
        self.assertIn("Usa la rueda para acercar", waveform)
        self.assertIn("Enfocar recorte", waveform)
        self.assertIn("to: 16", waveform)
        self.assertNotIn('model: ["Fragmento",', download)
        image = (ROOT / "src" / "ui" / "qml" / "pages" / "ImageStudioPage.qml").read_text(encoding="utf-8")
        for label in ("Tamaño", "Lienzo", "Formato", "Mejora IA", "Video"):
            self.assertIn(label, image)

    def test_runtime_no_longer_depends_on_tk(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        spec = (ROOT / ".build" / "XomacitoInstaller.spec").read_text(encoding="utf-8")
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("PySide6==", requirements)
        self.assertNotIn("customtkinter", requirements.lower())
        self.assertNotIn("tkinterdnd", requirements.lower())
        self.assertNotIn("import customtkinter", main)
        self.assertIn('"PySide6.QtQuick"', spec)
        self.assertIn('"customtkinter"', spec.split("excludes=", 1)[1])

    def test_settings_are_saved_atomically_and_keep_legacy_values(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"APPDATA": directory}):
            store = SettingsStore("XomacitoTest")
            store.update({"appearance_mode": "Light", "legacy_key": {"kept": True}})
            payload = json.loads(store.path.read_text(encoding="utf-8"))
            self.assertEqual(payload["appearance_mode"], "Light")
            self.assertEqual(payload["legacy_key"], {"kept": True})
            self.assertFalse(list(store.directory.glob("*.tmp")))

    def test_media_choices_keep_video_audio_and_subtitles(self):
        info = normalize_info({
            "id": "demo", "title": "Demo", "duration": 12,
            "formats": [
                {"format_id": "v", "ext": "mp4", "vcodec": "avc1", "acodec": "none", "height": 1080, "fps": 60, "filesize": 10_000_000},
                {"format_id": "a", "ext": "m4a", "vcodec": "none", "acodec": "mp4a", "abr": 192, "filesize": 2_000_000},
            ],
            "subtitles": {"es": [{"ext": "vtt", "url": "https://example.test/es.vtt"}]},
        })
        choices = build_media_choices(info)
        self.assertTrue(choices["video"])
        self.assertTrue(choices["audio"])
        self.assertIn("es", choices["subtitles"])

    def test_mp4_download_prefers_aac_audio_and_an_mp4_merge(self):
        info = normalize_info({
            "id": "premiere", "title": "Premiere", "duration": 12,
            "formats": [
                {"format_id": "v", "ext": "mp4", "vcodec": "avc1.4d401f", "acodec": "none", "height": 1080},
                {"format_id": "opus", "ext": "webm", "vcodec": "none", "acodec": "opus", "abr": 160},
                {"format_id": "aac", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 128},
            ],
        })
        choices = build_media_choices(info)
        self.assertEqual(choices["audio"][0]["formatId"], "aac")
        self.assertTrue(choices["audio"][0]["compatible"])
        self.assertEqual(preferred_merge_container(choices["video"][0], choices["audio"][0]), "mp4")
        self.assertEqual(preferred_merge_container(choices["video"][0], choices["audio"][1]), "")

    def test_editor_mp4_is_selected_before_a_higher_resolution_webm(self):
        info = normalize_info({
            "id": "premiere-default", "title": "Premiere", "duration": 12,
            "formats": [
                {"format_id": "webm-4k", "ext": "webm", "vcodec": "vp9", "acodec": "none", "height": 2160, "fps": 60},
                {"format_id": "mp4-1080", "ext": "mp4", "vcodec": "avc1.640028", "acodec": "none", "height": 1080, "fps": 60},
                {"format_id": "opus", "ext": "webm", "vcodec": "none", "acodec": "opus", "abr": 160},
                {"format_id": "aac", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 128},
            ],
        })
        choices = build_media_choices(info)
        self.assertEqual(choices["video"][0]["formatId"], "mp4-1080")
        self.assertEqual(choices["audio"][0]["formatId"], "aac")
        self.assertTrue(is_editor_mp4_selection(choices["video"][0], choices["audio"][0]))
        self.assertEqual(preferred_merge_container(choices["video"][0], choices["audio"][0]), "mp4")
        self.assertEqual(choices["video"][1]["formatId"], "webm-4k")

    def test_webm_fallback_is_transcoded_to_h264_aac_mp4(self):
        options = editor_mp4_fallback_options({"title": "WEBM", "mode": "Video+Audio"})
        params, container = resolve_recode_parameters(options)
        joined = " ".join(params)
        self.assertEqual(container, ".mp4")
        self.assertIn("libx264", joined)
        self.assertIn("aac", joined)
        self.assertFalse(options["keep_original_file"])

        controller_source = (ROOT / "src" / "ui" / "download_controller.py").read_text(encoding="utf-8")
        process_worker = controller_source.split("def _process_worker", 1)[1].split("def _download_worker", 1)[0]
        self.assertIn('Path(input_file).suffix.lower() != ".mp4"', process_worker)
        self.assertIn("not is_editor_mp4_selection", process_worker)
        self.assertIn("editor_mp4_fallback_options(options)", process_worker)

    def test_trim_preview_reuses_a_complete_native_proxy_for_every_selection(self):
        controller = DownloadController.__new__(DownloadController)
        attempts = []

        def fake_transcode(_ffmpeg, source, target, start, duration, _headers):
            attempts.append((source, start, duration))
            if source == "https://expired.example/video.mp4":
                raise RuntimeError("HTTP 403")
            Path(target).write_bytes(b"preview")
            return str(target)

        controller._fallback_trim_preview_worker = fake_transcode

        def fake_extract(_url, options, download):
            self.assertTrue(download)
            self.assertNotIn("download_ranges", options)
            self.assertIn("height<=480", options["format"])
            self.assertEqual(options["extractor_args"]["youtube"]["player_client"], ["web_embedded"])
            output = Path(options["outtmpl"].replace("%(ext)s", "mp4"))
            output.write_bytes(b"renewed video" * 512)
            return {"id": "renewed"}

        with tempfile.TemporaryDirectory() as directory, patch(
            "src.ui.download_controller.extract_info_resilient", side_effect=fake_extract,
        ):
            target = Path(directory) / "final.mp4"
            result = controller._remote_fallback_trim_preview_worker(
                "ffmpeg", "https://www.youtube.com/watch?v=1",
                "", target,
                32.0, 75.0, {}, "18", {},
            )
            self.assertTrue(Path(result).is_file())
            self.assertNotEqual(result, str(target))

        self.assertEqual(attempts, [])

    def test_result_button_reveals_the_file_without_an_image_studio_menu(self):
        download_page = (ROOT / "src" / "ui" / "qml" / "pages" / "DownloadPage.qml").read_text(encoding="utf-8")
        self.assertIn("onClicked: downloadController.openOutput()", download_page)
        self.assertNotIn("Enviar a Estudio de Imagen", download_page)
        self.assertNotIn("sendResultToImageStudio", download_page)

        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "resultado.mp4"
            result.write_bytes(b"demo")
            with patch("src.ui.download_controller.sys.platform", "win32"), patch(
                "src.ui.download_controller.subprocess.Popen"
            ) as popen:
                self.assertTrue(reveal_in_file_manager(result))
            self.assertEqual(popen.call_args.args[0][0:2], ["explorer.exe", "/select,"])
            self.assertEqual(Path(popen.call_args.args[0][2]), result.resolve())

    def test_successful_download_opens_its_location_automatically(self):
        controller_source = (ROOT / "src" / "ui" / "download_controller.py").read_text(encoding="utf-8")
        success_handler = controller_source.split("def _operation_success", 1)[1].split("def _operation_error", 1)[0]
        self.assertIn("if completed_download:", success_handler)
        self.assertIn('self.settings.get("open_explorer_after_download", True)', success_handler)
        self.assertIn("reveal_in_file_manager(output)", success_handler)

    def test_audio_only_local_file_uses_the_real_mp3_preset(self):
        script = r'''
from pathlib import Path
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController
from src.ui.presets import resolve_recode_parameters

app = QApplication([])
controller = AppController(app, Path.cwd(), "2.5")
download = controller.download
download._set_state(preset="Archivo - H.265 Normal")
download._options["applyPreset"] = True
download._apply_local_analysis({
    "videoStreams": [],
    "audioStreams": [{"index": 0, "codec_name": "vorbis", "sample_rate": "48000"}],
    "sourceHasAlpha": False,
    "thumbnail": "",
    "duration": 1.0,
})
assert download.state["mode"] == "Solo Audio"
assert download.state["preset"] == "Audio - MP3 128kbps"
options = download._collect_process_options()
params, container = resolve_recode_parameters(options)
assert container == ".mp3", (container, options)
assert "libmp3lame" in " ".join(params)
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_new_analysis_resets_mode_preset_and_clip_defaults(self):
        script = r'''
from pathlib import Path
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController
from src.ui.media_logic import normalize_info

app = QApplication([])
controller = AppController(app, Path.cwd(), "2.5")
download = controller.download
download._set_state(mode="Solo Audio", preset="Audio - MP3 128kbps")
download._options.update({
    "fragmentEnabled": True,
    "startTime": "00:00:01",
    "endTime": "00:00:02",
})
download._apply_url_analysis(normalize_info({
    "id": "new-video",
    "extractor_key": "Youtube",
    "title": "Nuevo video",
    "duration": 125,
    "formats": [
        {"format_id": "v", "ext": "mp4", "vcodec": "avc1", "acodec": "none", "height": 1080},
        {"format_id": "a", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 128},
    ],
}))
assert download.state["mode"] == "Video+Audio", download.state
assert download.state["preset"] in controller.presets.videoPresets
assert download.options["fragmentEnabled"] is False
assert download.options["startTime"] == "00:00:00"
assert download.options["endTime"] == "00:02:05"
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_download_tags_choose_a_real_output_folder(self):
        script = r'''
from pathlib import Path
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
controller = AppController(app, Path.cwd(), "2.5")
download = controller.download
tags = [
    {"name": "SFX", "folder": r"C:\Media\SFX", "color": "#FF5C8A"},
    {"name": "Música", "folder": r"D:\Edicion\Musica", "color": "#22D3EE"},
]
controller.settings.set("download_tags", tags)
download._tags = download._load_download_tags()
download.tagsChanged.emit()
download.selectDownloadTag("SFX")
assert download.state["effectiveOutputPath"] == r"C:\Media\SFX"
download.selectDownloadTag("Música")
download._set_state(title="impacto")
options = download._collect_process_options()
assert download.state["effectiveOutputPath"] == r"D:\Edicion\Musica"
assert options["output_path"] == r"D:\Edicion\Musica"
assert download.state["selectedTagColor"] == "#22D3EE"
controller.batch.selectDownloadTag("SFX")
assert controller.batch.state["effectiveOutputPath"] == r"C:\Media\SFX"
controller.batch.selectDownloadTag("Música")
assert controller.batch.state["effectiveOutputPath"] == r"D:\Edicion\Musica"
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_ogg_is_really_recoded_to_mp3(self):
        script = r'''
import subprocess
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
controller = AppController(app, Path.cwd(), "2.5")
with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    source = folder / "entrada.ogg"
    subprocess.run([
        controller.download.ffmpeg.ffmpeg_path, "-y", "-f", "lavfi",
        "-i", "sine=frequency=440:duration=0.25", "-c:a", "libvorbis", str(source)
    ], check=True, capture_output=True)
    controller.download._set_state(
        localFile=str(source), outputPath=str(folder), effectiveOutputPath=str(folder), title="audio",
        mode="Solo Audio", preset="Audio - MP3 128kbps",
        selectedVideo="", selectedAudio="Audio 1",
    )
    controller.download._audio_map = {"Audio 1": {"formatId": "0"}}
    controller.download._options["applyPreset"] = True
    options = controller.download._collect_process_options()
    result = Path(controller.download._recode_file(str(source), options, False))
    assert result.suffix.lower() == ".mp3", result
    media = controller.download.ffmpeg.get_local_media_info(str(result))
    assert media["format"]["format_name"].startswith("mp3"), media["format"]
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=30, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_image_studio_drop_zone_and_output_folder_are_real(self):
        image_page = (ROOT / "src" / "ui" / "qml" / "pages" / "ImageStudioPage.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "imageStudioDropArea"', image_page)
        self.assertIn("drop.urls", image_page)
        self.assertIn("imageController.addPaths(paths)", image_page)

        controller_source = (ROOT / "src" / "ui" / "image_controller.py").read_text(encoding="utf-8")
        self.assertIn("if not configured_output.is_absolute()", controller_source)
        self.assertIn('settings.set("image_output_path", str(configured_output))', controller_source)

    def test_audio_cover_is_contextual_and_explorer_setting_is_visible(self):
        download_page = (ROOT / "src" / "ui" / "qml" / "pages" / "DownloadPage.qml").read_text(encoding="utf-8")
        settings_page = (ROOT / "src" / "ui" / "qml" / "pages" / "SettingsPage.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "embedAudioCoverSwitch"', download_page)
        self.assertIn('visible: viewState.mode === "Solo Audio" && !viewState.localFile', download_page)
        self.assertIn('objectName: "openExplorerAfterDownloadSwitch"', settings_page)
        with tempfile.TemporaryDirectory() as appdata, patch.dict(os.environ, {"APPDATA": appdata}):
            self.assertTrue(SettingsStore("XomacitoTest").get("open_explorer_after_download"))

    def test_buttons_keep_readable_text_across_hover_and_pressed_states(self):
        button = (ROOT / "src" / "ui" / "qml" / "components" / "XButton.qml").read_text(encoding="utf-8")
        self.assertIn('if (kind === "primary") return theme.colors.primaryHover', button)
        self.assertIn("readonly property color currentBackgroundColor", button)
        self.assertIn("function contrastText(backgroundColor)", button)
        self.assertIn("color: root.foregroundColor()", button)
        self.assertIn("color: root.currentBackgroundColor", button)
        self.assertIn("readonly property color currentForegroundColor", button)
        self.assertIn("hovered || down", button)

        theme = (ROOT / "src" / "ui" / "theme.py").read_text(encoding="utf-8")
        self.assertIn("hover = _mix(primary, background", theme)

    def test_library_uses_a_dedicated_favorite_control(self):
        page = (ROOT / "src" / "ui" / "qml" / "pages" / "MediaLibraryPage.qml").read_text(encoding="utf-8")
        control = (ROOT / "src" / "ui" / "qml" / "components" / "XFavoriteButton.qml").read_text(encoding="utf-8")
        self.assertGreaterEqual(page.count("XFavoriteButton {"), 2)
        self.assertIn('Accessible.name: (favorite ? "Quitar de favoritos" : "Añadir a favoritos")', control)
        self.assertIn("implicitWidth: 34", control)
        self.assertIn("favorite ? theme.colors.warning", control)

    def test_mp3_cover_is_embedded_as_an_attached_picture(self):
        script = r'''
import io
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
controller = AppController(app, Path.cwd(), "2.5")
with tempfile.TemporaryDirectory() as directory:
    audio = Path(directory) / "cancion.mp3"
    subprocess.run([
        controller.download.ffmpeg.ffmpeg_path, "-y", "-f", "lavfi",
        "-i", "sine=frequency=440:duration=0.25", "-c:a", "libmp3lame", str(audio)
    ], check=True, capture_output=True)
    payload = io.BytesIO()
    Image.new("RGB", (40, 40), "#22c9e8").save(payload, "JPEG")
    with patch("src.ui.download_controller.requests.get") as get:
        get.return_value.content = payload.getvalue()
        get.return_value.raise_for_status.return_value = None
        controller.download._embed_audio_thumbnail(str(audio), "https://example.test/cover.jpg")
    media = controller.download.ffmpeg.get_local_media_info(str(audio))
    pictures = [stream for stream in media["streams"] if stream.get("codec_type") == "video"]
    assert pictures and pictures[0].get("disposition", {}).get("attached_pic") == 1, pictures
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=30, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_invalid_argument_download_retries_with_a_windows_safe_name(self):
        script = r'''
import tempfile
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
controller = AppController(app, Path.cwd(), "2.5")
download = controller.download
with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    download._video_map = {"1080p": {"formatId": "137", "combined": False}}
    download._audio_map = {"Audio": {"formatId": "140"}}
    download._set_state(
        url="https://example.test/video", title="Título visible",
        effectiveOutputPath=str(folder), outputPath=str(folder),
        mode="Video+Audio", selectedVideo="1080p", selectedAudio="Audio",
    )
    options = download._collect_process_options()
    calls = []
    def fake_download(_url, ydl_options, _progress, _cancel):
        calls.append(dict(ydl_options))
        if len(calls) == 1:
            raise OSError(22, "Invalid argument")
        staged = Path(ydl_options["outtmpl"].replace("%(ext)s", "mp4"))
        staged.write_bytes(b"xomacito")
        return str(staged)
    with patch("src.ui.download_controller.download_media", side_effect=fake_download):
        result = Path(download._download_worker(options))
    assert len(calls) == 2, calls
    assert "xomacito-" in calls[1]["outtmpl"], calls[1]["outtmpl"]
    assert result.name == "Título visible.mp4", result
    assert result.read_bytes() == b"xomacito"
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=30, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_alpha_preset_is_prores_4444(self):
        params, container = resolve_recode_parameters(BUILT_IN_PRESETS[ALPHA_PRESET])
        joined = " ".join(params)
        self.assertEqual(container, ".mov")
        self.assertIn("prores_ks", joined)
        self.assertIn("yuva444p10le", joined)
        self.assertNotIn("profile:v 0", joined)


if __name__ == "__main__":
    unittest.main()
