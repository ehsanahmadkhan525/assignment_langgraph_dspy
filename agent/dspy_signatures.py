import dspy
from typing import List, Optional

class Router(dspy.Signature):
    """Classify the user query to determine the best strategy: 'rag', 'sql', or 'hybrid'."""
    
    question = dspy.InputField(desc="The user's question about retail analytics.")
    strategy = dspy.OutputField(desc="The best strategy: 'rag' (policy/marketing docs), 'sql' (database queries), or 'hybrid' (requires both docs and db).")

class Planner(dspy.Signature):
    """Extract constraints and entities from the question to plan the SQL query."""
    
    question = dspy.InputField(desc="The user's question.")
    context = dspy.InputField(desc="Relevant context from retrieved documents.")
    date_range = dspy.OutputField(desc="Date range mentioned or implied (e.g., '1997-06-01 to 1997-06-30'), or 'None'.")
    entities = dspy.OutputField(desc="List of relevant entities (categories, products, customers) to filter by.")
    kpi_formula = dspy.OutputField(desc="Relevant KPI formula or definition from context, if any.")

class SQLGenerator(dspy.Signature):
    """Generate a SQLite query based on the question, schema, and plan."""
    
    question = dspy.InputField(desc="The user's question.")
    db_schema = dspy.InputField(desc="The database schema (tables and columns).")
    plan = dspy.InputField(desc="Constraints and entities extracted from the question/docs.")
    sql_query = dspy.OutputField(desc="The SQLite query to answer the question. Must be valid SQLite.")

class Synthesizer(dspy.Signature):
    """Synthesize the final answer based on the question, SQL results, and retrieved context."""
    
    question = dspy.InputField(desc="The user's question.")
    sql_query = dspy.InputField(desc="The executed SQL query, if any.")
    sql_result = dspy.InputField(desc="The result of the SQL query (columns and rows).")
    context = dspy.InputField(desc="Retrieved context from documents.")
    format_hint = dspy.InputField(desc="The expected format of the answer (e.g., 'int', 'float', '{category:str, quantity:int}').")
    
    final_answer = dspy.OutputField(desc="The final answer matching the format_hint.")
    explanation = dspy.OutputField(desc="A brief explanation (<= 2 sentences).")
    citations = dspy.OutputField(desc="List of DB tables used and doc chunk IDs referenced.")
