import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional

class SQLiteTool:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_schema(self) -> str:
        """Returns the schema of the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        schema_str = ""
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            schema_str += f"Table: {table_name}\n"
            
            # Get columns for each table
            cursor.execute(f"PRAGMA table_info('{table_name}');")
            columns = cursor.fetchall()
            
            for col in columns:
                # cid, name, type, notnull, dflt_value, pk
                schema_str += f"  - {col[1]} ({col[2]})\n"
            schema_str += "\n"
            
        conn.close()
        return schema_str

    def execute_query(self, query: str) -> Dict[str, Any]:
        """Executes a SQL query and returns the results."""
        conn = sqlite3.connect(self.db_path)
        try:
            df = pd.read_sql_query(query, conn)
            return {
                "columns": list(df.columns),
                "rows": df.to_dict(orient="records"),
                "error": None
            }
        except Exception as e:
            return {
                "columns": [],
                "rows": [],
                "error": str(e)
            }
        finally:
            conn.close()
