# Interview Question Bank — Setup Guide

## 简介

一个用于整理量化面试题库的工具，支持将题目（PDF、Notebook、截图、文字等）自动上传至 **Google Drive**，并同步录入 **Notion 数据库**（按公司、轮次、题型、难度分类）。配合 **Claude Code** 的 `/add-interview` 指令，粘贴题目或拖入文件即可完成录入，无需手动填表。

---

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
pip install -r requirements.txt
```

---

## Step 2: Google Drive OAuth setup

### 2a. Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. `interview-db`)
3. Enable these APIs:
   - Google Drive API

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

## Step 3: Notion API setup

The upload script and `/add-interview` skill both write to the shared Notion DB via the Notion API. Each user needs their own **Internal Integration Token**.

### 3a. Create a Notion integration

1. Go to [notion.so/profile/integrations](https://www.notion.so/profile/integrations)
2. Click **New integration**
3. Give it a name (e.g. `interview-db`)
4. Set **Associated workspace** to the workspace that contains the shared DB
5. Under **Capabilities**, enable: **Read content**, **Update content**, **Insert content**
6. Click **Save** → copy the **Internal Integration Secret** (starts with `ntn_...`)

### 3b. Connect the integration to the shared DB

1. Open the **Quant Interview Questions** Notion page (link shared by the repo owner)
2. Click **•••** (top-right) → **Connections** → **Connect to** → find your integration name
3. Confirm — the integration now has write access to the DB

### 3c. Add your token to `.env`

```
NOTION_API_KEY=ntn_your_integration_token_here
```

---

## Step 4: Notion MCP setup (for `/add-interview` Claude skill)

The `/add-interview` skill uses the Notion MCP server to interact with Notion directly from Claude Code.

### 4a. Install Notion MCP

```bash
npm install -g @notionhq/notion-mcp-server
```

### 4b. Configure MCP in Claude Code

```bash
claude mcp add notion --command notion-mcp-server --env NOTION_API_KEY=ntn_your_token_here
```

Or manually add to `~/.claude/claude.json`:

```json
{
  "mcpServers": {
    "notion": {
      "command": "notion-mcp-server",
      "env": {
        "NOTION_API_KEY": "ntn_your_token_here"
      }
    }
  }
}
```

---

## Step 5: Install the Claude skill

```bash
mkdir -p ~/.claude/skills
cp skills/add-interview.md ~/.claude/skills/add-interview.md
```

Then add to `~/.claude/CLAUDE.md` (create if it doesn't exist):

```markdown
## Skills
- `/add-interview` → Add Interview Problems skill at `~/.claude/skills/add-interview.md`. Parses unorganized interview problems and adds them to the Notion Interview Question Bank.
```

---

## Usage

### Option A — Bulk upload from `unorganized/` folder

Drop files into the `unorganized/` folder, organized by company:

```
unorganized/
  Citadel/
    oa_problem.pdf
    solution.ipynb
  Goldman Sachs.pdf       ← single file, stem = company name
```

Then run:

```bash
python scripts/upload_unorganized.py
```

This will:
1. Upload each file to Google Drive (`Interview DB/Company/Season/Position/Round/`)
2. Create a page in the shared Notion DB with a Drive link in the body
3. Clear the `unorganized/` folder when done

To customize position/round per company, edit `COMPANY_META` in the script.
To skip a company, add it to `SKIP_COMPANIES`.

---

### Option B — Add problems via Claude (text, screenshot, PDF)

Once the skill is installed, just talk to Claude Code:

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
5. Create pages in the shared Notion DB with Drive links in the body

---

## Project structure

```
interview-db/
├── scripts/
│   └── upload_unorganized.py   # Bulk upload from unorganized/ folder
├── skills/
│   └── add-interview.md        # Claude skill (copy to ~/.claude/skills/)
├── unorganized/                # Drop files here before running upload script
├── .env                        # Your config (gitignored)
├── .env.example                # Config template
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
