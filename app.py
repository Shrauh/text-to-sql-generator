"""
Conversational SQL Query Generator — Main Streamlit Application.

This app lets users ask questions in plain English about a college placements
database and get back validated SQL queries + results.  It uses the Groq API
(Llama 3.3 70B) for NL → SQL translation with a multi-layered safety validation
pipeline before any query touches the database.
"""

import os
import sys
import streamlit as st
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env for local development ──────────────────────────────────────────
load_dotenv()

# ── Resolve paths relative to this file ──────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = str(ROOT_DIR / "db" / "placements.db")

# ── Add root to sys.path so imports work on Streamlit Cloud ──────────────────
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.schema_extractor import get_schema_context, get_table_summaries
from core.sql_generator import generate_sql, explain_query
from core.sql_validator import sanitize_sql, validate_sql
from core.query_executor import execute_query, should_show_chart, get_chart_data

# ─────────────────────────────────────────────────────────────────────────────
# Page config & custom CSS
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Text‑to‑SQL · College Placements",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Global ────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Hero header gradient ──────────────────────────────────── */
.hero-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    color: white;
    box-shadow: 0 8px 32px rgba(102, 126, 234, 0.25);
}
.hero-header h1 {
    margin: 0; font-size: 2rem; font-weight: 700;
}
.hero-header p {
    margin: 0.4rem 0 0; opacity: 0.9; font-size: 1.05rem;
}

/* ── Cards ─────────────────────────────────────────────────── */
.result-card {
    background: linear-gradient(145deg, #f8f9ff 0%, #f0f2ff 100%);
    border: 1px solid #e0e4f5;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

/* ── Blocked badge ─────────────────────────────────────────── */
.blocked-badge {
    background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
    color: white;
    padding: 0.9rem 1.3rem;
    border-radius: 12px;
    font-weight: 600;
    box-shadow: 0 4px 16px rgba(255,65,108,0.25);
}

/* ── Success badge ─────────────────────────────────────────── */
.success-badge {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: white;
    padding: 0.6rem 1.1rem;
    border-radius: 10px;
    font-weight: 600;
    display: inline-block;
    margin-bottom: 0.5rem;
    box-shadow: 0 4px 16px rgba(17,153,142,0.20);
}

/* ── Sidebar styling ───────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e1e2f 0%, #2d2d44 100%);
}
section[data-testid="stSidebar"] * {
    color: #e0e0e0 !important;
}
section[data-testid="stSidebar"] .stExpander {
    border-color: rgba(255,255,255,0.08) !important;
}

/* ── Example question buttons ──────────────────────────────── */
.stButton > button {
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.12) !important;
}

/* ── Dataframe styling ─────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────────────────────────────────────
if "query_history" not in st.session_state:
    st.session_state.query_history = []

if "current_question" not in st.session_state:
    st.session_state.current_question = ""


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗂️ Schema Browser")
    st.caption("Explore the database tables to know what you can ask about.")

    if os.path.exists(DB_PATH):
        try:
            table_summaries = get_table_summaries(DB_PATH)
            for table_name, columns in table_summaries.items():
                with st.expander(f"📋 {table_name}", expanded=False):
                    for col in columns:
                        fk_badge = ""
                        if col.get("fk"):
                            fk_badge = f" → `{col['fk']['table']}.{col['fk']['to']}`"
                        pk_badge = " 🔑" if col.get("pk") else ""
                        st.markdown(
                            f"**{col['name']}** `{col['type']}`{pk_badge}{fk_badge}"
                        )
        except Exception as e:
            st.error(f"Could not load schema: {e}")
    else:
        st.warning("Database not found. Run `python db/setup_db.py` first.")

    st.markdown("---")
    st.markdown("## 💡 Example Questions")
    st.caption("Click any question to try it out.")

    EXAMPLES = [
        "Which students have CGPA above 8.5?",
        "Top 3 companies by average package",
        "How many students got placed in each branch?",
        "List students who haven't been placed yet",
        "What is the average CGPA per city?",
    ]

    for example in EXAMPLES:
        if st.button(example, key=f"ex_{example}", use_container_width=True):
            st.session_state.current_question = example

    st.markdown("---")
    st.markdown("## 📜 Query History")

    if st.session_state.query_history:
        for i, entry in enumerate(reversed(st.session_state.query_history)):
            idx = len(st.session_state.query_history) - i
            with st.expander(f"#{idx}: {entry['question'][:50]}…", expanded=False):
                st.code(entry["sql"], language="sql")
                if entry.get("blocked"):
                    st.error(f"⚠️ {entry['reason']}")
                else:
                    st.success(f"{entry.get('rows', 0)} rows returned")
    else:
        st.caption("No queries yet — ask something!")


# ─────────────────────────────────────────────────────────────────────────────
# Main content area
# ─────────────────────────────────────────────────────────────────────────────

# Hero header
st.markdown(
    '<div class="hero-header">'
    "<h1>🎓 Conversational SQL Query Generator</h1>"
    "<p>Ask questions about college placements in plain English — "
    "get validated SQL queries &amp; results instantly.</p>"
    "</div>",
    unsafe_allow_html=True,
)

# ── API key check ────────────────────────────────────────────────────────────
if not os.environ.get("GROQ_API_KEY"):
    st.warning(
        "⚠️ **GROQ_API_KEY not found.**  \n"
        "Set it as an environment variable or add it to a `.env` file in the project root.  \n"
        "Get a free key at [console.groq.com/keys](https://console.groq.com/keys)."
    )

# ── DB existence check ──────────────────────────────────────────────────────
if not os.path.exists(DB_PATH):
    st.error(
        "🗄️ **Database not found.**  \n"
        "Run `python db/setup_db.py` to generate the sample database."
    )
    st.stop()

# ── Question input ───────────────────────────────────────────────────────────
col_input, col_btn = st.columns([5, 1])

with col_input:
    question = st.text_input(
        "Ask a question about the placements database:",
        value=st.session_state.current_question,
        placeholder="e.g., Which branch has the highest average package?",
        label_visibility="collapsed",
        key="question_input",
    )

with col_btn:
    run_clicked = st.button("🚀 Run Query", type="primary", use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Query pipeline
# ─────────────────────────────────────────────────────────────────────────────
if run_clicked and question and question.strip():
    # Reset the pre-filled value so it doesn't persist after run
    st.session_state.current_question = ""

    # ── Step 1: Schema context ──────────────────────────────────────────────
    with st.spinner("📖 Reading database schema…"):
        try:
            schema_context = get_schema_context(DB_PATH)
        except Exception as e:
            st.error(f"Failed to read schema: {e}")
            st.stop()

    # ── Step 2: Generate SQL ────────────────────────────────────────────────
    with st.spinner("🤖 Generating SQL query via LLM…"):
        try:
            raw_sql = generate_sql(question, schema_context)
        except ValueError as e:
            st.error(f"⚙️ Configuration error: {e}")
            st.stop()
        except RuntimeError as e:
            st.error(f"🌐 LLM API error: {e}")
            st.stop()

    # ── Step 3: Sanitize ────────────────────────────────────────────────────
    clean_sql = sanitize_sql(raw_sql)

    # ── Step 4: Validate ────────────────────────────────────────────────────
    is_valid, validation_msg = validate_sql(clean_sql)

    if not is_valid:
        # Show blocked state
        st.markdown(
            f'<div class="blocked-badge">⚠️ Query Blocked — {validation_msg}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("#### Generated SQL (blocked)")
        st.code(clean_sql or raw_sql, language="sql")

        # Record in history
        st.session_state.query_history.append(
            {
                "question": question,
                "sql": clean_sql or raw_sql,
                "blocked": True,
                "reason": validation_msg,
            }
        )
        st.stop()

    # ── Step 5: Execute ─────────────────────────────────────────────────────
    st.markdown('<div class="success-badge">✅ Query validated & executed</div>', unsafe_allow_html=True)

    # Show the SQL
    st.markdown("#### 🔍 Generated SQL")
    st.code(clean_sql, language="sql")

    # Explain the query
    with st.spinner("💬 Generating explanation…"):
        try:
            explanation = explain_query(clean_sql, question)
            st.markdown(f"**📝 Explanation:** {explanation}")
        except Exception:
            pass  # Explanation is a nice-to-have, don't block on failure

    # Execute
    with st.spinner("⚡ Running query…"):
        try:
            df = execute_query(DB_PATH, clean_sql)
        except Exception as e:
            st.error(f"Query execution failed: {e}")
            st.session_state.query_history.append(
                {
                    "question": question,
                    "sql": clean_sql,
                    "blocked": False,
                    "rows": 0,
                }
            )
            st.stop()

    # ── Step 6: Display results ─────────────────────────────────────────────
    st.markdown("#### 📊 Results")

    if df.empty:
        st.info("The query returned no results.")
    else:
        st.markdown(f"*{len(df)} row(s) returned*")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Auto-chart
        if should_show_chart(df):
            st.markdown("#### 📈 Visualization")
            try:
                chart_type, chart_df = get_chart_data(df)
                if chart_type == "bar":
                    st.bar_chart(chart_df)
                else:
                    st.line_chart(chart_df)
            except Exception:
                pass  # Chart is optional — don't error out

    # Record in history
    st.session_state.query_history.append(
        {
            "question": question,
            "sql": clean_sql,
            "blocked": False,
            "rows": len(df),
        }
    )

elif run_clicked:
    st.warning("Please enter a question first.")


# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center; opacity:0.5; font-size:0.85rem;">'
    "Built with Streamlit · Powered by Groq (Llama 3.3 70B) · "
    '<a href="https://github.com/Shrauh/text-to-sql-generator" style="opacity:0.7;">GitHub</a>'
    "</p>",
    unsafe_allow_html=True,
)
