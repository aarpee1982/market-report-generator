# Market Report Generator

Fully autonomous market research report generator. Enter a title, get a Word file.

---

## What it does

1. You enter a market title (e.g. "Global Hydrogen Fuel Cell Market")
2. GPT-4.5 acts as a senior analyst and generates all market numbers
3. GPT-4.5 writes every section in the exact FMI report format
4. The app assembles a formatted Word document and gives you a download link

---

## Deploy on Streamlit Cloud (free, works on phone)

This is the easiest path. No server to manage, accessible from any device.

### Step 1: Create a GitHub account
Go to https://github.com and sign up (free).

### Step 2: Create a new repository
- Click the + icon → "New repository"
- Name it: `market-report-generator`
- Set it to Public
- Click "Create repository"

### Step 3: Upload these files to the repository
Upload all files in this folder:
- `app.py`
- `requirements.txt`
- `package.json`

(Use the "Add file → Upload files" button on GitHub)

### Step 4: Deploy on Streamlit Cloud
- Go to https://share.streamlit.io
- Sign in with your GitHub account
- Click "New app"
- Select your repository: `market-report-generator`
- Main file path: `app.py`
- Click "Deploy"

### Step 5: Install Node.js (one-time setup via packages.txt)
Create a file called `packages.txt` in your GitHub repo with just this line:
```
nodejs
npm
```
This tells Streamlit Cloud to install Node.js automatically.

### Done
Your app will be live at a URL like:
`https://your-username-market-report-generator-app-xxxxx.streamlit.app`

Open it on your phone, enter your OpenAI key and a market title, hit Generate.

---

## Run locally (optional)

```bash
pip install -r requirements.txt
npm install
streamlit run app.py
```

---

## What you need

- An OpenAI API key (from https://platform.openai.com)
- The model used is `gpt-4.5-turbo` (latest GPT-4.5)

---

## Report format produced

The Word file matches this structure exactly:

1. Intro paragraph (tagline + key market figures)
2. Report Summary
   - Market Snapshot (bullets)
   - Demand and Growth Drivers (bullets)
   - Product and Segment View (bullets)
   - Geography and Competitive Outlook (bullets)
3. Analyst Opinion (quote)
4. Market Definition
5. Market Inclusions (bullets)
6. Market Exclusions (bullets)
7. Research Methodology
8. Key Drivers / Restraints / Trends (prose)
9. Segmental Analysis (3 segments, prose each)
10. Competitive Aligners (2 paragraphs naming companies)
11. Key Players (bullet list)
12. Strategic Outlook by FMI
13. Scope of the Report (table)
14. Bibliography
15. FAQs

---

## No database needed

The app is stateless. No Supabase, no database required. Each report generation is self-contained. The OpenAI key is entered per session and never stored anywhere.
