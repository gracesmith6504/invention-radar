import json
import urllib.request
import urllib.error
import uuid


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


def drive_upload_or_update(token: str, file_path: str, name: str, mime_type: str,
                           folder_id: str | None = None, file_id: str | None = None) -> dict:
    with open(file_path, "rb") as f:
        file_data = f.read()

    if file_id:
        url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=multipart"
        method = "PATCH"
        metadata = {"name": name}
    else:
        url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
        method = "POST"
        metadata = {"name": name}
        if folder_id:
            metadata["parents"] = [folder_id]

    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", f"multipart/related; boundary={boundary}")

    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def drive_find_file(token: str, name: str, folder_id: str | None = None) -> str | None:
    query = f"name='{name}' and trashed=false"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    url = f"https://www.googleapis.com/drive/v3/files?q={urllib.request.quote(query)}&fields=files(id)"
    result = google_get(url, token)
    files = result.get("files", [])
    return files[0]["id"] if files else None
