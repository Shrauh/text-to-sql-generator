import sqlite3
import os
import pandas as pd
from typing import Tuple

def execute_query(db_path: str, sql: str, row_limit: int = 500) -> pd.DataFrame:
    """
    Executes a SQL query against a SQLite database in read-only mode and returns a pandas DataFrame.
    
    Using a read-only connection (mode=ro) acts as defense-in-depth to ensure 
    no destructive operations (INSERT, UPDATE, DELETE, DROP, etc.) can be performed 
    by the query execution, even if validation misses something.
    
    Args:
        db_path: Path to the SQLite database file.
        sql: The SQL query to execute.
        row_limit: Maximum number of rows to return (default 500).
        
    Returns:
        pd.DataFrame containing the query results.
        
    Raises:
        ValueError: If the database file does not exist.
        sqlite3.OperationalError: If there is an issue with the SQL syntax.
        sqlite3.DatabaseError: For other database issues.
    """
    if not os.path.exists(db_path):
        raise ValueError(f"Database file not found: {db_path}")

    # Use URI format to enforce read-only connection
    uri = f"file:{db_path}?mode=ro"
    
    try:
        # 5-second timeout for query execution
        with sqlite3.connect(uri, uri=True, timeout=5.0) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            
            # Fetch up to row_limit to ensure we cap the results
            rows = cursor.fetchmany(row_limit)
            
            # Extract column names from the cursor description
            columns = [description[0] for description in cursor.description] if cursor.description else []
            
            # Create and return the DataFrame
            df = pd.DataFrame(rows, columns=columns)
            return df
            
    except sqlite3.OperationalError as e:
        raise sqlite3.OperationalError(f"SQL Execution Error: {str(e)}. Please check your SQL syntax or database schema.") from e
    except sqlite3.DatabaseError as e:
        raise sqlite3.DatabaseError(f"Database Error: {str(e)}. The connection failed or the file is invalid.") from e


def should_show_chart(df: pd.DataFrame) -> bool:
    """
    Determines whether a chart should be displayed for the given DataFrame.
    
    Args:
        df: The pandas DataFrame to evaluate.
        
    Returns:
        bool: True if the DataFrame has 2-20 rows, at least one numeric column, 
              and at least one non-numeric column.
    """
    if df.empty:
        return False
        
    num_rows = len(df)
    if not (2 <= num_rows <= 20):
        return False
        
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) == 0:
        return False
        
    non_numeric_cols = df.select_dtypes(exclude=['number']).columns
    if len(non_numeric_cols) == 0:
        return False
        
    return True


def get_chart_data(df: pd.DataFrame) -> Tuple[str, pd.DataFrame]:
    """
    Prepares the DataFrame for charting and determines the best chart type.
    
    Args:
        df: The pandas DataFrame to prepare.
        
    Returns:
        A tuple containing the chart type ('line' or 'bar') and the prepared DataFrame.
    """
    chart_type = 'bar'
    
    datetime_cols = df.select_dtypes(include=['datetime', 'datetimetz']).columns
    if len(datetime_cols) > 0:
        chart_type = 'line'
        label_col = datetime_cols[0]
    else:
        # Fallback to the first non-numeric column if no datetime column exists
        non_numeric_cols = df.select_dtypes(exclude=['number']).columns
        label_col = non_numeric_cols[0]
        
        # Check if the chosen label column could be parsed as dates
        try:
            if len(df) > 0:
                val = str(df[label_col].iloc[0])
                if len(val) >= 8 and any(c.isdigit() for c in val):
                    # Quick test if it looks like a date/time
                    pd.to_datetime(df[label_col])
                    chart_type = 'line'
        except (ValueError, TypeError):
            pass
            
    # Prepare the dataframe by setting the index to the label column
    prepared_df = df.set_index(label_col)
    
    # Only keep numeric columns for the chart values to prevent plotting errors
    numeric_cols = prepared_df.select_dtypes(include=['number']).columns
    prepared_df = prepared_df[numeric_cols]
    
    return chart_type, prepared_df
