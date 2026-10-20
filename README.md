# YouTube Keyword Finder 🔍

**YouTube Keyword Finder** is a local-first, privacy-focused Windows desktop application engineered to discover real YouTube autocomplete suggestions, recursively map keyword clusters, and generate classified keyword variations (Top 5/10, Best, Reviews, How-to, Comparisons, Questions, and Long-tail).

---

## 🏛️ Architecture & Principles

- **Local-First & Offline Capable**: All discovered keywords and research sessions are stored in an embedded SQLite database (`data/keywords.db`) using Write-Ahead Logging (WAL) for durability and concurrent read performance.
- **Strict Data Integrity**:
  - Results are explicitly tagged with their origin: `autocomplete` (real YouTube suggestions), `cached` (local replay), or `algorithmic` (pattern-derived variations).
  - **Zero Fabricated Metrics**: No synthesized search volume, CPC, keyword difficulty scores, or fictional trend charts. Autocomplete suggestions represent observed search predictions, not search traffic volume.
- **Replaceable Provider Architecture**: Autocomplete queries are decoupled through `BaseAutocompleteProvider`, allowing alternative or private endpoints without rewriting business logic.
- **Bounded Breadth-First Expansion Engine**: Explores keyword hierarchies level-by-level with strict depth caps, request budgets, and unique keyword target limits.
- **Unicode-First**: Full native support for non-Latin scripts, prioritizing English and Bangla (`বাংলা`).
- **Zero Paid Dependencies**: Runs completely locally on Windows with standard open-source Python libraries.

---

## 📁 Project Directory Structure

```
YOUTUBE KEYWORD PLAN/
├── .gitignore                  # Git exclusions (venv, sqlite db, logs, caches)
├── requirements.txt            # Python dependencies (Streamlit, Requests, Pandas, OpenPyXL, Pytest)
├── README.md                   # Project documentation & setup instructions
├── checklist.md                # Phase-by-phase implementation & verification checklist
├── app.py                      # Main Streamlit desktop dashboard entry point
├── config.py                   # Root configuration proxy
├── data/                       # Local SQLite storage (created at runtime)
│   └── keywords.db
├── logs/                       # Rotating application logs (created at runtime)
│   └── app.log
├── src/                        # Modular application package
│   ├── __init__.py             # Package metadata
│   ├── classifier/             # Deterministic classification service (Phase 5)
│   │   ├── __init__.py         # Package exports
│   │   ├── models.py           # TailLength, SearchIntent, TailThresholds, KeywordClassification
│   │   ├── rules.py            # Bilingual regex rule definitions (English & Bangla)
│   │   └── service.py          # KeywordClassifier service
│   ├── config.py               # Central AppConfig dataclass & runtime constants
│   ├── crawler/                # Recursive & controlled expansion engine
│   │   ├── __init__.py         # Package exports
│   │   ├── engine.py           # RecursiveKeywordEngine (BFS queue, deduplication, provenance)
│   │   ├── expansion.py        # ControlledExpansionEngine (A-Z, 0-9, Preposition & Modifier expansion)
│   │   └── models.py           # CrawlConfig, ExpansionConfig, DiscoveredKeyword, StopReason

│   ├── deduplication/          # Deduplication & provenance engine (Phase 5)
│   │   ├── __init__.py         # Package exports
│   │   └── engine.py           # DeduplicationEngine (provenance merging & fuzzy detection)
│   ├── intelligence/           # Advanced Research Intelligence (Phase 9)
│   │   ├── __init__.py         # Package exports
│   │   ├── scoring.py          # RelevanceScorer (0-100 explainable formula & breakdown)
│   │   ├── clustering.py       # TopicClusteringEngine (semantic groups, renaming & moving)
│   │   └── summary.py          # ResearchSummary (audit-grade session metrics telemetry)
│   ├── models/
│   │   ├── __init__.py
│   │   └── keyword.py          # KeywordItem, AutocompleteResult, SourceType enums
│   ├── patterns/               # Smart keyword pattern generator (Phase 4)
│   │   ├── __init__.py         # Package exports
│   │   ├── generator.py        # SmartKeywordPatternGenerator (de-stuttering & provenance)
│   │   ├── models.py           # GeneratedKeyword, PatternCategory, PatternConfig
│   │   └── templates.py        # Bilingual templates (English & Bangla NFC)
│   ├── providers/              # Autocomplete provider engine
│   │   ├── __init__.py         # Package exports
│   │   ├── base.py             # BaseAutocompleteProvider abstract class
│   │   ├── exceptions.py       # Domain exception hierarchy (RateLimitError, etc.)
│   │   ├── rate_limiter.py     # Thread-safe request rate limiter
│   │   └── youtube.py          # YouTubeAutocompleteProvider (retries, timeouts, cache)
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── backup.py           # SQLite online backup, validation, and safe restore service
│   │   ├── database.py         # SQLite connection manager, project persistence, and TTL cache
│   │   ├── export.py           # CSV (UTF-8 BOM), Excel (.xlsx), and formula-injection sanitizer
│   │   └── migrations.py       # Versioned schema migration runner with pre-migration backups
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── components.py       # Streamlit UI headers, metrics cards, sidebar controls
│   │   └── styles.py           # CSS styling & responsive layout
│   └── utils/
│       ├── __init__.py
│       ├── logging.py          # Rotating file & console logger
│       ├── normalization.py    # Bilingual Unicode NFC, tokenization & canonical keys
│       └── validators.py       # Unicode-safe input and parameter bounds validation
└── tests/                      # Automated test suite (100% offline with mocks)
    ├── __init__.py
    ├── conftest.py             # Pytest fixtures and isolated temporary databases
    ├── test_app_imports.py     # Architecture boundary and module import tests
    ├── test_autocomplete.py    # Provider unit tests (18 requirements + dashboard)
    ├── test_classification.py  # Phase 5 classification, normalization & deduplication tests
    ├── test_config.py          # Settings, bounds validation & startup tests
    ├── test_crawler.py         # Recursive engine unit tests (18 requirements + UI integration)
    ├── test_dashboard_phase6.py # Phase 6 dashboard, navigation & controls tests
    ├── test_database.py        # SQLite schema, queries, rollback & cache tests
    ├── test_models.py          # KeywordItem, Unicode handling, and classification tests
    ├── test_patterns.py        # Smart pattern generator tests (20 requirements + models)
    ├── test_storage_phase7.py  # Phase 7 migrations, research projects, export & backup tests
    └── test_validators.py      # Unicode sanitization and crawl limits validation tests
```

---

## 🔄 Recursive Keyword Expansion Engine (Phase 3)

The recursive engine (`RecursiveKeywordEngine`) traverses YouTube autocomplete suggestions hierarchically using a breadth-first search (BFS) queue.

### Core Capabilities:
1. **Multi-Seed Processing**: Accepts one or multiple seed keywords (comma- or newline-separated), initiating exploration at depth 0.
2. **Explicit Depth Tracking**:
   - `depth = 0`: Seed query executed.
   - `depth = 1`: First-level suggestions explored.
   - `depth = 2+`: Deeper cluster branches expanded recursively.
3. **Strict Bounded Controls**:
   - **Maximum Depth**: Clamped strictly between 0 and 5.
   - **Request Budget**: Maximum allowable outbound HTTP requests per session (enforced *before* each request).
   - **Result Target**: Halts exploration immediately once the desired number of unique keywords is found.
   - **Polite Delays**: Configurable pause between requests (`min_delay_seconds`).
4. **Deduplication & Provenance Merging**:
   - Normalized Unicode comparison (`NFC` form, whitespace-stripped, case-folded).
   - When a keyword is rediscovered through an alternative branch, its provenance (`parent_queries`, `discovery_paths`, `last_discovered_at`) is merged without creating redundant database rows.
   - Avoids repeated requests for already processed queries.
5. **Transparent Stop Reasons**:
   - `Result target reached`: Desired keyword count achieved.
   - `Request budget exhausted`: Hard request ceiling hit (retaining partial results).
   - `Maximum depth reached`: Explored all branches within depth boundaries.
   - `Queue exhausted`: All discovered keyword branches fully mapped.
   - `User cancellation`: User requested immediate stop via cancellation token.
   - `Provider failure`: Gracefully halted on network error while preserving discovered keywords.

---

## 🌐 YouTube Autocomplete Provider & Limitations

The application uses YouTube's suggestion endpoint:
```
https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q=KEYWORD
```

### Important Data-Source Notes & Limitations:
1. **Unofficial Endpoint**: This is a free-first, unofficial suggestion endpoint. It is not permanently guaranteed by YouTube and may be throttled or changed by Google at any time.
2. **Network Resilience**:
   - **Connection & Read Timeouts**: Defaults to 3.0s connect, 6.0s read.
   - **Bounded Retries**: Maximum 3 attempts with exponential backoff (`0.3s * 2^attempt`). Never retries indefinitely.
   - **HTTP 403 (Forbidden)**: Immediately halts without retrying.
   - **HTTP 429 (Rate Limit)**: Honors `Retry-After` headers if <= 5 seconds; otherwise raises `RateLimitError`.
   - **Rate Limiting**: Enforces a minimum interval (default 0.2s) between consecutive outbound requests.
   - **Local TTL Cache**: Successful responses are cached in SQLite for 24 hours (`cache_ttl_seconds = 86400`) to prevent redundant network requests.
3. **Structured Results**: Every result returns structured metadata:
   - `keyword`: Discovered suggestion text (Unicode NFC normalized)
   - `source_type`: Set to `"autocomplete"` for genuinely retrieved predictions
   - `source_name`: `"youtube_autocomplete"`
   - `language`: Configured ISO-639-1 language code (e.g., `en`, `bn`)
   - `country`: Configured ISO-3166-1 regional country code (e.g., `US`, `BD`)
   - `retrieved_at`: UTC ISO timestamp
   - `discovery_query`: Seed query that triggered the suggestion

---

## 💻 Windows Setup & Installation

### 1. Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Version 3.12 or newer

If Python 3.12 is not yet installed on your system, install it via `winget` in PowerShell:
```powershell
winget install --id Python.Python.3.12 --scope user
```

### 2. Environment Setup

Open PowerShell in the project directory (`c:\Users\HP\Downloads\YOUTUBE KEYWORD PLAN`):

```powershell
# Create a local virtual environment
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

Install the locked requirements into the virtual environment:
```powershell
pip install -r requirements.txt
```

---

## 🧪 Running Automated Tests

Run the full automated test suite using Pytest:

```powershell
pytest -v
```

All 171 automated tests pass with 0 failures:
- Architecture boundary and import tests (`tests/test_app_imports.py` - 7 tests)
- Full autocomplete provider mock test suite (`tests/test_autocomplete.py` - 22 tests)
- Classification, normalization & deduplication test suite (`tests/test_classification.py` - 21 tests)
- Configuration, bounds validation & startup tests (`tests/test_config.py` - 4 tests)
- Recursive expansion engine test suite (`tests/test_crawler.py` - 21 tests)
- Professional dashboard & interactive controls test suite (`tests/test_dashboard_phase6.py` - 18 tests)
- SQLite database schema, persistence, rollback & cache tests (`tests/test_database.py` - 6 tests)
- Domain model and Bangla Unicode tests (`tests/test_models.py` - 5 tests)
- Smart keyword pattern generator test suite (`tests/test_patterns.py` - 27 tests)
- Database migration, backup, restore & spreadsheet export test suite (`tests/test_storage_phase7.py` - 26 tests)
- Unicode input sanitization and range checks (`tests/test_validators.py` - 7 tests)
- Phase 8 End-to-End integration, security & provider error test suite (`tests/test_integration_e2e_phase8.py` - 7 tests)

*Note: All automated tests use deterministic mock sessions and run 100% offline without live internet access.*

### Optional Live Smoke Test
To verify live responsiveness against the real Google Suggest endpoint:
```powershell
.\.venv\Scripts\python.exe tests/live_smoke_test.py
```

---

## 🚀 Launching the Application

### Option A: 1-Click Windows Batch Launcher (Recommended)
Double-click `run.bat` or execute in Command Prompt:
```cmd
run.bat
```
*Automatically validates virtual environment, installs dependencies if needed, and launches the dashboard.*

### Option B: 1-Click PowerShell Launcher
```powershell
.\run.ps1
```

### Option C: Manual Virtual Environment
```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

### Option D: Standalone Desktop Distribution (No Python Required)
Run the compiled standalone desktop application in `dist`:
```powershell
.\dist\YouTubeKeywordFinder\YouTubeKeywordFinder.exe
```

The application will launch in your default web browser at:
```
http://localhost:8501
```

---

## 🔒 Security & Data Privacy Guarantees

1. **Zero Cloud Transmission**: All keyword research, search parameters, and cached entries are stored exclusively on your local hard drive (`data/keywords.db`).
2. **Zero Credentials Required**: Operates 100% keyless without requiring YouTube Data API keys or cloud tokens.
3. **Spreadsheet Formula-Injection Protection**: Automatically escapes sensitive spreadsheet trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) during CSV and Excel exports.
4. **Directory Traversal Defense**: Backups and exports strictly sanitize filenames, preventing directory traversal attacks.
5. **No Administrator Privileges Required**: Runs purely in standard user space without requiring UAC elevation.
6. **Windows Defender Notice**: Standalone unsigned open-source `.exe` binaries created with PyInstaller may occasionally trigger a Windows SmartScreen false-positive notice ("Windows protected your PC"). Click *"More info"* -> *"Run anyway"* or use the Python launcher (`run.bat` / `run.ps1`).

---

## 🔧 Troubleshooting Instructions

### 1. PowerShell Script Execution Disabled (`PSSecurityException`)
If executing `.\run.ps1` produces an execution policy error, enable script execution for the current PowerShell session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\run.ps1
```

Alternatively, invoke Streamlit directly from the virtual environment:
```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

### 2. Port 8501 Already in Use
If port 8501 is occupied by another application, specify an alternate port:
```powershell
streamlit run app.py --server.port 8502
```

### 3. Windows Terminal Unicode Display Issues
If Unicode or Bangla characters appear as question marks (`???`) in the Windows console, configure PowerShell to use UTF-8 encoding:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

### 4. Windows App Execution Alias Conflict
If running `python` launches the Microsoft Store instead of Python 3.12:
1. Open Windows **Settings** > **Apps** > **Advanced app settings** > **App execution aliases**.
2. Toggle OFF **App Installer** for `python.exe` and `python3.exe`.
3. Use `.\.venv\Scripts\python.exe` directly.

---

## 🧩 Smart Keyword Pattern Generator (Phase 4)

The pattern generator (`SmartKeywordPatternGenerator`) produces high-intent search query variations across 8 categories in English and Bangla completely offline:

1. **8 Core Categories**:
   - **Listicles**: `top 5 [keyword]`, `top 10 [keyword]`, `best 5 [keyword]`, `সেরা ৫ [keyword]`
   - **Best & Buying Intent**: `best [keyword]`, `best budget [keyword]`, `[keyword] buying guide`, `সেরা [keyword]`
   - **Reviews**: `[keyword] review`, `[keyword] honest review`, `[keyword] রিভিউ`
   - **How-To & Tutorials**: `how to [keyword]`, `[keyword] tutorial`, `[keyword] step by step`, `কিভাবে [keyword] করবেন`
   - **Comparisons (VS)**: `[keyword] vs alternatives`, `[keyword] vs [alternative]`, `[keyword] বনাম [alternative]`
   - **Questions**: `what is [keyword]`, `how does [keyword] work`, `why is [keyword] important`, `[keyword] কি`
   - **Audience & Use-Case**: `[keyword] for beginners`, `[keyword] for students`, `নতুনদের জন্য [keyword]`
   - **Time Modifiers**: `best [keyword] [current_year]`, `[keyword] guide [current_year]` (dynamic year via `datetime.now(timezone.utc).year`)
2. **Deterministic & 100% Offline**: Requires zero network requests, YouTube API keys, or paid AI services.
3. **Bilingual NFC Normalization**: Full Unicode NFC normalization across all English and Bengali strings.
4. **De-Stuttering Engine**: Automatically collapses repetitive adjacent words or phrases (e.g., `"python tutorial tutorial"` -> `"python tutorial"`).
5. **Strict Competitor Rules**: Never hallucinates or fabricates comparison competitors; specific comparison pairs are generated only when verified alternatives are supplied by the user.
6. **Strict Provenance Preservation**: When merging generated patterns into autocomplete results, `source_type="autocomplete"` is strictly preserved, and genuine autocomplete attribution is never overwritten.

---

## 🏷️ Keyword Classification, Normalization & Deduplication (Phase 5)

Phase 5 introduces a deterministic classification service, bilingual Unicode normalization, canonical deduplication with provenance merging, and multi-dimensional search filtering.

### 1. Multi-Dimensional Classification (`src/classifier/`)
- **Strict Decoupling**: Tail length (`short`, `medium`, `long`), search intent (`question`, `listicle`, `review`, `how_to`, `comparison`, `buying_intent`, `informational`, `audience`), and origin (`autocomplete`, `generated`, `cached`) are tracked as distinct, independent dimensions.
- **Configurable Tail Thresholds (`TailThresholds`)**:
  - `short_max` (default 2): Keywords with 1–2 words $\rightarrow$ **Short-tail**
  - `medium_max` (default 4): Keywords with 3–4 words $\rightarrow$ **Medium-tail**
  - `5+` words $\rightarrow$ **Long-tail**
- **8 Intent Categories with Heuristics**: Bilingual regex-driven pattern matching for English and Bangla returning intent tags and heuristic confidence scores (0.0 to 1.0).
- **Multiple Intent Labels**: A keyword can qualify for multiple intents (e.g., `"how to buy best laptop"` qualifies for both `how_to` and `buying_intent`).

> [!IMPORTANT]
> **Data Integrity Notice**: Word count and tail classification describe query length only. Word count is **NOT** search volume, user demand, click-through rate, or ranking competition.

### 2. Bilingual Normalization & Tokenization (`src/utils/normalization.py`)
- **Unicode NFC Form**: Normalizes all inputs into canonical composed form, preventing decomposed Unicode mismatches in Bengali text (`বাংলা`).
- **Punctuation & Symbol Preservation**:
  - Technical symbols: `.net`, `node.js`, `c++`, `c#` are preserved as distinct single tokens.
  - Hyphenated compound terms: `step-by-step` is preserved intact.
  - Numeric tokens: `python 3.12`, Bengali numbers `৩.১২` are preserved.
- **Canonical Keys (`normalize_keyword_key`)**: Produces lowercase, whitespace-collapsed, punctuation-stripped keys solely for indexing and duplicate detection while preserving the exact original display text.

### 3. Deduplication & Provenance Merging (`src/deduplication/`)
- **Consolidation**: Deduplicates keywords across recursive crawl depths and pattern generations using the canonical key.
- **Authentic Provenance Preservation**: When a generated keyword matches an autocomplete suggestion, its `source_type="autocomplete"` is strictly preserved; multi-source discovery paths, parent queries, and timestamps are merged into `sources`.
- **Fuzzy Duplicate Detection**: Implements a non-destructive Levenshtein distance algorithm (`fuzzy_similarity`) to suggest potential duplicates without automatically destroying distinct search queries.

### 4. Safe SQLite Schema Migration (`src/storage/database.py`)
- Inspects SQLite schema dynamically via `PRAGMA table_info(keywords)`.
- Non-destructively alters the table to add `normalized_key`, `tail_length`, `intent_labels`, `sources_json`, and `word_count`.
- Automatically backfills legacy rows with token counts, canonical keys, and classifications upon application startup.
- Creates lookup indices `idx_keywords_norm_key` and `idx_keywords_tail`.

### 5. Multi-Dimensional UI Filters & Export Actions (`app.py`, `src/ui/components.py`)
- Real-time filtering grid for Source Type, Tail Length, Search Intent, Language, Country, and Keyword Substring.
- One-click UTF-8 CSV and Excel (`.xlsx` via `openpyxl`) export actions preserving Bengali Unicode text, classification tags, and full multi-source provenance metadata.

---

## 🖥️ Professional Dashboard & Interactive Controls (Phase 6)

Phase 6 structures the application into 6 dedicated, logical pages with clean visual hierarchy, thread-safe cancellation, and interactive keyword manipulation.

### 1. Six Dedicated Navigation Pages
1. **📊 Dashboard**: High-level overview with active research summary, engine health cards, SQLite storage statistics, and top 5 recent sessions with quick-load actions.
2. **🔍 New Keyword Research**: Research configuration supporting single and multi-seed inputs, locale selectors, expansion boundaries (depth, budget, target, delay), integrated pattern generation toggle, live progress tracking, and thread-safe cancellation.
3. **📋 Keyword Results**: Interactive results table with multi-dimensional filtering, 6 summary metric cards, multi-row selection, copy drawer, view row removal, and filter-aware CSV/Excel downloads.
4. **🧩 Pattern Generator**: Offline pattern generator generating variations across 8 intent categories in English and Bangla with provenance-preserving merge capability.
5. **💾 Saved Research**: Complete history browser for all persisted SQLite sessions, enabling session inspection, loading past sessions into results, session exports, and safe deletion.
6. **⚙️ Settings & Data Sources**: Runtime diagnostics, YouTube endpoint policies, local TTL cache inspection, cache pruning, and database maintenance tools.

### 2. Thread-Safe Research Cancellation
- Uses `threading.Event()` passed into the provider and recursive engine.
- Halts immediately before initiating the next network request.
- Safely retains all partial results collected prior to cancellation.
- Transparently reports `Cancelled by User` status without thread termination hazards.

### 3. Interactive Keyword Actions
- **📋 Copy Selected & Copy All Filtered**: Renders an accessible, cross-browser copy box with formatted newline-delimited text for one-click clipboard copying.
- **🗑️ Remove Selected from View**: Removes unwanted rows from active session memory without modifying or deleting stored records from SQLite.
- **💾 Save Research**: Persists in-memory research sessions to SQLite.
- **📥 Filter-Aware Exports**: One-click downloads of filtered results as UTF-8 CSV and Excel (`.xlsx` via `openpyxl`).

---

---

## 🗄️ Database, Research History & Export (Phase 7)

Phase 7 hardens local data persistence, research project lifecycle, audit trail, export fidelity, and disaster recovery.

### 1. Versioned Schema Migrations (`src/storage/migrations.py`)
- Tracks schema versions in table `schema_migrations`.
- Predictable, sequential migrations wrapped in transactions with immediate rollback on error.
- Automatic safety backups (`data/backups/pre_migration_v*`) before applying migrations on populated databases.
- Backfills legacy rows without modifying existing provenance.

### 2. Research Projects & Session Management (`src/storage/database.py`, `app.py`)
- Full research project metadata: project name, seed keywords, language, country, result counts, completion/cancellation/failure statuses, stop reasons, requests made, and parameter snapshots.
- Project listing, case-insensitive keyword search, project renaming, and confirmed cascade deletion.
- Opening saved research loads full historical records without re-triggering network requests.
- Resume/rerun research pre-populates research form with original parameters safely.

### 3. Provenance & Transactional Upserts
- Rich provenance tracking: `sources_json`, `parent_queries_json`, `discovery_paths_json`, `source_name`, and `last_seen_at`.
- Intra-batch and cross-run consolidation prevents duplicate keyword rows for the same project while merging sources and updating timestamps.
- Preserves authentic autocomplete source attribution even when rediscovered via algorithmic patterns.

### 4. Cache Policies & Isolation
- Locale-isolated cache keys `(query, language, country)`.
- Configurable TTL expiry (default 24h).
- Cache diagnostics: total, active, and expired query counts.
- Selective expired cache pruning and complete cache flush without altering research projects or keyword history.

### 5. Spreadsheet Export Center & Formula Protection (`src/storage/export.py`)
- **Formula Injection Protection**: Escapes leading spreadsheet formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) at the export boundary with a leading single quote, protecting users in Microsoft Excel, LibreOffice Calc, and Google Sheets while keeping original database values untouched.
- **UTF-8 Byte Order Mark (BOM)**: Uses `utf-8-sig` so Microsoft Excel on Windows renders non-Latin scripts (such as Bengali বাংলা) with 100% typography fidelity and zero mojibake.
- **openpyxl Excel (.xlsx)**: Generates styled workbooks with custom header fills, auto-fit column widths, and metadata summary blocks.
- **Multi-Scope**: Export currently filtered keywords, selected table rows, or all project keywords with descriptive timestamped filenames.

### 6. Atomic Online Backup & Safe Restore (`src/storage/backup.py`)
- Uses SQLite's online backup API (`sqlite3.Connection.backup()`) to create consistent snapshots even during active WAL concurrency.
- Validates backup integrity using `PRAGMA integrity_check` and table verification.
- Safe restore mechanism automatically takes a pre-restore safety snapshot before overwriting the active database.

---

## 🗺️ Project Phases

| Phase | Title | Status |
| :--- | :--- | :--- |
| **Phase 1** | **Project Foundation & Architecture** | **Completed & Audited** ✅ |
| **Phase 2** | **Live YouTube Autocomplete Integration** | **Completed & Verified** ✅ |
| **Phase 3** | **Recursive Keyword Expansion Engine** | **Completed & Verified** ✅ |
| **Phase 4** | **Smart Keyword Pattern Generator** | **Completed & Verified** ✅ |
| **Phase 5** | **Classification, Normalization & Deduplication** | **Completed & Verified** ✅ |
| **Phase 6** | **Professional Dashboard & Interactive Controls** | **Completed & Verified** ✅ |
| **Phase 7** | **Database, Research History & Export** | **Completed & Verified** ✅ |
| **Phase 8** | **Final Integration, Security Audit & Desktop Release** | **Completed & Verified** ✅ |
| **Phase 9** | **Advanced Keyword Discovery & Research Intelligence** | **Completed & Verified** ✅ |
| **Phase 10** | **YouTube Video SERP & Competitor Inspector** | **Completed & Verified** ✅ |
| **Phase 11** | **YouTube Content Opportunity Analyzer & Video Planning System** | **Completed & Verified** ✅ |
| **Phase 12** | **Niche Product Discovery & Last-60-Days Content Gap Analyzer** | **Completed & Verified** ✅ |
| **Phase 12.1** | **Product Opportunity System Final Audit & Error Fix** | **Completed & Verified** ✅ |
| **Phase 13** | **AI-Powered Niche Research & Product Opportunity Intelligence** | **Completed & Verified** ✅ |
| **Phase 14** | **Product Opportunity Ranking & Affiliate Content Planner** | **Completed & Verified** ✅ |
| **Phase 15** | **Automated Niche Research Reports & Opportunity Monitoring** | **Completed & Verified** ✅ |

---

## 🧠 Advanced Research Intelligence & Discovery (Phase 9)

Phase 9 upgrades the research engine into a structured, audit-grade YouTube keyword intelligence system:

### 1. Multi-Source Controlled Keyword Discovery
- **Discovery Dimensions**:
  - Original Seed Autocomplete
  - Alphabet Expansion: `seed a` through `seed z`
  - Prefix & Intent Expansion: `seed for`, `seed in`, `seed vs`, `seed review`, `seed comparison`
  - Question Expansion: `how to choose the seed`, `which seed is best`, `what is the best seed`
  - Target Audience & Use-Case Expansion: `seed for beginners`, `seed for black cars`, `seed for old cars`
  - Numeric Expansion: `seed 0` through `seed 9`
- **Strict Provenance Separation**: Explicit tagging between `LIVE_AUTOCOMPLETE`, `CACHED_AUTOCOMPLETE`, `GENERATED_QUERY`, and `GENERATED_PATTERN`. Generated queries are never mislabeled as keywords returned by YouTube.

### 2. Rule-Based Bilingual Intent Classification (10 Canonical Categories)
- `HOW_TO_TUTORIAL`: Step-by-step instructional guides ("how to apply car wax")
- `COMPARISON_VS`: Head-to-head comparisons & alternative evaluations ("car wax vs ceramic coating")
- `BEST_TOP_LIST`: Top recommendations & listicles ("top 10 best car wax 2025")
- `BUYING_COMMERCIAL`: Purchase intent & deals ("where to buy car wax cheap")
- `PROBLEM_SOLVING`: Troubleshooting & defect correction ("how to fix car wax haze and streaks")
- `AUDIENCE_SPECIFIC`: User segment & use-case ("best car wax for beginners")
- `LOCATION_SPECIFIC`: Geographic & local availability ("car wax shop near me in Dhaka")
- `Bangla Informational`: Bengali informational searches ("গাড়ির ওয়াক্স কী")
- `Bangla Commercial`: Bengali pricing & availability ("গাড়ির ওয়াক্স এর দাম কত")
- `GENERAL`: Core topic variation without modifier

### 3. Explainable Heuristic Relevance Scoring (0–100)
- **Formula Breakdown**:
  $$\text{Relevance Score} = (0.40 \times \text{Seed Overlap}) + (0.30 \times \text{Sequence Similarity}) + (0.20 \times \text{Intent Clarity}) + (0.10 \times \text{Length Quality}) - \text{Spam Penalty}$$
- **Data Integrity Disclaimer**: This is an explainable heuristic relevance score, **not** search volume, CPC, or ranking difficulty.

### 4. Topic Clustering Engine
- **Deterministic Semantic Groups**: Automatically categorizes keywords into Paint Colors & Finishes, Comparisons & Alternatives, Reviews & Evaluations, How-To Guides, Pricing & Deals, Target Audience, Troubleshooting, Formulations, and Core Seed Variations.
- **Interactive Controls**: Supports manual cluster renaming, keyword moving across clusters, and cluster exclusion.

### 5. Audit-Grade Session Telemetry
- Computes actual metrics: Queries Attempted, Succeeded, Failed, Live Autocomplete Count, Cached Count, Generated Count, Total Unique Keywords, and Topic Cluster Count.

---

## 🎥 YouTube Video SERP & Competitor Inspector (Phase 10)

Phase 10 adds real YouTube search result inspection and competitor intelligence with full cost and quota transparency:

### 1. Local-First & Offline Resilience
- When no API key is configured, the application functions 100% offline in local-first mode.
- In strict adherence to our **zero fabricated metrics guarantee**, synthetic views and fictional tags are never invented. The dashboard honestly states: *"Not connected — enter optional API key in Settings"*.

### 2. Verified YouTube Data API v3 Integration
- **Batch Quota Optimization**:
  - Step 1: `search.list` retrieves up to 50 top-ranking video IDs (100 quota units).
  - Step 2: `videos.list` retrieves snippet, statistics, and contentDetails in a single batched call (1 quota unit).
  - Total Cost: Exactly **101 quota units** per search (~99 free searches/day with Google's free 10,000 units/day tier).
- **Zero-Unit Cache Hit**: Repeated keyword lookups are served instantly from the local SQLite `serp_cache` table (0 quota units consumed).
- **Daily Quota Guardrails**: Tracks daily units in `api_quota_usage` and automatically halts queries if the 10,000 unit daily limit is reached.

### 3. Video Metrics & Metadata Parsing
- **ISO 8601 Duration Parser**: Converts YouTube duration strings (`PT14M22S` -> `14:22`, `PT1H2M10S` -> `1:02:10`, `PT45S` -> `0:45`).
- **Relative Age**: Computes days elapsed and human-readable time ("Today", "2 months ago", "1 year ago").
- **Competitor Video Tags Cloud**: Aggregates all tags across ranking videos, computes occurrence frequencies, and provides a **1-click copy box** for creators to paste into their video uploads.

### 4. Explainable Creator Opportunity Score (0–100)
- **Formula Components**:
  1. **Demand Factor (0–40 pts)**: Evaluates median views of ranking videos. High median views confirm sustained audience interest.
  2. **Content Gap & Freshness (0–30 pts)**: Rewards keywords where top-ranking videos are older (> 1–2 years), indicating an opening for fresh content.
  3. **Competition Accessibility (0–30 pts)**: Rewards SERPs where videos with under 50,000 views successfully rank, proving smaller creators can break through.
- **Qualitative Opportunity Bands**:
  - `75–100`: High Opportunity (Strong demand & accessible competition)
  - `50–74`: Moderate Opportunity (Consistent demand with established channels)
  - `25–49`: Low-to-Moderate Opportunity (High competition saturation)
  - `0–24`: Challenging / Saturated (Monopoly domination or low demand)

### 5. Export & Security Protection
- **CSV Export**: Encoded in UTF-8 BOM (`utf-8-sig`) for Excel multi-script fidelity with formula injection protection (`'=SUM(...)`).
- **Excel Export**: Styled `.xlsx` workbooks with custom header colors, auto-width columns, and frozen header rows.

---

## 💡 Content Opportunities & Planning System (Phase 11)

Phase 11 introduces a structured content strategy workspace combining keyword discovery from Phase 9 and video SERP research from Phase 10:

- **Unified Opportunity Pipeline**: Discovers high-potential topics, scores them using empirical demand and competition metrics, and maps them to clear content formats (Tutorials, Buying Guides, Comparisons).
- **Automated Content Brief Generator**: Creates production-ready video outlines, recommended title hooks, chapter timestamps, and target keywords.
- **Content Calendar & Kanban Workflow**: Organizes production from `Idea` -> `Outlined` -> `Scripted` -> `Recorded` -> `Edited` -> `Published`.
- **Integrated Dual Exports**: Exports entire content schedules and topic opportunities to CSV (UTF-8 BOM) and formatted Excel workbooks.

---

## 📦 Niche Product Opportunity Finder (Phase 12 & Phase 12.1)

Phase 12 builds a specialized product research engine to identify commercial and hardware content gaps over recent date windows (default: previous 60 days):

### 1. Multi-Channel Product Discovery
- **Curated Hardware Catalogs**: Pre-loaded market models for popular categories: Wireless Earbuds, Mechanical Keyboards, Smartwatches, Action Cameras, and Microphones.
- **Dynamic Autocomplete Discovery**: Exploits free YouTube autocomplete suggestions to discover emerging market products in any custom niche.
- **Database Provenance**: Ingests previously discovered keyword seed items and competitor video titles.
- **User-Supplied Seeds**: Parses custom seed lists, brands, and models.

### 2. Multi-Mode Date-Bounded YouTube Research
- **Query Strategies**: Automatically generates structured queries across Product Reviews, Unboxing, Comparisons, Buying Guides, Alternatives, and General Searches.
- **RFC 3339 Date Filtering**: Passes `publishedAfter` and `publishedBefore` parameters to YouTube Data API v3 search endpoint to isolate videos published strictly within the selected window (e.g. past 60 days).
- **Exact Model Matching & Isolation**: Token-level decomposition and brand isolation prevent cross-generation collisions (e.g., `Sony WF-1000XM4` is strictly isolated from `Sony WF-1000XM5`).

### 3. Transparent 4-Tier Classification
- `MATCHING VIDEOS FOUND`: Multiple videos retrieved in the date window exceeding user threshold.
- `FEW MATCHING VIDEOS FOUND`: 1 to $N-1$ matching videos found in search sample.
- `NO MATCHING VIDEOS FOUND IN SEARCHES`: 0 matching videos retrieved across $\ge min\_queries\_for\_zero\_match$ queries.
- `INSUFFICIENT RESEARCH`: Queries executed were below minimum threshold or failed; prevents false gap claims.

### 4. Explainable Research Opportunity Scoring (0–100)
- **Scarcity Factor (0–40 pts)**: Rewards observed gaps in recent YouTube coverage.
- **Search Coverage (0–25 pts)**: Rewards products with 2 or more successful query strategies executed.
- **Identity Confidence (0–20 pts)**: Weights verified hardware models over unverified extractions.
- **Niche Relevance (0–15 pts)**: Weights verified catalog and keyword provenance over unknown sources.
- **Penalty Guardrails**: Unverified extractions and items with insufficient research coverage are strictly capped ($\le 45$ or $\le 55$) with `Low` confidence to prevent false top rankings.
- **Empirical Notice**: Results are labeled as empirical search observations over the configured date window, explicitly stating they do not represent proof of platform-wide absence.

---

## 🤖 AI-Powered Niche Research & Product Opportunity Intelligence (Phase 13)

Phase 13 elevates the product research engine into an intelligent, evidence-backed YouTube research assistant:

### 1. 10-Step Guided Niche Workflow
1. **Enter Niche & Scope**: Set niche name (e.g. `Wireless Earbuds`).
2. **Region & Dates**: Select target country, language, and date window (default: previous 60 days).
3. **Multi-Channel Discovery**: Real market models gathered across seed inputs, curated catalogs, database queries, and live autocomplete.
4. **Identity Verification**: Assign verification statuses (`Verified Market Product`, `Extracted Candidate`, `User Supplied`, `Needs Review`, `Unverified`, `Rejected`) and preserve original detected names.
5. **AI Query Expansion**: Generates specialized search angles labeled `AI_GENERATED_QUERY` with pre-execution review.
6. **Bounded Search Execution**: Executes queries through connected YouTube API v3 or offline simulation within strict request budgets.
7. **Video Matching**: Matches retrieved videos using exact model, alias, or description isolation.
8. **5-Tier Content Gap Classification**: Separates `MATCHING VIDEOS FOUND`, `FEW MATCHING VIDEOS FOUND`, `NO MATCHING VIDEOS FOUND IN EXECUTED SEARCHES`, `INSUFFICIENT RESEARCH`, and `PRODUCT IDENTITY UNVERIFIED`.
9. **Weighted Opportunity Scoring**: Calculates 0–100 score with user-customizable factor weights (Scarcity, Coverage, Identity, Relevance).
10. **Executive Report & User Review**: Produces a structured synthesis separating verified facts from strategic interpretations, with a full user correction audit trail.

### 2. Multi-Angle Query Generation
Generates targeted queries across 10 distinct content angles:
- `Product Reviews`
- `Unboxing`
- `Comparisons`
- `Buying Guides`
- `Alternatives`
- `Product Testing` (sound, latency, battery tests)
- `Long-Term Use` (after 6 months, 1 year later)
- `Common Problems` (issues, fixes, complaints)
- `Target Audiences` (for gaming, gym, students)
- `Different Use Cases` (mic quality, ANC performance)

### 3. Multi-Provider AI Architecture (`src/providers/ai.py`)
- **Deterministic Offline Provider**: 100% offline, zero-cost fallback generating structured query expansion and executive syntheses without external network dependencies.
- **Google Gemini Provider**: Cloud REST API integration via `generateContent`.
- **OpenAI Provider**: Cloud REST API integration via `/v1/chat/completions`.
- **Mock AI Provider**: Fast, predictable provider for automated testing.

### 4. Non-Destructive User Review & Audit Trail
- **Product Renaming**: Renames candidate products while preserving `original_name` and recording timestamp, old value, new value, and reason in `audit_trail_json`.
- **Status & Priority Controls**: Direct UI controls to confirm/reject products, change priority (`High`, `Medium`, `Low`), and write research notes.
- **Video Exclusions**: Exclude individual video matches from scoring calculations with recorded exclusion reasons.

### 5. Structured Reporting & Formula-Safe Exports
- **Empirical Findings Notice**: Results are strictly presented as empirical observations within the search sample, avoiding unfounded claims of platform-wide absence.
- **Zero Synthetic Volume Guarantee**: No fabricated search volumes or ranking probability metrics.
- **Dual Formats**: Formula-sanitized CSV (`utf-8-sig` with BOM) and openpyxl styled Excel (`.xlsx`) containing all Phase 13 metadata, priority, categories, and audit notes.

---

## 🏷️ Product Opportunity Ranking & Affiliate Content Planner (Phase 14)

Phase 14 provides an evidence-based product opportunity ranking and affiliate content planning workspace to prioritize real products for YouTube content production without speculative assumptions:

### 1. Product Opportunity Workspace
- **Dedicated Navigation**: New UI workspace `🏷️ Product Opportunity Planner` integrated into sidebar navigation.
- **Candidate Import**: Seamless one-click import from existing Niche Research Sessions (Phases 12–13) or manual product addition.
- **8-Stage Workflow Lifecycle**: Tracks products across `Discovered`, `Needs Research`, `Verified`, `Shortlisted`, `Brief Created`, `In Production`, `Published`, and `Rejected`.
- **Dynamic Prioritization & Notes**: Assign priority (`High`, `Medium`, `Low`), record notes/hypotheses, and track verification checkboxes.

### 2. Multi-Factor Opportunity Scoring Formula (v14.0)
Transparent, heuristic 0–100 score based strictly on observed research findings:
1. **Identity Verification** (max 20 pts): Verified brand & model vs unverified extraction.
2. **Niche Relevance** (max 15 pts): Direct alignment with target niche and user category.
3. **Keyword Evidence** (max 15 pts): Depth and volume of supporting search queries.
4. **Research Coverage** (max 20 pts): Query diversity and execution breadth.
5. **Video Scarcity** (max 20 pts): Observed few or 0 matching videos in the recent search sample (requires at least 2 queries to claim scarcity).
6. **Evidence Completeness** (max 10 pts): Confirmed merchant availability and affiliate program data.

**Evidence Guardrails**:
- *Insufficient Research Cap*: If queries executed < 2, score is capped at $\le 40$ with confidence `Low Evidence`.
- *Unverified Identity Cap*: If product identity is unverified, score is capped at $\le 50$.
- *Scarcity Clarity*: Scarcity reflects observed search results within the executed query sample and is never labeled as search volume, ranking probability, or guaranteed profitability.

### 3. Non-Fabricated Affiliate Product Research (`src/providers/affiliate.py`)
- Captures real product/model, brand, official product page, known merchants (Amazon, Best Buy, direct brand), price/currency, affiliate program, commission info, and stock availability.
- **Strict Non-Fabrication Rule**: Unverified fields strictly record `"Needs verification"` or `None`. No synthetic conversion rates, earnings predictions, or fake merchant URLs.
- Extensible provider interfaces: `ManualAffiliateProvider`, `CuratedCatalogAffiliateProvider`, `MockAffiliateProvider`.

### 4. Strategic Content Format Recommendations (`ContentFormatRecommender`)
Rule-based recommendation engine matching product signals to 9 strategic YouTube formats:
- `Product Review`: Default baseline for physical goods with specifications and pricing.
- `Unboxing`: When product is newly launched or unboxing keywords appear.
- `Product Comparison`: When comparison queries (`vs`, `or`) or direct competitors exist.
- `Alternatives`: For premium products or budget-seeking search intent.
- `Buying Guide`: For roundup and category-wide selection queries.
- `Beginner Tutorial`: When setup, configuration, or pairing keywords appear.
- `Common Mistakes`: When buyer hesitation or mistake-avoidance keywords exist.
- `Long-Term Review`: For products with established longevity or durability interests.
- `Problem-Solving Video`: For troubleshooting, fixing, and pairing resolution queries.

### 5. Evidence-Grounded Affiliate Content Brief (`AffiliateBriefGenerator`)
Generates comprehensive, editable YouTube production briefs:
- **SEO & Audience Focus**: Primary keyword, supporting keywords, target audience, and search intent.
- **Title Angles**: 3–5 evidence-based video title options.
- **Timestamped Video Outline**: 6-part video structure tailored to the intended content format.
- **Research Priorities**: Questions to investigate, features to verify, and objective pros/cons.
- **Mandatory FTC Compliance Reminder**: Standard spoken and written disclosure statement prominently surfaced.
- **Ethical Creator Protection**: Explicit guidance prohibiting unsupported claims of personal testing or hands-on experience without verified direct use.
- **Fact-Checking Checklist**: Verification checklist ensuring specs, pricing, and links are confirmed before publishing.

### 6. Side-by-Side Product Comparison Matrix (`ProductComparisonEngine`)
- Allows users to select 2 or more products from the shortlist for side-by-side evaluation.
- Rigorous missing-metric handling: unobserved prices or merchants are formatted as `"Unavailable"` or `"Needs verification"`, never `0`.
- Prominent caution banner: *"Scarcity of observed videos does not guarantee search volume or profitability."*

### 7. Dual Spreadsheet Exports (`src/storage/export.py`)
- **Full Shortlist**: CSV (UTF-8 BOM `utf-8-sig`) and openpyxl Excel (`.xlsx`) with formula sanitization (`=`, `+`, `-`, `@`).
- **Content Briefs**: Dedicated CSV and Excel exports formatted for creators and scriptwriters.
- **Comparison Matrix**: Dual-format export of side-by-side matrices.

---

## 📡 Automated Niche Research Reports & Opportunity Monitoring (Phase 15)

Phase 15 builds a production-grade research automation and monitoring platform that allows users to save niche research configurations, trigger on-demand or recurring monitoring runs, execute differential snapshot analysis, and track longitudinal product opportunity shifts.

### 1. Saved Research Configurations (`SavedResearchConfig`)
- **Reusable Templates**: Captures niche name, country/language, date window (default 60 days), category filters, query templates, max products/queries, request budget ceiling, matching modes (`Exact Model Match`, `Flexible Fuzzy Match`), min coverage, opportunity formula version (`v14.0`, `v13.0`), enabled discovery methods (`seed`, `catalog`, `autocomplete`, `ai_angles`), and notes.
- **Full Configuration CRUD**: Create, inspect, edit, duplicate (`Copy of...`), pause, resume, and confirmed deletion.
- **Quota & Resource Safety**: Pre-run request estimation displays expected API queries upfront (`min(budget, max_products * max_queries)`) and adheres strictly to configured ceilings.

### 2. Repeatable Research Runs (`ResearchMonitorRun`, `ProductSnapshotItem`)
- **Execution Telemetry**: Tracks run number, trigger type (`Manual`, `Scheduled`, `Rerun`), status (`Pending`, `Running`, `Completed`, `Cancelled`, `Failed`, `Partial`), queries attempted/succeeded/failed, live vs cached requests, products discovered, and matching videos retrieved.
- **Safe Partial Preservation**: When request budgets are exhausted or runs are cancelled, all product snapshots gathered up to that point are safely persisted with status `Partial`.
- **Rerun Failed Queries**: Dedicated action allows creators to re-attempt failed queries without re-running the entire niche pipeline.

### 3. In-Process Recurring Scheduler (`ResearchSchedulerService`, `ResearchSchedule`)
- **Frequencies**: `Daily`, `Weekly`, `Monthly`, and `Manual Queue Only`.
- **Deduplication Safeguards**: Computes frequency window keys (`YYYY-MM-DD`, `YYYY-Www`, `YYYY-MM`) stored in `last_window_key` to prevent duplicate executions within the same interval.
- **Mandatory Local Process Disclosure**: Clearly communicates that recurring scans execute while the local application or background process is active on the user's desktop, with zero external credential leakage.

### 4. Snapshot Comparison Workbench (`ResearchComparisonEngine`, `SnapshotComparisonResult`)
- **Differential Matrix Analysis**: Compares Baseline Run A vs Newer Run B for the same niche.
- **Delta Tracking**:
  - *Newly Discovered Products*: Candidates observed in Run B that were absent in Run A.
  - *Dropped Products & Failed Query Caveats*: If Run B experienced search query failures, dropped products explicitly show: `"Omission may be due to search query failure in Run B, not absence from YouTube."`
  - *Matching Video Count Deltas*: Tracks shifts in observed YouTube videos over time.
  - *Opportunity Score Shifts*: Tracks point changes in heuristic opportunity scores.
  - *Newly Observed Channels*: Highlights new competitor or niche channels entering the SERP.
- **Empirical Caution Banner**: Discloses that snapshot variations reflect differences observed within the executed search sample and date window, never proof of platform-wide absence or deletion.

### 5. Change Detection Alerts & Evidence Feed (`ChangeAlertDetector`, `MonitorAlert`)
- **Severity Tiers**: `Critical` (run failures), `High Opportunity` (new verified candidates, major score increases), `Warning` (high query failure rates, budget ceilings, score drops), and `Info` (video count increases).
- **Supporting Evidence Details**: Every alert contains structured JSON evidence data inspectable via expandable cards.
- **Configurable Sensitivity**: Users can adjust score shift thresholds (default 15 pts) and video increase thresholds (default 3 videos).
- **In-App Management**: Dismiss individual alerts or clear all alerts with confirmation.

### 6. Historical Analytics & Longitudinal Telemetry (`HistoricalAnalyticsAggregator`)
- **Timeline Compilation**: Aggregates stored snapshot time series (Total Products, Average Opportunity Score, Matching Videos, Insufficient Research Count, Query Success Rate, Unique Channels).
- **Zero Extrapolation Policy**: Charts and summaries represent actual stored local snapshots across user-executed searches; missing data points are never synthetically fabricated or interpolated.
- **Interactive Visualizations**: Time-series line charts for score trends, video counts, query success rates, and product volume over time.

### 7. Dual Spreadsheet Export Center (`src/storage/export.py`)
- **Research Runs History**: CSV (UTF-8 BOM `utf-8-sig`) and openpyxl Excel (`.xlsx`).
- **Snapshot Comparison Matrix**: Full comparison matrix with delta indicators.
- **Change Alerts Feed**: Alerts with severity tags and serialized evidence details.
- **Historical Trends & Telemetry**: Time-series timeline metrics and complete runs logs.
- **Formula Injection Sanitization**: All exported cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are sanitized with leading single quotes.

---

## Phase 16 — Critical Quality Gates, Premium UI, Smooth Animations & Full-Stack Reliability

### 1. Premium SaaS Visual Experience & Design System (`src/ui/styles.py`)
- **Modern Dark Palette**: Deep dark aesthetic (`#090d16` canvas, `#0f172a` surface, `#1e293b` elevated) with glowing indigo ambient radial gradients.
- **Visual Hierarchy & Polished Tokens**: Custom `.demo-pill`, `.dot-demo`, `.dot-live`, `.premium-hero`, `.hero-title`, `.hero-gradient-text`, `.saas-card`, and refined `.metric-card` with glowing top-edge borders.
- **Zero Generic Template Feel**: Purpose-built desktop SaaS layout inspired by modern high-end software experiences without third-party asset bloat.

### 2. Smooth GPU-Accelerated Micro-Animations & Accessibility
- **Performance-Friendly Keyframes**: Hardware-accelerated CSS animations (`@keyframes fadeInUp`, `@keyframes pulseGlow`) using strictly `transform` and `opacity` properties.
- **Strict Reduced-Motion Compliance**: Dedicated `@media (prefers-reduced-motion: reduce)` media query instantly clamps animation and transition durations to `0.01ms` and disables pulse keyframes for sensitive users.
- **Multi-Device Responsive Breakpoints**: Comprehensive CSS media queries optimized for compact mobile viewports (320px–480px), tablet screens (481px–1024px), standard desktop displays (1440px), and ultra-wide monitors (1920px+).

### 3. Interactive Overview Showcase (`render_page_landing`)
- **High-Impact Hero**: Clean value proposition with 3 instant action triggers ("Launch Keyword Studio", "Find Niche Products", "View Live Dashboard") and architecture trust indicators.
- **5-Tab Interactive Product Showcase**: Illustrative simulated previews demonstrating autocomplete tree expansion, competitor SERP analysis, 60-day niche product gap detection, affiliate briefs, and monitor snapshot diffs.
- **Strict In-Memory Demo Separation**: Explicitly labeled with `[DEMO DATA - ILLUSTRATIVE PREVIEW]` badges; showcase previews never touch or mutate SQLite production tables.

### 4. Studio Profile & On-Device Security Vault (`render_page_auth`)
- **Creator Identity & Workspace Configuration**: Configurable studio name, workspace mode (`Solo Creator (Local Studio)`, `Production Agency Workstation`, `Enterprise Research Suite`, `Offline Privacy Vault`), default region, and primary niche saved to SQLite `app_settings`.
- **Zero-Cloud Privacy Vault**: Visual indicators confirming SQLite WAL multi-process concurrency, 100% on-device private data isolation, and verified database schema integrity.
- **Masked API Credential Security**: Safe display of YouTube Data API v3 keys (`AIzaSy...****`) with zero plaintext credential exposure.

### 5. Full Backward Compatibility & Acceptance Gates
- **Preserved Core Navigation**: `NAVIGATION_PAGES` strictly preserves its 6-item count for Phase 6/11/12 backward compatibility while `ALL_NAVIGATION_PAGES` contains the full 13-page workstation suite.
- **100% Passing Automated Tests**: 373 total tests passing across Phases 1–16 with zero regressions.
- **Clean Health & Database Integrity**: Verified Streamlit HTTP 200 health check and `PRAGMA integrity_check = ok`.

---

## Phase 17 — Apple-Inspired White Motion Design, Smart User Guide & Interactive Workflow Assistant

### 1. Apple-Inspired Typography & White Design System (`src/ui/styles.py`)
- **San Francisco System Font Priority**: `-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif` with fluid `clamp()` sizing and antialiased rendering.
- **Crisp White Palette**: `#FFFFFF` main canvas, `#F8FAFC` secondary background, `#111827` high-contrast primary text (15.6:1 WCAG AAA contrast), `#E5E7EB` borders, and `#2563EB` vibrant blue accent.
- **Subtle Visual Simplicity**: White cards with soft shadows, delicate top-edge borders, and generous whitespace inspired by Apple's minimalist design philosophy.

### 2. Fast Motion & Interactive Cursor Experience
- **Hardware-Accelerated Keyframes**: Fast, lightweight transitions (120ms–280ms) using strictly `transform` and `opacity` properties (`@keyframes fadeInUp`, `@keyframes fadeInScale`, `@keyframes pulseGlow`).
- **Interactive Cursor & Pressed Feedback**: Smooth hover elevation (`translateY(-2px)`), button active pressed state (`scale(0.985)`), and visible focus rings (`2px solid #2563EB`).
- **Touch-Device Protection**: `@media (hover: none) and (pointer: coarse)` disables hover animations on mobile devices to prevent touch artifacts and save battery.
- **Strict Reduced-Motion Support**: `@media (prefers-reduced-motion: reduce)` override clamps animations and transitions to `0.01ms !important`.

### 3. Complete User Guide & Playbooks (`src/ui/guide.py`, `PAGE_USER_GUIDE`)
- **All 10 Major Features Covered**:
  1. Keyword Discovery & Autocomplete Expansion
  2. Smart Keyword Pattern Generator
  3. YouTube Video Research & Competitor SERP
  4. Content Opportunities & Hook Workshop
  5. Niche Product Opportunity Finder (60-Day Gap)
  6. Product Opportunity Planner & Affiliate Briefs
  7. Research Monitor & In-Process Scheduler
  8. Saved Research Projects & History
  9. Studio Profile & Local Authentication Vault
  10. Settings, Cache Maintenance & SQLite Backups
- **All 11 Mandatory Points Per Feature**:
  1. Summary & purpose &bull; 2. When to use &bull; 3. Prerequisites &bull; 4. Step-by-step execution &bull; 5. Option choices & trade-offs &bull; 6. Recommended defaults &bull; 7. Expected results &bull; 8. How to interpret &bull; 9. Common mistakes &bull; 10. Troubleshooting &bull; 11. What to do next.
- **Searchable Documentation & Filters**: Instant full-text search across all guides and category filtering.
- **5-Stage Interactive Guided Tour**: Quick-start roadmap navigating creators across the complete workflow.

### 4. Contextual Help in Every Major Dashboard Page (`render_contextual_help`)
- Dedicated in-page expandable drawers embedded in Keyword Research, Video SERP, Content Opportunities, Product Opportunities, Planner, Monitor, History, Settings, and Studio Profile.

### 5. Smart Step-by-Step Workflow Assistant & Deterministic Guidance Engine
- **State-Aware Next Best Action**: Evaluates actual session state and SQLite statistics to recommend the single most impactful next action with rationale and direct navigation.
- **Interactive First-Time Onboarding**: Goal picker card helping new creators jump immediately into long-tail keywords, product gaps, competitor SERP, or affiliate planning.

### 6. Full Verification & Zero Regressions
- **392 Automated Tests Passing**: All 373 earlier tests + 19 new Phase 17 tests passed in 31.94s.
- **Operational Health**: Verified clean compile, `pip check`, whitespace check, and Streamlit HTTP 200 health.
