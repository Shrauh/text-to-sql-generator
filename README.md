# 🎓 Text-to-SQL Generator — College Placements

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq_API-Llama_3.3_70B-orange)](https://console.groq.com)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A **Conversational SQL Query Generator** that lets users ask questions in plain English and get back validated SQL queries + results — running against a sample college placements database.

Live Demo Link:- https://text-to-sql-generator-5rb7f6t72vlrwjcijs4ajk.streamlit.app/
![Screenshot placeholder](https://via.placeholder.com/900x500?text=App+Screenshot+—+Replace+Me)

---

## ✨ Features

- **Natural Language → SQL**: Type a question in English, get a valid SQLite query back
- **Schema-Aware Prompting**: Database schema is extracted programmatically and injected into every LLM call — never hardcoded
- **Multi-Layer Safety Validation**: Queries are sanitized and validated before execution (see [Why This Project](#-why-this-project))
- **Read-Only Execution**: Database connections use SQLite's `mode=ro` URI parameter as defense-in-depth
- **Auto-Visualization**: Results with 2–20 rows and numeric columns get automatic bar/line charts
- **Query Explanation**: Every result includes a plain-English explanation of what the SQL does
- **Session History**: Revisit past queries in the sidebar without re-running them
- **Schema Browser**: Expandable sidebar showing all tables, columns, types, and foreign keys

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  User Question (plain English)                                    │
└──────────────┬───────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────┐
│  Schema Extractor        │  ← Introspects SQLite DB via PRAGMAs
│  (schema_extractor.py)   │    Returns table/column/FK metadata
└──────────────┬───────────┘
               │  schema context
               ▼
┌──────────────────────────┐
│  SQL Generator           │  ← Sends question + schema to Groq API
│  (sql_generator.py)      │    Llama 3.3 70B @ temperature=0
└──────────────┬───────────┘
               │  raw SQL
               ▼
┌──────────────────────────┐
│  SQL Validator           │  ← Defense-in-depth validation:
│  (sql_validator.py)      │    • SELECT-only allow-list
│                          │    • Semicolon injection detection
│                          │    • Dangerous keyword scanning
│                          │    • SQLite-specific attack blocking
└──────────────┬───────────┘
               │  validated SQL
               ▼
┌──────────────────────────┐
│  Query Executor          │  ← Read-only SQLite connection (mode=ro)
│  (query_executor.py)     │    5s timeout, 500-row cap
└──────────────┬───────────┘
               │  pandas DataFrame
               ▼
┌──────────────────────────┐
│  Streamlit UI            │  ← Results table + auto-chart
│  (app.py)                │    + SQL code block + explanation
└──────────────────────────┘
```

---

## 📁 Project Structure

```
text-to-sql-generator/
├── app.py                   # Main Streamlit application
├── db/
│   ├── setup_db.py          # Creates + populates the sample SQLite DB
│   └── placements.db        # Generated database (not committed)
├── core/
│   ├── __init__.py
│   ├── schema_extractor.py  # Programmatic schema introspection
│   ├── sql_generator.py     # Groq LLM API integration
│   ├── sql_validator.py     # Multi-layer safety validation
│   └── query_executor.py    # Safe query execution + charting logic
├── requirements.txt
├── .env.example             # API key template
├── .gitignore
└── README.md
```

---

## 🚀 Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/Shrauh/text-to-sql-generator.git
cd text-to-sql-generator
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your Groq API key

Get a free API key from [console.groq.com/keys](https://console.groq.com/keys), then:

```bash
# Option A: Create a .env file
cp .env.example .env
# Edit .env and paste your key

# Option B: Set environment variable directly
export GROQ_API_KEY="your_key_here"       # macOS/Linux
set GROQ_API_KEY=your_key_here            # Windows CMD
$env:GROQ_API_KEY="your_key_here"         # Windows PowerShell
```

### 5. Generate the sample database

```bash
python db/setup_db.py
```

This creates `db/placements.db` with ~50 rows per table across 5 tables.

### 6. Run the app

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## 🛡️ Why This Project

Most text-to-SQL demos take a user's question, send it to an LLM, and execute whatever SQL comes back. **This is dangerous.** LLMs can hallucinate destructive queries, and malicious users can craft prompt-injection attacks to manipulate the generated SQL.

This project implements a **defense-in-depth safety validation pipeline** — the same kind of layered security approach used in production systems:

| Layer | What It Does | Why It Matters |
|-------|-------------|----------------|
| **Sanitization** | Strips markdown, trailing semicolons, whitespace | LLMs frequently wrap output in code blocks |
| **SELECT allow-list** | Only permits queries starting with `SELECT` | Blocks INSERT/UPDATE/DELETE/DROP at the gate |
| **Multi-statement detection** | Scans for semicolon-chained commands | Prevents `SELECT ...; DROP TABLE ...` injection |
| **Keyword scanning** | Word-boundary regex for destructive keywords | Catches dangerous ops hidden in subqueries/CTEs |
| **SQLite-specific checks** | Blocks ATTACH DATABASE, LOAD_EXTENSION | Prevents SQLite-specific attack vectors |
| **Read-only connection** | `sqlite3.connect(uri, mode=ro)` | Even if all above fail, DB physically can't be modified |
| **Row limit + timeout** | 500-row cap, 5-second timeout | Prevents denial-of-service via runaway queries |

This isn't just a toy demo — it's an **engineering-first approach** that demonstrates awareness of real-world security concerns when integrating LLMs with databases.

---

## 🗃️ Sample Database Schema

The database simulates a **college placement system** with 5 interrelated tables:

- **students** — Student profiles with CGPA, branch, batch year, city
- **companies** — Recruiting companies with sector and package info
- **placements** — Placement records linking students to companies (with status)
- **courses** — Academic courses offered per branch
- **enrollments** — Student course enrollments with grades

The data includes deliberate patterns for interesting queries: varied CGPA distributions, students without placements, multiple placement attempts, and diverse company sectors.

---

## ☁️ Deploying to Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set `GROQ_API_KEY` in **Settings → Secrets**:
   ```toml
   GROQ_API_KEY = "your_key_here"
   ```
5. The app will auto-deploy

> **Note:** Make sure to run `python db/setup_db.py` locally and commit `db/placements.db` to the repo before deploying, OR add a startup script.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit |
| LLM | Groq API (Llama 3.3 70B Versatile) |
| Database | SQLite |
| Language | Python 3.10+ |
| Data Generation | Faker |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
