import unittest
import json
from pathlib import Path
from urllib.request import Request, urlopen
from unittest.mock import Mock, patch

from src.ui.social_controller import SocialController


ROOT = Path(__file__).resolve().parents[1]


class MemorySettings:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def update(self, values):
        self.values.update(values)


class Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload if payload is not None else {}
        self.content = b"json"
        self.text = str(self.payload)

    def json(self):
        return self.payload


class SocialAuthTests(unittest.TestCase):
    def controller(self, values=None):
        return SocialController(ROOT, MemorySettings(values), Mock())

    @patch("src.ui.social_controller.requests.post")
    def test_signup_uses_real_email_and_public_username(self, post):
        post.return_value = Response(payload={"access_token": "token", "refresh_token": "refresh"})
        social = self.controller()

        result = social._signup_worker(" Papu_2911 ", " PAPU@Example.com ", "12345678")

        self.assertEqual(result["xomacito_email"], "papu@example.com")
        self.assertEqual(result["xomacito_username"], "papu_2911")
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["email"], "papu@example.com")
        self.assertEqual(body["data"], {"username": "papu_2911"})
        self.assertEqual(
            post.call_args.kwargs["params"],
            {"redirect_to": "http://localhost:3000/"},
        )

    @patch("src.ui.social_controller.requests.put")
    @patch("src.ui.social_controller.requests.post")
    def test_recovery_verifies_six_digit_code_before_updating_password(self, post, put):
        post.return_value = Response(payload={
            "access_token": "recovery-token",
            "refresh_token": "refresh-token",
            "user": {"id": "user-1", "email": "papu@example.com"},
        })
        put.return_value = Response(payload={"id": "user-1"})
        social = self.controller()

        result = social._password_reset_confirm_worker(
            "papu@example.com", "291129", "contraseña-nueva"
        )

        self.assertEqual(post.call_args.args[0], f"{social._url}/auth/v1/verify")
        self.assertEqual(
            post.call_args.kwargs["json"],
            {"email": "papu@example.com", "token": "291129", "type": "recovery"},
        )
        self.assertEqual(put.call_args.args[0], f"{social._url}/auth/v1/user")
        self.assertEqual(put.call_args.kwargs["json"], {"password": "contraseña-nueva"})
        self.assertIn("Bearer recovery-token", put.call_args.kwargs["headers"]["Authorization"])
        self.assertEqual(result["xomacito_email"], "papu@example.com")

    @patch("src.ui.social_controller.requests.post")
    def test_recovery_email_targets_the_running_local_callback(self, post):
        post.return_value = Response()
        social = self.controller()

        self.assertEqual(
            social._password_reset_request_worker("papu@example.com"),
            "papu@example.com",
        )

        self.assertEqual(post.call_args.args[0], f"{social._url}/auth/v1/recover")
        self.assertEqual(
            post.call_args.kwargs["params"],
            {"redirect_to": "http://localhost:3000/"},
        )

    @patch("src.ui.social_controller.requests.post")
    def test_email_bonus_claim_uses_the_authenticated_session(self, post):
        post.return_value = Response(payload=15)
        social = self.controller({"social_access_token": "opaque-session"})

        self.assertEqual(social._claim_signup_bonus_worker(), 15)
        self.assertEqual(
            post.call_args.args[0],
            f"{social._url}/rest/v1/rpc/claim_email_roll_reward",
        )
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Bearer opaque-session",
        )

    @patch("src.ui.social_controller.requests.post")
    def test_private_account_gift_uses_server_identity_and_rpc(self, post):
        post.return_value = Response(payload=50)
        social = self.controller({"social_access_token": "opaque-session"})

        self.assertEqual(social._claim_account_roll_gifts_worker(), 50)
        self.assertEqual(
            post.call_args.args[0],
            f"{social._url}/rest/v1/rpc/claim_account_roll_gifts",
        )
        self.assertEqual(post.call_args.kwargs["json"], {})
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Bearer opaque-session",
        )

    def test_private_account_gift_is_added_and_announced_only_when_server_returns_it(self):
        social = self.controller()
        granted = []
        notices = []
        social.signupBonusGranted.connect(granted.append)
        social.notificationRequested.connect(lambda *values: notices.append(values))

        social._account_roll_gifts_completed(0)
        social._account_roll_gifts_completed(50)

        self.assertEqual(granted, [50])
        self.assertEqual(len(notices), 1)
        self.assertIn("50", notices[0][1])
        self.assertIn("una vez", notices[0][2])

    def test_legacy_internal_email_requires_the_mandatory_upgrade(self):
        social = self.controller({"social_access_token": "session"})
        self.assertTrue(social._account_requires_recovery_email(""))
        self.assertTrue(social._account_requires_recovery_email(
            "papu@rvtoyahqxpduhrwemfyv.supabase.co"
        ))
        self.assertFalse(social._account_requires_recovery_email("papu@example.com"))

    @patch("src.ui.social_controller.requests.request")
    def test_logged_in_legacy_account_can_request_a_real_recovery_email(self, request):
        request.return_value = Response(payload={
            "email": "papu@rvtoyahqxpduhrwemfyv.supabase.co",
            "new_email": "papu@example.com",
        })
        social = self.controller({"social_access_token": "opaque-session"})

        result = social._update_recovery_email_worker("papu@example.com")

        self.assertEqual(result["requested_email"], "papu@example.com")
        self.assertEqual(request.call_args.args[0], "PUT")
        self.assertEqual(request.call_args.kwargs["json"], {"email": "papu@example.com"})
        self.assertEqual(
            request.call_args.kwargs["params"],
            {"redirect_to": "http://localhost:3000/"},
        )
        self.assertEqual(
            request.call_args.kwargs["headers"]["Authorization"],
            "Bearer opaque-session",
        )

    def test_local_callback_page_supports_email_confirmation_and_password_reset(self):
        social = self.controller()
        social.RECOVERY_CALLBACK_PORT = 0
        self.assertTrue(social._start_recovery_callback_server())
        port = social._recovery_callback_server.server_address[1]
        try:
            with urlopen(f"http://127.0.0.1:{port}/", timeout=3) as response:
                page = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertIn("Correo verificado", page)
            self.assertIn("Crea una contraseña nueva", page)
            self.assertIn('fetch("/password-reset"', page)
            self.assertIn("window.history.replaceState", page)
            self.assertNotIn("eyJ", page)
        finally:
            social.shutdown()

    @patch("src.ui.social_controller.requests.put")
    def test_local_recovery_page_changes_password_with_the_link_session(self, put):
        put.return_value = Response(payload={
            "id": "user-1",
            "email": "papu@example.com",
            "user_metadata": {"username": "papu_2911"},
        })
        social = self.controller()
        social.RECOVERY_CALLBACK_PORT = 0
        self.assertTrue(social._start_recovery_callback_server())
        port = social._recovery_callback_server.server_address[1]
        body = json.dumps({
            "access_token": "recovery-access-token",
            "refresh_token": "recovery-refresh-token",
            "password": "contraseña-nueva",
        }).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{port}/password-reset",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertTrue(payload["ok"])
            self.assertEqual(put.call_args.args[0], f"{social._url}/auth/v1/user")
            self.assertEqual(put.call_args.kwargs["json"], {"password": "contraseña-nueva"})
            self.assertEqual(
                put.call_args.kwargs["headers"]["Authorization"],
                "Bearer recovery-access-token",
            )
        finally:
            social.shutdown()

    def test_mensva_receives_the_private_51_roll_creator_gift_only_once(self):
        settings = MemorySettings({
            "social_access_token": "session",
            "social_username": "mensva",
        })
        social = SocialController(ROOT, settings, Mock())
        granted = []
        notices = []
        social.signupBonusGranted.connect(granted.append)
        social.notificationRequested.connect(lambda *values: notices.append(values))

        social.claimCreatorGiftIfEligible()
        social.claimCreatorGiftIfEligible()

        self.assertEqual(granted, [51])
        self.assertEqual(len(notices), 1)
        self.assertIn("mensva", notices[0][1].lower())
        self.assertIn("no necesitas", notices[0][2].lower())

    def test_private_creator_gift_is_invisible_to_everyone_else(self):
        social = self.controller({
            "social_access_token": "session",
            "social_username": "strike",
        })
        granted = []
        notices = []
        social.signupBonusGranted.connect(granted.append)
        social.notificationRequested.connect(lambda *values: notices.append(values))

        social.claimCreatorGiftIfEligible()

        self.assertEqual(granted, [])
        self.assertEqual(notices, [])

    def test_collection_merge_restores_remote_cats_on_a_fresh_pc(self):
        social = self.controller()
        merged = social._merge_collection_states(
            {
                "unlockedIds": ["starter"],
                "equippedId": "starter",
                "totalRolls": 0,
                "duplicates": {},
            },
            {
                "unlockedIds": ["starter", "gato-strike"],
                "equippedId": "gato-strike",
                "totalRolls": 12,
                "duplicates": {"gato-strike": 2},
            },
        )

        self.assertEqual(merged["unlockedIds"], ["gato-strike", "starter"])
        self.assertEqual(merged["equippedId"], "gato-strike")
        self.assertEqual(merged["duplicates"], {"gato-strike": 2})
        self.assertEqual(merged["totalRolls"], 12)

    def test_collection_merge_keeps_the_newer_lower_roll_balance(self):
        social = self.controller()
        merged = social._merge_collection_states(
            {
                "schema": 4,
                "unlockedIds": ["starter", "new-cat"],
                "equippedId": "new-cat",
                "earnedRolls": 8,
                "totalRolls": 7,
                "rollBalanceRevision": 107,
            },
            {
                "schema": 4,
                "unlockedIds": ["starter"],
                "equippedId": "starter",
                "earnedRolls": 10,
                "totalRolls": 5,
                "rollBalanceRevision": 105,
            },
        )

        self.assertEqual(merged["earnedRolls"], 8)
        self.assertEqual(merged["rollBalanceRevision"], 107)
        self.assertEqual(merged["totalRolls"], 7)
        self.assertEqual(merged["unlockedIds"], ["new-cat", "starter"])

    @patch("src.ui.social_controller.requests.post")
    @patch("src.ui.social_controller.requests.get")
    def test_collection_sync_downloads_merges_and_upserts_private_state(self, get, post):
        get.side_effect = [
            Response(payload=[{"state": {
                "unlockedIds": ["remote-cat"], "equippedId": "remote-cat", "totalRolls": 4,
            }}]),
            Response(payload=[{"cats_count": 149}]),
        ]
        post.return_value = Response(status_code=201)
        social = self.controller({
            "social_access_token": "opaque-session",
            "social_user_id": "0f3a93dd-3c31-4ca4-9f6c-8aec3d15c7f9",
        })

        merged = social._collection_sync_worker({
            "unlockedIds": ["starter"], "equippedId": "starter", "totalRolls": 0,
        })

        self.assertEqual(merged["unlockedIds"], ["remote-cat", "starter"])
        self.assertEqual(merged["equippedId"], "remote-cat")
        self.assertEqual(merged["historicalUnlockedCount"], 149)
        self.assertEqual(get.call_count, 2)
        self.assertIn("Bearer opaque-session", get.call_args_list[0].kwargs["headers"]["Authorization"])
        self.assertEqual(
            get.call_args_list[1].kwargs["params"],
            {"id": "eq.0f3a93dd-3c31-4ca4-9f6c-8aec3d15c7f9", "select": "cats_count", "limit": "1"},
        )
        self.assertEqual(post.call_args.kwargs["params"], {"on_conflict": "user_id"})
        self.assertEqual(post.call_args.kwargs["json"]["state"], merged)


if __name__ == "__main__":
    unittest.main()
