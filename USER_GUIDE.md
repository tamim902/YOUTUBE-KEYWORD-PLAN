# Keyword Studio — Creator's Complete User Guide
**Advanced YouTube SEO Intelligence & Content Strategy Platform**

Welcome to **Keyword Studio**! This platform is designed specifically for YouTube creators, affiliate marketers, and content strategists to discover high-signal keyword opportunities, eliminate duplicate research, validate topics, and prepare production-ready video packages across 4 dedicated channel portfolios.

---

## 📑 Table of Contents
1. [How to Launch Keyword Studio](#1-how-to-launch-keyword-studio)
2. [Navigating Interface Modes: Simple vs. Advanced](#2-navigating-interface-modes-simple-vs-advanced)
3. [Managing the Four Channel Workspaces](#3-managing-the-four-channel-workspaces)
4. [Step-by-Step Keyword Research](#4-step-by-step-keyword-research)
5. [Understanding Keyword Metrics & Search Intent](#5-understanding-keyword-metrics--search-intent)
6. [Investigating Product & Affiliate Opportunities](#6-investigating-product--affiliate-opportunities)
7. [60-Day Competitor Content-Gap Analysis](#7-60-day-competitor-content-gap-analysis)
8. [The 1-Click SEO Content Factory](#8-the-1-click-seo-content-factory)
9. [Pre-Publish SEO Readiness Checklist](#9-pre-publish-seo-readiness-checklist)
10. [Saving, Reopening & Exporting Research](#10-saving-reopening--exporting-research)
11. [Personal Research Memory & Duplicate Alerts](#11-personal-research-memory--duplicate-alerts)
12. [Daily Action Center & Morning Opportunity Reports](#12-daily-action-center--morning-opportunity-reports)
13. [Database Backup, Restore & Data Safety](#13-database-backup-restore--data-safety)
14. [Troubleshooting Common Issues](#14-troubleshooting-common-issues)
15. [Notice on Epistemic Modesty & Truthful Metrics](#15-notice-on-epistemic-modesty--truthful-metrics)

---

## 1. How to Launch Keyword Studio

Keyword Studio runs locally on your Windows computer. It does not require a remote server.

### Option A: Double-Click Batch Launcher (Recommended for Windows)
1. Open the project folder in Windows File Explorer.
2. Double-click `run.bat`.
3. The launcher will automatically:
   - Create your `.env` configuration file from template if missing.
   - Detect or initialize your Python virtual environment (`.venv`).
   - Launch the local Streamlit application.
   - Automatically open your default web browser to `http://localhost:8501`.

### Option B: PowerShell Launcher
1. Right-click `run.ps1` and select **Run with PowerShell**, or in terminal:
   ```powershell
   .\run.ps1
   ```

### Option C: Manual Command Line
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\activate

# 2. Launch Streamlit
streamlit run app.py
```

> **Important**: Keep the terminal window open while using Keyword Studio. To stop the application safely, click into the terminal window and press `Ctrl + C`.

---

## 2. Navigating Interface Modes: Simple vs. Advanced

Keyword Studio provides two distinct modes tailored to your experience level:

- **Simple Mode (Default for Beginners)**:
  - Clean, distraction-free view with plain-English tooltips.
  - Hides technical sliders, regex filters, and advanced API quotas.
  - Presents clear next actions (`🟢 Highly Relevant`, `🔵 Worth Reviewing`).
  - Access to the **7-Step Guided Keyword Wizard**.
- **Advanced Mode (For Seasoned SEO Strategists)**:
  - Full control over crawl depth (1–5), request budget caps (10–200), and seed expansion modes.
  - Granular country and language filtering (English, Bengali, Hindi, Spanish, French, etc.).
  - Direct access to Topic Clustering, Content Pillars, and Monitor Alerts.

*You can switch between modes at any time using the mode toggle pill at the top of the sidebar.*

---

## 3. Managing the Four Channel Workspaces

Keyword Studio comes pre-configured with 4 distinct channel profiles to prevent research bleed between different content niches:

| Channel Name | Core Niche & Audience | Default Language & Country | Monetization Focus |
| :--- | :--- | :---: | :--- |
| **TechGear Pulse** (Channel 1) | Mechanical Keyboards, Desk Mats & Workspace Aesthetics | English (`en`) / US | Amazon Associates, Drop, Keychron |
| **CodeCraft বাংলা** (Channel 2) | Python Programming, Web Dev & AI Automation | Bengali (`bn`) / Bangladesh (`BD`) | Developer Tools, Tech Courses |
| **HomeChef Artisan** (Channel 3) | Artisanal Sourdough Baking & Cast Iron Cooking | English (`en`) / US | Cookware, Pantry Subscriptions |
| **FitPulse Active** (Channel 4) | Home Calisthenics, Mobility & Functional Fitness | English (`en`) / US | Home Gym Gear, Resistance Bands |

### Switching Channels
- Click the **Active Channel Selector** in the sidebar at any time.
- All subsequent searches, saved packages, research memory, and action tasks will instantly switch to that channel's dedicated workspace.
- **Zero Bleed Guarantee**: Research conducted on Channel 1 will never pollute suggestions or recommendations on Channels 2, 3, or 4.

---

## 4. Step-by-Step Keyword Research

### The 7-Step Guided Wizard
For beginners, the fastest way to research a topic is using the **Guided Wizard**:
1. **Choose a Channel**: Select which channel will publish this video.
2. **Enter a Topic**: Type your core seed concept (e.g. `mechanical keyboard under 100`).
   - *Duplicate Memory Check*: If you already researched this topic on this channel, a banner will notify you whether your previous research is fresh ($\le 30$ days) or stale ($> 30$ days).
3. **Choose Settings**: Select your search depth and region.
4. **Find Keywords**: The engine queries Google Suggest and retrieves real autocomplete predictions.
5. **Review Results**: View sorted keywords with relevance tiers and search intent.
6. **Choose Best-Fit Keyword**: Pick your target primary keyword.
7. **Next Actions**: 1-click jump to create a video package, export CSV, or schedule on calendar.

---

## 5. Understanding Keyword Metrics & Search Intent

Keyword Studio classifies every discovered keyword deterministically:

### Relevance Tiers
- `🟢 Tier 1: Core Target (Score 80–100)`: Exceptional alignment with seed topic. Prime candidates for main video titles.
- `🔵 Tier 2: Strong Supporting (Score 60–79)`: Great for secondary keyword inclusions, sub-sections, and tags.
- `🟡 Tier 3: Worth Exploring (Score 40–59)`: Niche long-tail angles or spin-off Shorts ideas.
- `⚪ Tier 4: Low Priority (Score < 40)`: Tangential phrases; keep for reference.

### Search Intent Categories
- **Informational / How-To**: Queries starting with *how to*, *guide*, *tutorial*, *steps*, or *tips*. Focus video on clear step-by-step teaching.
- **Commercial / Buyer Intent**: Queries containing *best*, *review*, *vs*, *comparison*, *top 10*, *worth it*. Ideal for product showcases and affiliate monetization.
- **Problem Solving**: Queries containing *fix*, *error*, *troubleshooting*, *not working*. High watch-time potential with urgent viewer needs.

---

## 6. Investigating Product & Affiliate Opportunities

For channels with affiliate marketing enabled:
1. Navigate to **Niche Product Opportunity Finder** in the sidebar.
2. Select your channel to load curated product catalogs aligned with your channel's niche.
3. Review candidate products with estimated commission tiers and buyer intent keywords.
4. Click **Generate Affiliate Brief** to produce an FTC-compliant monetization section for your video script, including mandatory disclosures and affiliate link placements.

---

## 7. 60-Day Competitor Content-Gap Analysis

The **Gap Finder Engine** analyzes recent video publishing density in a rolling 60-day window:
- **Major Opportunity (Gap State 1)**: Zero or near-zero recent competitor videos found. High potential to capture search traffic quickly.
- **Few Matching Recent Videos (Gap State 2)**: 1–3 matching videos found. Market is active but underserved; a high-quality video can rank easily.
- **Competitive Space (Gap State 3)**: 4+ videos published recently. Requires a unique angle, contrarian title hook, or superior production value.

---

## 8. The 1-Click SEO Content Factory

Once you select a winning topic:
1. Open the **SEO Content Factory** page.
2. Enter your topic and target viewer.
3. Click **Generate Content Package**.
4. The factory instantly prepares:
   - **5 Click-Worthy Title Candidates**: Optimized for search intent and character length (50–65 characters).
   - **5-Section Video Outline**: Hook, Intro, Problem Breakdown, Practical Solution, and Strong Outro.
   - **Complete 8-Part YouTube Description Draft**: Opening hook, primary keyword integration, chapter timestamps, social links, and affiliate disclaimer.
   - **Thumbnail Focal Point Concept**: Visual composition idea with high-contrast text hook.
   - **Target Tag Recommendations**: Formatted for YouTube Studio copy-pasting.

---

## 9. Pre-Publish SEO Readiness Checklist

Every generated content package includes an automated 5-point readiness check:
- ✅ **Title Length Check**: Validates that titles are between 50 and 70 characters (optimal for mobile and desktop truncation).
- ✅ **Opening Keyword Placement**: Confirms target keyword appears in the first 150 characters before YouTube's *"Show More"* fold.
- ✅ **Outline Pacing**: Ensures at least 4 structured retention checkpoints to prevent viewer drop-off.
- ✅ **Natural Keyword Density**: Flags repetitive stuffing ($\le 3.5\%$ density limit enforced).
- ✅ **FTC Affiliate Compliance**: Verifies that affiliate links include clear consumer disclosure language.

---

## 10. Saving, Reopening & Exporting Research

### Saving & Reopening
- All research sessions, video packages, and calendar entries are automatically saved to your local SQLite database (`data/keywords.db`).
- Access past work anytime under **Saved Projects & Memory** in the sidebar.

### Spreadsheet Export Security
- Click **Export CSV** or **Export Excel** on any research table or content package.
- **Formula Injection Defense**: All exported spreadsheets automatically sanitize formula prefix characters (`=`, `+`, `-`, `@`, `\t`, `\r`) with single quotes to protect your computer from malicious Excel macro executions.

---

## 11. Personal Research Memory & Duplicate Alerts

Keyword Studio actively remembers your past work so you never repeat research unnecessarily:
- **Instant Warning on Duplicate Seeds**: When entering a seed query in New Research or the Wizard, the engine checks existing channel records.
- **Fresh vs. Stale Guidance**:
  - *Researched $\le 30$ days ago*: Advises reopening your saved package to save time.
  - *Researched $> 30$ days ago*: Recommends a fresh refresh to capture new algorithm trends.
- **Non-Blocking**: Alerts are purely informative; you can always execute a fresh query if desired.
- **Smart Next Steps**: The **Smart Next Actions** tab recommends grounded tasks based on your actual data (e.g. *"Schedule recording date for unscheduled video package"*).

---

## 12. Daily Action Center & Morning Opportunity Reports

Keyword Studio features an automated **Morning Opportunity Engine**:
- **Execution Time**: Scheduled daily at `07:00 AM (Asia/Dhaka)`.
- **4-Channel Coverage**: Generates 3–5 fresh video opportunities for every channel.
- **Anti-Exhaustion Angle Fallbacks**: When initial seed topics have been generated, the engine automatically generates fresh angles (*Beginner Setup*, *Long-term Review*, *Common Mistakes*, *Worth Buying Revisit*) so your morning reports never dry up.
- **Local Runner Requirement**: To execute automated morning reports, Keyword Studio and your computer must remain running with Streamlit active.

---

## 13. Database Backup, Restore & Data Safety

All creator data, channel profiles, saved packages, and research history reside in `data/keywords.db`.

### How to Back Up Your Data
Double-click `backup_data.bat` in the project root, or run in terminal:
```powershell
python scripts/backup_data.py --note "Weekly creator backup"
```
- Creates a timestamped snapshot in `data/backups/keywords_backup_YYYYMMDD_HHMMSS.db`.
- Automatically verifies SQLite integrity and outputs a manifest JSON.

### How to Restore a Backup
Double-click `restore_data.bat` in the project root, or run in terminal:
```powershell
# List available backups
python scripts/restore_data.py --list

# Restore the most recent backup
python scripts/restore_data.py
```
- Creates a safety pre-restore backup of your current database before replacing it.
- Restores the file atomically and verifies table integrity.

---

## 14. Troubleshooting Common Issues

### Issue 1: "Address already in use (port 8501 occupied)"
- **Cause**: Another instance of Keyword Studio or Streamlit is already running.
- **Solution**: Open `http://localhost:8501` in your browser. Alternatively, launch on a custom port:
  ```powershell
  streamlit run app.py --server.port 8502
  ```

### Issue 2: "Python was not detected on your system PATH"
- **Solution**: Install Python 3.12 without administrator privileges:
  ```powershell
  winget install --id Python.Python.3.12 --scope user
  ```
  Restart your terminal and re-run `run.bat`.

### Issue 3: "YouTube Data API metrics showing 'Not Available'"
- **Cause**: `YOUTUBE_API_KEY` is not configured in your `.env` file.
- **Solution**: This is expected behavior. Keyword Studio works completely offline without it. If you want live competitor view counts, add your free key to `.env`.

---

## 15. Notice on Epistemic Modesty & Truthful Metrics

Keyword Studio adheres to strict standards of truth in software engineering:
1. **No Guaranteed Rankings**: Relevance scores (0–100) measure keyword-to-topic alignment and search intent. They do **not** guarantee a #1 ranking on YouTube.
2. **Autocomplete Predictions vs. Search Volume**: Autocomplete queries represent real phrases actively suggested by YouTube's search engine. They are **not** monthly search volume estimates.
3. **Sample Coverage vs. Platform Absence**: When a search reveals 0 competitor videos in the 60-day window, this indicates low competition within the analyzed query sample; it does not prove zero videos exist platform-wide.
