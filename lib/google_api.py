import json
import urllib.request
import urllib.error


def google_get(url: str, token: str) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")

    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def google_post(url: str, token: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def google_patch(url: str, token: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="PATCH")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())
