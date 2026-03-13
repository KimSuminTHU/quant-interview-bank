# Interview Question Bank — Setup Guide

Personal quant interview question tracker using **Notion** (DB) + **Google Drive** (files) + **Claude Code** (skill for adding problems).

---

## What This Does

- Notion database as the master question bank (searchable, filterable by company/round/type/difficulty)
- Google Drive stores raw files (PDFs, notebooks, ZIPs) linked from Notion pages
- `/add-interview` Claude skill lets you add new problems in seconds — just paste text, drop a file, or show a screenshot

---

## Prerequisites

- [Claude Code](https://claude.ai/code) installed (`npm install -g @anthropic-ai/claude-code`)
- A Google account with access to Google Drive
- A Notion account with access to the shared workspace
- Python 3.9+ with `pip`

---

## Step 1: Clone & install Python deps

```bash
git clone <this-repo>
cd interview-db
python3 -m venv .venv
source .venv/bin/activate
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

---

## Step 2: Google Drive / Sheets OAuth setup

### 2a. Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. `interview-db`)
3. Enable these APIs:
   - Google Drive API
   - Google Sheets API
   - Google Docs API

### 2b. Create OAuth credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Download the JSON → rename to `client_secret.json` and place in the project root

### 2c. Add yourself as a test user (while app is in testing mode)

1. Go to **APIs & Services → OAuth consent screen**
2. Under **Test users**, add your Google account email

### 2d. First-time auth

Run any script once to trigger the browser OAuth flow:

```bash
.venv/bin/python3 scripts/interview_drive_setup.py
```

This creates `.google_token.pickle` in the project root — keep this file private (it's in `.gitignore`).

---

## Step 3: Notion MCP setup

The `/add-interview` skill uses the Notion MCP server to write directly to the DB.

### 3a. Install Notion MCP

```bash
npm install -g @notionhq/notion-mcp-server
```

### 3b. Get your Notion integration token

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Create a new integration → copy the **Internal Integration Token**
3. In the Notion workspace, open the **Interview Question Bank** database → **Share** → invite your integration

### 3c. Configure MCP in Claude Code

Add to your `~/.claude/claude.json` (or run `claude mcp add`):

```json
{
  "mcpServers": {
    "notion": {
      "command": "notion-mcp-server",
      "env": {
        "NOTION_API_KEY": "your_integration_token_here"
      }
    }
  }
}
```

Or via CLI:
```bash
claude mcp add notion --command notion-mcp-server --env NOTION_API_KEY=secret_xxx
```

---

## Step 4: Install the Claude skill

Copy the skill file to your Claude skills directory:

```bash
mkdir -p ~/.claude/skills
cp skills/add-interview.md ~/.claude/skills/add-interview.md
```

Then register it in `~/.claude/CLAUDE.md` (create if it doesn't exist):

```markdown
## Skills
- `/add-interview` → Add Interview Problems skill at `~/.claude/skills/add-interview.md`. Parses unorganized interview problems and adds them to the Notion Interview Question Bank.
```

### 4a. Update the skill config for your setup

Open `~/.claude/skills/add-interview.md` and update:

| Field | Where to change | What to put |
|---|---|---|
| Notion DB ID | `## Target Notion DB` section | Your DB's ID from the URL |
| Data Source ID | same section | From `notion-fetch` on your DB |
| Drive project root | Step 3.5 script | Path to your project |
| `venv` path | Step 3.5 script | Path to your `.venv` |

---

## Step 5: Duplicate the Notion DB

1. Open the shared Notion page → **Duplicate** into your own workspace
2. The DB will have a new ID — update it in the skill file (Step 4a above)
3. You can add your own companies to the `Company` select field

---

## Usage

Once set up, just talk to Claude:

```
"Citadel OA 문제야. X,Y~Uniform[0,1]. P(|X-Y|>0.5) 구해."
```

```
"이 파일 추가해줘" + drag in a PDF/notebook
```

```
"MS R1 문제들이야: [paste screenshot or text]"
```

Claude will:
1. Parse all problems from the input
2. Infer company, round, type, difficulty, sub-category
3. Check if any coding problems match LeetCode
4. Upload any attached files to Google Drive
5. Create pages in Notion DB with Drive links in the body

---

## Project structure

```
interview-db/
├── scripts/
│   ├── interview_drive_setup.py   # Initial bulk upload from CSV
│   ├── upload_unorganized.py      # Upload loose files to Drive + add Sheet rows
│   └── backfill_sheet_rows.py     # Add Sheet rows for files already in Drive
├── skills/
│   └── add-interview.md           # Claude skill (copy to ~/.claude/skills/)
├── client_secret.json             # OAuth credentials (DO NOT commit — gitignored)
├── .google_token.pickle           # OAuth token (DO NOT commit — gitignored)
└── README.md
```

---

## .gitignore

Make sure these are gitignored:

```
client_secret*.json
.google_token.pickle
.upload_unorganized_progress.json
.venv/
__pycache__/
```

---

## Notion DB Schema

| Property | Type | Notes |
|---|---|---|
| Problem Title | Title | Required |
| Company | Select | Add new companies via Notion or `notion-update-data-source` |
| Season | Select | e.g. `2025-2026` |
| Round | Select | `OA` or `Interview` |
| Problem Type | Select | Probability, Statistics, Coding, Market Making, Finance, Math |
| Sub-Category | Text | e.g. "Markov Chain", "BFS/DFS" |
| Difficulty | Select | Easy, Medium, Hard |
| LeetCode Ref | URL | Auto-filled by skill for known problems |
| Problem Summary | Text | 1-sentence summary |
| Solved | Checkbox | Track your progress |
