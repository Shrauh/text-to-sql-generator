import os
import logging
from typing import Optional

try:
    import groq
    from groq import Groq
except ImportError:
    pass

logger = logging.getLogger(__name__)

def _get_client() -> "Groq":
    """
    Initializes and returns the Groq API client.
    
    Raises:
        ValueError: If GROQ_API_KEY environment variable is not set.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set. Please set it to use the SQL generator.")
    return Groq(api_key=api_key)

def generate_sql(question: str, schema_context: str, model: str = 'llama-3.3-70b-versatile') -> str:
    """
    Converts a natural language question into a SQLite SQL query using the Groq API.
    
    Args:
        question (str): The natural language question to translate.
        schema_context (str): The database schema context to guide the SQL generation.
        model (str, optional): The LLM model to use. Defaults to 'llama-3.3-70b-versatile'.
        
    Returns:
        str: The generated raw SQL query.
        
    Raises:
        ValueError: If the GROQ_API_KEY is not set.
        RuntimeError: If there is an error communicating with the Groq API.
    """
    client = _get_client()
    
    system_prompt = (
        "You are an expert SQLite SQL developer. Your task is to translate a natural language question into a single valid SQLite SELECT query.\n\n"
        "SCHEMA CONTEXT:\n"
        f"{schema_context}\n\n"
        "RULES:\n"
        "1. Output ONLY the raw SQL query. Do NOT include markdown formatting, backticks, or code blocks.\n"
        "2. Do NOT include any explanations, preambles, or postscripts.\n"
        "3. Use valid SQLite syntax. Pay attention to SQLite-specific date/time functions and string concatenations if needed.\n"
        "4. The query must be a valid SELECT statement."
    )
    
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            model=model,
            temperature=0.0,
        )
        
        # Extract and clean up the SQL
        sql_output = response.choices[0].message.content or ""
        
        # Strip common markdown blocks just in case the model ignores instructions
        sql_output = sql_output.strip()
        if sql_output.startswith("```sql"):
            sql_output = sql_output[6:]
        elif sql_output.startswith("```"):
            sql_output = sql_output[3:]
        if sql_output.endswith("```"):
            sql_output = sql_output[:-3]
            
        return sql_output.strip()
        
    except groq.APIConnectionError as e:
        raise RuntimeError(f"Network error while connecting to Groq API: {e}") from e
    except groq.RateLimitError as e:
        raise RuntimeError(f"Groq API rate limit exceeded: {e}") from e
    except groq.APIStatusError as e:
        raise RuntimeError(f"Groq API returned an error status ({e.status_code}): {e.response.text}") from e
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred during SQL generation: {e}") from e

def explain_query(sql: str, question: str, model: str = 'llama-3.3-70b-versatile') -> str:
    """
    Provides a plain English explanation of a SQL query based on the original question.
    
    Args:
        sql (str): The SQL query to explain.
        question (str): The original natural language question.
        model (str, optional): The LLM model to use. Defaults to 'llama-3.3-70b-versatile'.
        
    Returns:
        str: A one-line plain English explanation of the SQL query.
        
    Raises:
        ValueError: If the GROQ_API_KEY is not set.
        RuntimeError: If there is an error communicating with the Groq API.
    """
    client = _get_client()
    
    system_prompt = (
        "You are a helpful data analyst. Given a user's question and a corresponding SQL query, "
        "provide a ONE-LINE plain English explanation of what the SQL query is doing to answer the question.\n"
        "Keep it concise, user-friendly, and strictly on a single line. Do not explain SQL syntax, just the business logic."
    )
    
    user_message = f"Question: {question}\nSQL: {sql}\n\nPlease provide the one-line explanation."
    
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            model=model,
            temperature=0.0,
        )
        
        explanation = response.choices[0].message.content or ""
        # Ensure it's a single line by replacing newlines
        return explanation.strip().replace("\n", " ")
        
    except groq.APIConnectionError as e:
        raise RuntimeError(f"Network error while connecting to Groq API: {e}") from e
    except groq.RateLimitError as e:
        raise RuntimeError(f"Groq API rate limit exceeded: {e}") from e
    except groq.APIStatusError as e:
        raise RuntimeError(f"Groq API returned an error status ({e.status_code}): {e.response.text}") from e
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred during explanation generation: {e}") from e
