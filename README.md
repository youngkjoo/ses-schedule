# TVKCC Facility Scheduler & Calendar Automation (8/2026 - 7/2027)

A robust, enterprise-grade Python tool that automates the ingestion, overlap checking, and Google Sheets synchronization of church facility requests for the 8/2026 - 7/2027 planning year. 

It generates an **interactive, premium, glassmorphic calendar view (`index.html`)** that is optimized to be hosted for free on **GitHub Pages** so your community members can see reservations in real-time.

---

## 🛠️ System Architecture

* **`scheduler_engine.py`**: Expands natural language and recurring scheduling patterns (e.g. "Every 2nd Sun", "8/9부터 연말까지 매주일"), manages room-specific exclusions, translates Korean facility requests to English, and standardizes date representations.
* **`overlap_detector.py`**: Compares exact start/end datetime intervals for facilities, permitting back-to-back bookings with zero buffer times.
* **`sheets_client.py`**: Connects via a Google Apps Script Web App to query and overwrite the Google Sheet, utilizing rectangular padding to prevent cell-range mismatch errors. It gracefully falls back to a local offline CSV on your disk if no API endpoint is configured.
* **`main.py`**: The CLI orchestrator. It checks overlaps, appends events under their correct layout headers (Liturgy vs. Community Events), and regenerates the calendar HTML in real-time.
* **`ingest.py`**: Multi-lingual (English and Korean) terminal utility allowing you to paste raw, unstructured requests straight from your email or messaging threads to parse and schedule them instantly.
* **`index.html`**: The interactive public calendar grid displaying a month-by-month calendar view with sticky headers, weekend highlighting, search filters, and group dropdown selectors.

---

## 🚀 Easy Ingestion Guide

### Method 1: Direct Chat Ingestion (Recommended)
Simply copy and paste raw facility requests (in English or Korean) directly into your AI assistant chat window. The assistant will parse, translate, check for overlaps, push it to Google Sheets, and update the calendar view automatically!

### Method 2: Local Terminal Paste
Run the interactive parser script from the root of this repository:
```bash
python3 ingest.py
```
Paste the entire email/message request directly into the prompt, press `Ctrl+D`, and the script will handle the rest!

---

## 🧪 Testing & Validation

The codebase features a comprehensive unit test suite covering date pre-processing, room mapping, overnight bookings, exclusions, and conflict detection.

To execute the tests:
```bash
python3 tests.py
```

---

## 🌐 Publishing the Calendar to GitHub Pages

To publish the calendar so your community members can view it on the web:

1. **Initialize Git & Commit**:
   ```bash
   git init
   git add .
   git commit -m "Initialize TVKCC Facility Scheduler & Calendar"
   ```
2. **Push to GitHub**:
   * Create a new repository on GitHub (e.g., `ses-schedule`).
   * Add the remote origin and push your main branch:
     ```bash
     git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git
     git branch -M main
     git push -u origin main
     ```
3. **Enable GitHub Pages**:
   * Go to your repository on GitHub.
   * Click **Settings** ➡️ **Pages** (in the left-hand menu).
   * Under **Build and deployment**:
     * Set **Source** to `Deploy from a branch`.
     * Set **Branch** to `main` and Folder to `/` (root).
     * Click **Save**.
4. **Access the Calendar**:
   * GitHub will deploy the page within a couple of minutes!
   * The calendar will be live at: **`https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/`**
   * Whenever you add a request locally and push it (`git add index.html && git commit -m "Update calendar" && git push`), the public calendar will update automatically!
