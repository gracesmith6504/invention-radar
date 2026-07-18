"""Manual integration test — requires real Google OAuth credentials.
Run: GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... GOOGLE_REFRESH_TOKEN=... python3 tests/test_auth.py
"""
import sys
sys.path.insert(0, ".")

from lib.auth import get_access_token, clear_token_cache
from lib.google_api import google_get


def test_auth_and_api():
    token = get_access_token()
    assert token, "Got empty token"
    print(f"✓ Got access token: {token[:20]}...")

    result = google_get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        token,
    )
    print(f"✓ Authenticated as: {result.get('email', 'unknown')}")

    clear_token_cache()
    token2 = get_access_token()
    assert token2, "Second token fetch failed"
    print("✓ Token cache clear + re-fetch works")

    print("\nAll auth tests passed.")


if __name__ == "__main__":
    test_auth_and_api()
