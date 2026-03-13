"""
Upload unorganized/ files to Google Drive + add Notion DB rows.

Folder structure expected:
  unorganized/
    CompanyName/          ← folder per company (name = company)
      file1.pdf
      file2.ipynb
    CompanyName.pdf       ← or a single file (stem = company)

Config: read from .env in the project root (interview-db/.env)

Usage:
  python scripts/upload_unorganized.py
"""

import json
import mimetypes
import os
import pickle
import requests
import shutil
import time
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ── Config ────────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

UNORGANIZED_ROOT  = ROOT_DIR / "unorganized"
CLIENT_SECRET     = Path(os.environ["GOOGLE_CLIENT_SECRET_PATH"])
TOKEN_PATH        = Path(os.environ["GOOGLE_TOKEN_PATH"])
PROGRESS_PATH     = ROOT_DIR / ".upload_progress.json"
ROOT_FOLDER_ID    = os.environ.get("INTERVIEW_ROOT_FOLDER_ID", "").strip()
ROOT_FOLDER_NAME  = os.environ.get("INTERVIEW_DB_FOLDER_NAME", "Interview DB")
SEASON            = os.environ.get("INTERVIEW_SEASON", "2025-2026")
NOTION_DB_ID      = os.environ["NOTION_DB_ID"]
NOTION_API_KEY    = os.environ["NOTION_API_KEY"]

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

SCOPES = [
    "https://www.googleapis.com/auth/drive",
]

# Only upload these file types (problem files, not raw data)
UPLOAD_EXTENSIONS = {".pdf", ".docx", ".doc", ".md", ".txt", ".ipynb",
                     ".png", ".jpg", ".jpeg", ".zip"}

# Skip these folders entirely
SKIP_FOLDER_NAMES = {"data", ".ipynb_checkpoints", "__MACOSX",
                     "stock_20231007", "gd3w", "mo3w", "策略项目"}

# Companies to skip entirely
SKIP_COMPANIES: set[str] = set()

# Per-company metadata overrides: {company_name: {"position": ..., "round": ...}}
# Defaults to {"position": "Quant Researcher", "round": "OA"} if not listed.
COMPANY_META: dict[str, dict] = {}

# ── Helpers ───────────────────────────────────────────────────────────────────

def retry(fn, retries=6, delay=2):
    for attempt in range(retries):
        try:
            return fn()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(delay * (2 ** attempt))

def get_credentials():
    creds = None
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)
    return creds

def load_progress():
    if PROGRESS_PATH.exists():
        with open(PROGRESS_PATH) as f:
            return json.load(f)
    return {"uploaded": {}}

def save_progress(p):
    with open(PROGRESS_PATH, "w") as f:
        json.dump(p, f, indent=2)

# ── Drive helpers ─────────────────────────────────────────────────────────────

_folder_cache: dict = {}

def find_or_create_folder(drive, name, parent_id):
    key = (name, parent_id)
    if key in _folder_cache:
        return _folder_cache[key]
    safe = name.replace("'", "\\'")
    q = (f"name='{safe}' and mimeType='application/vnd.google-apps.folder' "
         f"and '{parent_id}' in parents and trashed=false")
    res = retry(lambda: drive.files().list(q=q, fields="files(id)").execute())
    files = res.get("files", [])
    if files:
        _folder_cache[key] = files[0]["id"]
        return files[0]["id"]
    body = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    fid = retry(lambda: drive.files().create(body=body, fields="id").execute())["id"]
    _folder_cache[key] = fid
    return fid

def get_root_folder_id(drive):
    if ROOT_FOLDER_ID:
        return ROOT_FOLDER_ID
    q = (f"name='{ROOT_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' "
         f"and 'root' in parents and trashed=false")
    res = retry(lambda: drive.files().list(q=q, fields="files(id)").execute())
    return res["files"][0]["id"]

def upload_file(drive, local_path, parent_id):
    mime, _ = mimetypes.guess_type(str(local_path))
    mime = mime or "application/octet-stream"
    body = {"name": local_path.name, "parents": [parent_id]}
    media = MediaFileUpload(str(local_path), mimetype=mime, resumable=True)
    f = retry(lambda: drive.files().create(
        body=body, media_body=media, fields="id,webViewLink"
    ).execute())
    return f["webViewLink"]

# ── Notion helpers ────────────────────────────────────────────────────────────

def notion_create_page(company, position, round_, filename, stem, drive_link):
    """Create one Notion DB row with Drive link in the page body."""
    db_id = NOTION_DB_ID

    props = {
        "Problem Title": {"title": [{"text": {"content": stem}}]},
        "Season": {"select": {"name": SEASON}},
        "Round": {"select": {"name": round_}},
    }
    if company:
        props["Company"] = {"select": {"name": company}}

    body = {
        "parent": {"database_id": db_id},
        "properties": props,
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": f"Source file: {filename}"}}]
                }
            },
            {"object": "block", "type": "divider", "divider": {}},
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "📎 "}},
                        {"type": "text", "text": {"content": filename, "link": {"url": drive_link}}}
                    ]
                }
            },
        ]
    }
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=body,
        timeout=30,
    )
    res.raise_for_status()
    return res.json()["url"]

# ── File collection ───────────────────────────────────────────────────────────

def collect_problem_files(company_path):
    files = []
    if company_path.is_file():
        if company_path.suffix.lower() in UPLOAD_EXTENSIONS:
            files.append(company_path)
        return files
    for p in company_path.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_FOLDER_NAMES for part in p.parts):
            continue
        if p.name.startswith("."):
            continue
        if p.suffix.lower() in UPLOAD_EXTENSIONS:
            files.append(p)
    return files

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not UNORGANIZED_ROOT.exists():
        print(f"unorganized/ folder not found at {UNORGANIZED_ROOT}")
        return

    print("Authenticating...")
    creds = get_credentials()
    drive = build("drive", "v3", credentials=creds)
    root_id = get_root_folder_id(drive)

    progress = load_progress()
    uploaded = progress["uploaded"]

    for item in sorted(UNORGANIZED_ROOT.iterdir()):
        if item.name.startswith(".") or item.name == "__MACOSX":
            continue

        company = item.stem if item.is_file() else item.name

        if company in SKIP_COMPANIES:
            print(f"\n── {company}: skipped")
            continue

        meta     = COMPANY_META.get(company, {"position": "Quant Researcher", "round": "OA"})
        position = meta["position"]
        round_   = meta["round"]

        files = collect_problem_files(item)
        if not files:
            print(f"\n── {company}: no uploadable files, skipping")
            continue

        print(f"\n── {company} ({len(files)} files) ──")

        cid = find_or_create_folder(drive, company,  root_id)
        sid = find_or_create_folder(drive, SEASON,   cid)
        pid = find_or_create_folder(drive, position, sid)
        rid = find_or_create_folder(drive, round_,   pid)

        for f in sorted(files):
            key = str(f)
            if key in uploaded:
                print(f"  SKIP {f.name}")
                continue
            print(f"  ↑ {f.name}")
            try:
                link = upload_file(drive, f, rid)
                uploaded[key] = link
                save_progress(progress)

                notion_url = notion_create_page(company, position, round_, f.name, f.stem, link)
                print(f"  ✓ Drive + Notion → {notion_url}")
            except Exception as e:
                print(f"  ERROR {f.name}: {e}")

    # Clear unorganized folder after upload
    print("\nClearing unorganized/...")
    for item in UNORGANIZED_ROOT.iterdir():
        if item.name.startswith("."):
            continue
        try:
            if item.is_file():
                item.unlink()
            else:
                shutil.rmtree(item)
            print(f"  ✗ removed {item.name}")
        except Exception as e:
            print(f"  ERROR clearing {item.name}: {e}")

    print("\nDone!")


if __name__ == "__main__":
    main()
