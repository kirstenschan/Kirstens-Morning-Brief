# Daily News Brief

A personal news dashboard that updates itself every morning at **7am Pacific** and sends a short **AI-written recap to your phone**. It starts with one topic, **AI in public accounting audit**, and you can add more topics later without touching any code.

**How it works:**
1. **GitHub Actions** wakes up at 7am Pacific and runs `fetch_news.py`.
2. For each topic in the `topics/` folder, the script pulls Google News feeds, keeps stories that match the topic's keywords, tags them by theme, and removes duplicates.
3. `recap.py` picks the stand-out new stories. **Claude** (Anthropic's AI) writes a quick take on the day and a one-line "why it matters to you" for each story. If the AI is unavailable, a simpler rule-based recap is sent instead, so you still get a message.
4. `notify.py` sends the recap to your phone through the free **ntfy** app. Each stand-out story gets a "Read" button, and tapping the notification opens your dashboard.
5. Results are saved to `data/` and committed back to the repo, where **GitHub Pages** serves the dashboard (`index.html`).

**Cost:** GitHub and ntfy are free. The AI recap costs about **1 cent per topic per day** (roughly $0.30 a month).

## Project files

| File | What it does |
|---|---|
| `topics/ai-in-audit.yaml` | Your first topic: sources, keywords, themes |
| `topics/_template.yaml` | Copy this to add a new topic |
| `config.yaml` | Shared settings: dashboard link, who the recap is for, AI model |
| `fetch_news.py` | Main job: fetch, filter, tag, save |
| `recap.py` | Picks the stand-out stories; the AI writes the recap |
| `notify.py` | Sends the push notification |
| `index.html` | The dashboard (works on phone and desktop) |
| `.github/workflows/daily.yml` | The 7am Pacific schedule |

## Setup (about 25 minutes)

### 1. Put the project on GitHub
1. Create a free account at github.com.
2. Click **New repository**. Name it `ai-audit-news` (or anything you like), set it to **Public**, and click **Create repository**.
3. Click **uploading an existing file** and drag in everything from this folder, including the `topics` folder and the hidden `.github` folder.
   - To show hidden folders: on a Mac, press **Cmd + Shift + .** in Finder. On Windows, turn on **View → Show → Hidden items**.
   - If the `.github` folder won't upload, click **Add file → Create new file**, type `.github/workflows/daily.yml` as the name, and paste in the file's contents.
4. Click **Commit changes**.

### 2. Let the job save its results
**Settings → Actions → General → Workflow permissions →** select **Read and write permissions** → **Save**.

### 3. Set up phone notifications (ntfy)
1. Install **ntfy** from the App Store or Google Play. It's free, and you don't need an account.
2. Make up a **long, random topic name**, for example `audit-brief-k7q2m9xw4t`.
   ntfy topics are like unlisted links: anyone who guesses the name can read the messages, so don't use something guessable like `kirsten-news`.
3. In the app, tap **+** and subscribe to that exact name. Allow notifications when asked.
4. In GitHub: **Settings → Secrets and variables → Actions → New repository secret**.
   Name: `NTFY_TOPIC`. Value: your topic name.

### 4. Set up the AI recap (Claude API key)
1. Sign in to the **Claude Console** at platform.claude.com. This is separate from a regular Claude chat subscription.
2. Add a small amount of API credit under **Billing**. $5 lasts many months at about a cent a day.
3. Go to **API Keys → Create Key** and copy the key. It's shown only once.
4. In GitHub, add another repository secret. Name: `ANTHROPIC_API_KEY`. Value: the key.

> Secrets are encrypted. They never appear in your code or in the public repo. Never paste the key into a file.

### 5. Turn on the dashboard
**Settings → Pages →** under *Branch*, choose `main` and `/ (root)` → **Save**. After a minute or two, it will be live at
`https://<your-username>.github.io/ai-audit-news/`

Then open `config.yaml` on GitHub (pencil icon), paste that address into `dashboard_url`, and commit. Tapping a notification will now open the dashboard.

**On your phone:** open the dashboard link, then tap **Share → Add to Home Screen** (iPhone) or **⋮ → Add to Home screen** (Android). It will open like an app.

### 6. Test it
**Actions** tab → **Daily news brief** → **Run workflow**. About a minute later you should get a notification, and the dashboard will show stories. From then on, it runs by itself every morning at 7am.

## Adding a new topic

1. Copy `topics/_template.yaml` and give the copy a short name with no spaces, such as `topics/cpa-exam.yaml`. On GitHub: open the template, copy its text, then **Add file → Create new file** and paste.
2. Fill in the name, keywords, searches, and themes. The comments in the file explain each field.
3. Commit it. The new topic appears as a **tab** on the dashboard after the next run (or click **Run workflow** to see it now). If `notify: true`, it also sends its own morning push.

To pause a topic, rename its file to start with `_` (for example `_cpa-exam.yaml`). To remove it, delete the file.

## Tuning
- **Too much noise?** Make a topic's `must_mention` lists more specific, or remove broad searches.
- **Missing a publication?** Add a source with `query: site:example.com your words`.
- **Recap tone off?** Edit `reader_profile` in `config.yaml` or `recap_focus` in the topic file. The AI reads both.
- **Cheaper AI:** set `recap_model: claude-haiku-5-5` in `config.yaml`.
- **Different time:** edit the two `cron` lines and the matching times in the "Check time" step of `daily.yml`. Cron times are in UTC.

## Running on your own computer (optional)
```bash
pip install -r requirements.txt
python fetch_news.py --no-notify   # without NTFY_TOPIC set, it prints the recap instead of sending it
python -m http.server              # then open http://localhost:8000
```

## Notes
- **The schedule is approximate.** GitHub sometimes starts scheduled jobs 5–30 minutes late at busy times.
- **7am all year.** The job is scheduled at both 14:00 and 15:00 UTC, and the time check skips whichever one isn't 7am Pacific that day.
- **Inactive repos pause.** GitHub pauses schedules in a repo with no activity for 60 days. The daily commits normally count as activity, but if the job ever stops, click **Enable workflow** on the Actions tab.
- **Recap accuracy.** The AI only sees each story's headline and snippet, and it's told not to add details beyond them. Still, open the article before you repeat anything in an interview.
