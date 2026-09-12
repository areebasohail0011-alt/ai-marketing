# AI Marketing Co-Pilot - Build & Demo Guide

This is the working MVP scaffold matching the PRD's Priority 1–4 scope:
Business Input → Grok API → Business Analysis → Competitor Analysis → Market
Gaps → Positioning → Strategy → 30-Day Plan → Streamlit dashboard, with the
optional AI assistant (Priority 5) included.

Files:
- `app.py` - Streamlit UI (form + results dashboard + chat assistant)
- `pipeline.py` - orchestrates the 8-stage AI pipeline
- `prompts.py` - all prompt templates, one per stage
- `grok_client.py` - Grok/Groq API wrapper + error handling
- `requirements.txt` - dependencies

---

## Step 1 - Get an Groq (Grok) API key
1. Go to https://console.groq.com and create/sign in to an account.
2. Generate an API key.
3. Keep it secret - never paste it into code, screenshots, or git commits.

## Step 2 - Set up Google Colab
1. Open a new Colab notebook.
2. Upload the 5 project files (`app.py`, `pipeline.py`, `prompts.py`,
   `grok_client.py`, `requirements.txt`) into the Colab file system
   (drag-and-drop into the Files pane, or `git clone` your own repo).
3. In a Colab cell, install dependencies:
   ```
   !pip install -r requirements.txt -q
   ```

## Step 3 - Set your API key as an environment variable (never hard-code it)
In a Colab cell:
```python
import os
from getpass import getpass
os.environ["GROQ_API_KEY"] = getpass("Enter your Groq API key: ")
# Optional: override the default model
# os.environ["XAI_MODEL"] = "llama-3.3-70b-versatile"
```
`getpass` hides the key as you type it and keeps it out of the notebook's
saved output - safer than `os.environ["GROQ_API_KEY"] = "sk-..."` typed in plain text.

## Step 4 - Run Streamlit in the background
Streamlit needs to run as a server process; Colab cells are foreground, so
launch it in the background and pipe logs to a file:
```python
!streamlit run app.py --server.port 8501 &>/content/logs.txt &
```
Wait ~5 seconds, then check `!cat /content/logs.txt` to confirm it started
without errors (most common error here: missing package - rerun Step 2).

## Step 5 - Expose it publicly with a Cloudflare Tunnel (no API key needed)
```python
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
!chmod +x cloudflared-linux-amd64
!./cloudflared-linux-amd64 tunnel --url http://localhost:8501 &>/content/cloudflared.txt &
```
Wait ~10 seconds, then run:
```python
!grep -o 'https://.*trycloudflare.com' /content/cloudflared.txt
```
This prints your temporary public URL (e.g. `https://random-words.trycloudflare.com`).
Open it - that's your live demo link.

## Step 6 - Test the full journey before the demo
1. Open the URL from Step 5.
2. Fill in the form with the GlowSkin example from the PRD (or your own).
3. Click **🚀 Analyze My Business**.
4. Confirm all 8 sections populate: Business & Audience, Competitor
   Landscape, Competitor Analysis, Market Opportunities, Positioning,
   Marketing Strategy & Content, 30-Day Plan.
5. Try the assistant with a question like "Give me 10 Instagram Reel ideas."

## Step 7 - Rehearse the demo narrative
Follow the PRD's flow when presenting (section 21/34):
Business Owner → Business Info → AI Analysis → Competitor Intelligence →
Market Gap → Positioning → Strategy → 30-Day Plan → Actionable Recommendations.
Narrate it as: *"We turn a startup's business idea into a data-driven
marketing strategy by discovering competitors, identifying market
opportunities, and creating an actionable plan."*

---

## Troubleshooting (maps to PRD section 24)
- **"Grok API configuration is missing"** → `GROQ_API_KEY` isn't set in this
  Colab session (session state resets when the runtime restarts - redo Step 3).
- **"We couldn't complete the analysis right now"** → transient API failure
  or rate limit; click Analyze again. Check `console.groq.com` for quota/billing.
- **A section shows raw text instead of a formatted card** → the model
  didn't return valid JSON for that stage; the app falls back gracefully
  instead of crashing (see `raw_text` handling in `app.py`). Lowering
  `temperature` in `grok_client.py` or shortening the prompt can help.
- **Cloudflare URL not appearing** → wait a few more seconds and rerun the
  `grep` command; `cloudflared` can take a moment to establish the tunnel.

## What to build next, in order (matches PRD section 33)
1. ✅ Priority 1–3 are done in this scaffold (input → pipeline → strategy → plan).
2. Priority 4: polish the Streamlit UI (branding, colors, layout) once the
   core pipeline is demoed and working.
3. Priority 5: the assistant is already included - extend its prompt with
   more few-shot examples if answers feel too generic.
4. Priority 6 (What-If Simulator): add a new Streamlit tab that takes a
   hypothetical change (e.g. "target UAE instead of Pakistan") and re-runs
   `stage5`–`stage7` with that variable swapped in the business dict, then
   shows old vs. new positioning/strategy side by side.

---

## Deploying permanently: GitHub + Streamlit Community Cloud

Once you've tested via Colab + Cloudflare Tunnel and are happy with it, deploy
it permanently like this.

### Step 1 - Push the code to GitHub (WITHOUT the API key)
1. Create a new **public or private** repo on GitHub.
2. Upload all files EXCEPT `secrets.toml.example` doesn't matter (it has no
   real key in it, it's just a template) - but never create or upload a real
   `.streamlit/secrets.toml` file with your actual key in it.
3. The included `.gitignore` already blocks `.env` and `.streamlit/secrets.toml`
   from being committed if you're using `git` locally.
4. Double-check before pushing: open every file and confirm no real API key
   is pasted anywhere in the text.

### Step 2 - Deploy on Streamlit Community Cloud
1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **New app**, pick your repo, branch, and set the main file to `app.py`.
3. Click **Deploy** - it will fail at first because the API key isn't set yet. That's expected.

### Step 3 - Add your API key as a Streamlit "Secret" (this is where the key goes now)
1. On your deployed app's page, click **⋮ (Manage app)** → **Settings** → **Secrets**.
2. Paste in exactly this, with your real key:
   ```toml
   GROQ_API_KEY = "your-real-key-here"
   ```
3. Click **Save**. The app will automatically restart and pick it up -
   `grok_client.py` already checks `st.secrets` for this, no code change needed.

This is the equivalent of the `getpass()` step from Colab, just done once in
the dashboard instead of every session - and it's the correct way to keep the
key out of GitHub permanently while still being visible to your live app.

### Step 4 - Get your permanent link
Streamlit gives you a URL like `https://your-app-name.streamlit.app` - this
one doesn't expire like the Cloudflare tunnel link does, and it survives
restarts, so this is the link to share in your final pitch/demo.

---

## Do NOT do before the demo
- Do not commit `GROQ_API_KEY` to GitHub or leave it visible in Colab output
  cells you plan to share.
- Do not claim the competitor data is real-time or verified - the UI already
  shows a disclaimer; keep that framing in your pitch too (PRD section 26).
