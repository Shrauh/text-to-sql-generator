"""
Schema extraction module for SQLite databases.

This module provides programmatic extraction of database schemas rather than
relying on hardcoded schema strings. Programmatic extraction is superior because
it ensures the schema context provided to the LLM is always accurate, up-to-date,
and automatically adapts to any underlying database migrations or structural changes
without requiring code updates.
"""

import sqlite3
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def _get_tables(cursor: sqlite3.Cursor) -> List[str]:
    """
    Retrieve a list of all user tables in the database.
    
    Args:
        cursor: SQLite cursor object.
        
    Returns:
        List of table names.
    """
    # Using PRAGMA table_list if available, fallback to sqlite_master
    try:
        cursor.execute("PRAGMA table_list;")
        # table_list returns (schema, name, type, ncol, wr, strict)
        tables = []
        for row in cursor.fetchall():
            schema, name, type_, *_ = row
            if schema == 'main' and type_ == 'table' and not name.startswith('sqlite_'):
                tables.append(name)
        return tables
    except sqlite3.OperationalError:
        # Fallback for older SQLite versions
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        return [row[0] for row in cursor.fetchall()]

def _get_table_info(cursor: sqlite3.Cursor, table_name: str) -> List[Dict[str, Any]]:
    """
    Retrieve column information for a specific table.
    
    Args:
        cursor: SQLite cursor object.
        table_name: Name of the table.
        
    Returns:
        List of dictionaries containing column details.
    """
    cursor.execute(f"PRAGMA table_info('{table_name}');")
    # table_info returns (cid, name, type, notnull, dflt_value, pk)
    columns = []
    for row in cursor.fetchall():
        columns.append({
            'name': row[1],
            'type': row[2],
            'notnull': bool(row[3]),
            'dflt_value': row[4],
            'pk': bool(row[5])
        })
    return columns

def _get_foreign_keys(cursor: sqlite3.Cursor, table_name: str) -> Dict[str, Dict[str, str]]:
    """
    Retrieve foreign key relationships for a specific table.
    
    Args:
        cursor: SQLite cursor object.
        table_name: Name of the table.
        
    Returns:
        Dictionary mapping local column names to dict with 'table' and 'to' (target column).
    """
    cursor.execute(f"PRAGMA foreign_key_list('{table_name}');")
    # foreign_key_list returns (id, seq, table, from, to, on_update, on_delete, match)
    foreign_keys = {}
    for row in cursor.fetchall():
        local_col = row[3]
        foreign_keys[local_col] = {
            'table': row[2],
            'to': row[4]
        }
    return foreign_keys

def get_schema_info(db_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Introspect the SQLite database and extract its full schema structure.
    
    Extracts tables, columns, primary keys, and foreign keys. This programmatic
    approach prevents schema drift between the actual database and the LLM context.
    
    Args:
        db_path: Path to the SQLite database file.
        
    Returns:
        Dictionary mapping table names to their structural information.
        
    Raises:
        sqlite3.Error: If there's an issue connecting to or querying the database.
    """
    schema_info = {}
    
    try:
        # Use context manager to ensure connection is properly closed
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            tables = _get_tables(cursor)
            
            for table in tables:
                columns = _get_table_info(cursor, table)
                foreign_keys = _get_foreign_keys(cursor, table)
                
                # Merge foreign key info into column definitions for easier processing
                for col in columns:
                    if col['name'] in foreign_keys:
                        col['fk'] = foreign_keys[col['name']]
                    else:
                        col['fk'] = None
                        
                schema_info[table] = {
                    'columns': columns
                }
                
    except sqlite3.Error as e:
        logger.error(f"Database error while extracting schema from {db_path}: {e}")
        raise
        
    return schema_info

def format_schema_for_llm(schema_info: Dict[str, Dict[str, Any]]) -> str:
    """
    Format the extracted schema dictionary into a readable text representation.
    
    This function structures the raw schema data into a clean, intuitive text
    format optimized for LLM comprehension. Providing a well-formatted schema
    improves the LLM's ability to generate syntactically correct and contextually
    accurate SQL queries.
    
    Args:
        schema_info: Structured schema information returned by get_schema_info.
        
    Returns:
        Formatted text description of the database schema.
    """
    formatted_schema = []
    
    for table_name, table_data in schema_info.items():
        formatted_schema.append(f"Table: {table_name}")
        formatted_schema.append("Columns:")
        
        for col in table_data['columns']:
            col_name = col['name']
            col_type = col['type']
            
            constraints = []
            if col['pk']:
                constraints.append("PRIMARY KEY")
            
            if col['fk']:
                fk_target = f"{col['fk']['table']}.{col['fk']['to']}"
                constraints.append(f"FOREIGN KEY -> {fk_target}")
                
            type_and_constraints = col_type
            if constraints:
                type_and_constraints += f", {', '.join(constraints)}"
                
            formatted_schema.append(f"  - {col_name} ({type_and_constraints})")
            
        formatted_schema.append("") # Empty line between tables
        
    return "\n".join(formatted_schema).strip()

def get_schema_context(db_path: str) -> str:
    """
    Convenience function to get the formatted schema string directly from a database.
    
    Args:
        db_path: Path to the SQLite database file.
        
    Returns:
        Formatted text description of the database schema suitable for LLM prompts.
    """
    schema_info = get_schema_info(db_path)
    return format_schema_for_llm(schema_info)

def get_table_summaries(db_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract a simplified schema representation for UI consumption.
    
    Args:
        db_path: Path to the SQLite database file.
        
    Returns:
        Dictionary mapping table names to lists of column information dictionaries,
        suitable for display in interfaces like Streamlit sidebars.
    """
    schema_info = get_schema_info(db_path)
    
    summaries = {}
    for table_name, table_data in schema_info.items():
        summaries[table_name] = table_data['columns']
        
    return summaries
