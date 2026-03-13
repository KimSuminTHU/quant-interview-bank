# Add Interview Problems Skill

Triggered when the user provides unorganized interview problems to add to the Notion DB.

## Trigger
User provides problems in any format: PDF, ZIP, text dump, screenshots, copy-paste, or typed descriptions. May say things like "이거 추가해줘", "DB에 넣어줘", "인터뷰 문제야" etc.

---

## Target Notion DB

- **DB ID**: `1ef8c511ee8048b681b6fa8a63ac9d72`
- **Data Source**: `collection://0cba59e6-e350-4e35-a7aa-90a05948cd8f`
- **Location**: 1P3A page in Notion

### DB Schema

| Property | Type | Options |
|---|---|---|
| Problem Title | TITLE | Free text |
| Company | SELECT | Dynamic — fetch DB schema to see current options. **If company not in options, add it first with `notion-update-data-source` before creating pages.** |
| Season | SELECT | 2023-2024, 2024-2025, 2025-2026 |
| Round | SELECT | OA, Interview |
| Problem Type | SELECT | Probability, Statistics, Coding, Market Making, Finance, Math |
| Sub-Category | RICH_TEXT | Free text (e.g. "Bayes", "BFS/DFS", "Markov Chain") |
| Difficulty | SELECT | Easy, Medium, Hard |
| LeetCode Ref | URL | Full LeetCode URL if applicable |
| Problem Summary | RICH_TEXT | 1-sentence summary |
| Solved | CHECKBOX | Default: unchecked |

---

## Workflow

### Step 1: Parse the input

Read all provided content (PDF text, ZIP contents, raw text, etc.) and identify individual problems. Each problem is a distinct question or problem statement.

**Extraction signals to look for:**
- Problem numbering (Problem 1, Q2, etc.)
- Section headers ([OA], [Interview], company names)
- Sub-part labels (a), (b), (c)
- LeetCode references

### Step 2: Extract metadata for each problem

For each problem, extract what's available. **Leave as null/empty if not mentioned — do NOT guess:**

| Field | How to extract |
|---|---|
| **Problem Title** | Infer a concise title from the problem content (required — always generate one) |
| **Company** | Only if explicitly stated or strongly implied. Check current DB schema options first. **If company is not in the existing options, add it using `mcp__notion__notion-update-data-source` before creating pages.** |
| **Season** | From context (e.g. "2025-2026 recruiting season", file names, dates) |
| **Round** | `OA` if labeled as online assessment / take-home. `Interview` if live interview |
| **Problem Type** | Infer from content: math/probability → Probability, regression/stats → Statistics, code → Coding, bid-ask/market → Market Making, options/bonds → Finance, pure math → Math |
| **Sub-Category** | Specific technique (e.g. "Markov Chain", "Ridge Regression", "BFS/DFS") |
| **Difficulty** | Infer: straightforward single-step → Easy, multi-step → Medium, complex/open-ended → Hard |
| **LeetCode Ref** | See Step 2.5 below |
| **Problem Summary** | 1-sentence description of the core question |

### Step 2.5: Check LeetCode availability

For every problem where Problem Type is **Coding**:

1. Based on the problem content, judge if it matches a known LeetCode problem.
   - Look for: classic algorithm patterns (two pointers, sliding window, BFS/DFS, DP, heap, trie, etc.), familiar problem structures, or explicit LeetCode number references
   - Use your training knowledge of LeetCode problems — do NOT web search

2. If a match is found, set `LeetCode Ref` to the full URL: `https://leetcode.com/problems/[slug]/`

3. Common mappings already in use (do not re-verify):
   - Number of Islands → `/problems/number-of-islands/`
   - Valid Parentheses → `/problems/valid-parentheses/`
   - Merge k Sorted Lists → `/problems/merge-k-sorted-lists/`
   - Best Time to Buy and Sell Stock → `/problems/best-time-to-buy-and-sell-stock/`
   - LeetCode 53 → `/problems/maximum-subarray/`
   - LeetCode 300 → `/problems/longest-increasing-subsequence/`
   - etc.

4. For non-Coding problems (Probability, Statistics, Finance, etc.) → skip, leave `LeetCode Ref` empty.

### Step 3: Confirm with user (if multiple problems or ambiguous)

If more than 5 problems, briefly list what was found:
```
찾은 문제 X개:
1. [Title] — [Company if known] / [Type] / [Difficulty]
2. ...
추가할까요?
```

For 1-3 problems, proceed directly without confirmation.

### Step 3.5: Upload files to Google Drive (if local files provided)

If the user provides local file paths (e.g. `.pdf`, `.ipynb`, `.csv`, `.zip`, `.docx`):

1. Use the Python script to upload files to Drive and get shareable links:
```bash
cd /Users/suminkim/LinqAlpha
.venv/bin/python3 - <<'EOF'
import pickle, mimetypes
from pathlib import Path
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_PATH = Path(".google_token.pickle")
with open(TOKEN_PATH, "rb") as f:
    creds = pickle.load(f)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

drive = build("drive", "v3", credentials=creds)

# Get Interview DB root folder
res = drive.files().list(
    q="name='Interview DB' and mimeType='application/vnd.google-apps.folder' and 'root' in parents and trashed=false",
    fields="files(id)"
).execute()
root_id = res["files"][0]["id"]

# Upload file — change path/company/season/position/round as needed
local_path = Path("REPLACE_WITH_FILE_PATH")
company = "REPLACE_COMPANY"
season = "REPLACE_SEASON"   # e.g. "2025-2026"
position = "REPLACE_POSITION"
round_ = "REPLACE_ROUND"    # "OA" or "Interview"

def find_or_create(name, parent):
    safe = name.replace("'", "\\'")
    r = drive.files().list(
        q=f"name='{safe}' and mimeType='application/vnd.google-apps.folder' and '{parent}' in parents and trashed=false",
        fields="files(id)"
    ).execute()
    if r["files"]: return r["files"][0]["id"]
    return drive.files().create(
        body={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent]},
        fields="id"
    ).execute()["id"]

cid = find_or_create(company, root_id)
sid = find_or_create(season, cid)
pid = find_or_create(position, sid)
rid = find_or_create(round_, pid)

mime, _ = mimetypes.guess_type(str(local_path))
mime = mime or "application/octet-stream"
f = drive.files().create(
    body={"name": local_path.name, "parents": [rid]},
    media_body=MediaFileUpload(str(local_path), mimetype=mime, resumable=True),
    fields="id,webViewLink"
).execute()
print(f["webViewLink"])
EOF
```

2. The script prints the Drive `webViewLink` — save it as `drive_link`.
3. If multiple files → run per file, collect all links.

### Step 4: Add to Notion DB

For each problem:

1. **Create DB row** using `mcp__notion__notion-create-pages`:
```json
{
  "parent": {"database_id": "1ef8c511ee8048b681b6fa8a63ac9d72"},
  "properties": {
    "Problem Title": {"title": [{"text": {"content": "<title>"}}]},
    "Company": {"select": {"name": "<company>"}},
    "Season": {"select": {"name": "<season>"}},
    "Round": {"select": {"name": "<round>"}},
    "Problem Type": {"select": {"name": "<type>"}},
    "Sub-Category": {"rich_text": [{"text": {"content": "<sub-category>"}}]},
    "Difficulty": {"select": {"name": "<difficulty>"}},
    "LeetCode Ref": {"url": "<url>"},
    "Problem Summary": {"rich_text": [{"text": {"content": "<summary>"}}]}
  }
}
```
Omit any property where value is unknown/empty.

2. **Update page body** using `mcp__notion__notion-update-page` with `replace_content`:
   - Write the full problem statement exactly as provided
   - Preserve all sub-parts (a), (b), (c)
   - Use clean markdown formatting
   - **If Drive file(s) were uploaded**, append at the bottom:
     ```
     ---
     📎 Files
     - [filename](drive_link)
     - [filename2](drive_link2)
     ```

### Step 5: Report results

```
✅ X개 문제 추가 완료

1. [Title] → [Company] / [Round] / [Type] / [Difficulty]
2. ...

DB: https://www.notion.so/1ef8c511ee8048b681b6fa8a63ac9d72
```

---

## Format Notes

- If input is a **PDF**: extract text, parse problems from the text
- If input is a **ZIP**: unzip, read each file, parse problems from each
- If input is **raw text / paste**: parse directly
- If input is **image/screenshot**: read text from image, then parse
- Problems may be in Korean or English — handle both
- If `[OA]` / `[Interview]` tags are present, use them for Round
- Company names may appear in Korean: 씨타델=Citadel, 포인트72=Point72, etc.

---

## Example

**Input:** "Citadel OA 문제야. X,Y~Uniform[0,1]. P(|X-Y|>0.5) 구해."

**Output:**
- Title: "Uniform Distance Probability"
- Company: Citadel
- Round: OA
- Type: Probability
- Sub-Category: Geometric Probability
- Difficulty: Easy
- Summary: "X,Y~Uniform[0,1]. Compute P(|X-Y|>0.5)."
- Body: Full problem text
