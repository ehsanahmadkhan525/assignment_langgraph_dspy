import os
import dspy
import json
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from agent.dspy_signatures import Router, Planner, SQLGenerator, Synthesizer
from agent.rag.retrieval import Retriever
from agent.tools.sqlite_tool import SQLiteTool

# Define the state
class AgentState(TypedDict):
    question: str
    format_hint: str
    strategy: str
    context: List[Dict]
    plan: Dict[str, Any]
    sql_query: str
    sql_result: Dict[str, Any]
    final_answer: Any
    citations: List[str]
    explanation: str
    errors: List[str]
    repair_count: int

class HybridAgent:
    def __init__(self, db_path: str, docs_dir: str):
        self.db_path = db_path
        self.docs_dir = docs_dir
        self.retriever = Retriever(docs_dir)
        self.sqlite_tool = SQLiteTool(db_path)
        
        # Initialize DSPy modules
        self.router = dspy.ChainOfThought(Router)
        self.planner = dspy.ChainOfThought(Planner)
        self.sql_generator = dspy.ChainOfThought(SQLGenerator)
        self.synthesizer = dspy.ChainOfThought(Synthesizer)
        
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("router", self.route_query)
        workflow.add_node("retriever", self.retrieve_docs)
        workflow.add_node("planner", self.plan_query)
        workflow.add_node("sql_generator", self.generate_sql)
        workflow.add_node("executor", self.execute_sql)
        workflow.add_node("synthesizer", self.synthesize_answer)
        workflow.add_node("repair", self.repair_step)
        
        workflow.set_entry_point("router")
        
        workflow.add_conditional_edges(
            "router",
            lambda state: state["strategy"],
            {
                "rag": "retriever",
                "sql": "sql_generator", # Skip retrieval for pure SQL? Or maybe just go to planner? Let's go to planner for consistency if needed, or straight to sql_generator if no docs needed. Actually, let's just go to sql_generator for pure SQL, but maybe planner is useful. Let's stick to the plan: Router -> (Retriever | Planner -> SQL -> Executor) -> Synthesizer.
                # Wait, the plan said: Router -> (Retriever | Planner -> SQL -> Executor) -> Synthesizer
                # If strategy is RAG: Router -> Retriever -> Synthesizer
                # If strategy is SQL: Router -> Planner (optional?) -> SQL -> Executor -> Synthesizer
                # If strategy is Hybrid: Router -> Retriever -> Planner -> SQL -> Executor -> Synthesizer
                "hybrid": "retriever"
            }
        )
        
        # RAG path
        workflow.add_edge("retriever", "planner") # For hybrid/rag, we might need planning.
        
        # Logic for after retriever
        def after_retriever(state):
            if state["strategy"] == "rag":
                return "synthesizer"
            return "planner"

        workflow.add_conditional_edges(
            "retriever",
            after_retriever,
            {
                "synthesizer": "synthesizer",
                "planner": "planner"
            }
        )
        
        # SQL/Hybrid path
        workflow.add_edge("planner", "sql_generator")
        workflow.add_edge("sql_generator", "executor")
        workflow.add_edge("executor", "synthesizer")
        
        # Repair loop
        def check_repair(state):
            if state.get("errors") and state["repair_count"] < 2:
                return "repair"
            return END
            
        workflow.add_conditional_edges("synthesizer", check_repair, {"repair": "repair", END: END})
        
        # Repair logic: if SQL error, go back to SQL generator. If format error, go back to Synthesizer?
        # For simplicity, let's route repair back to SQL generator if it was a SQL error, or Synthesizer if it was a format error.
        # But the node is "repair". Let's make "repair" a node that decides where to go or just updates state.
        # Actually, let's just have conditional edge from synthesizer.
        
        workflow.add_edge("repair", "sql_generator") # Simple repair: try generating SQL again.
        
        return workflow.compile()

    def route_query(self, state: AgentState):
        pred = self.router(question=state["question"])
        strategy = pred.strategy.lower()
        if strategy not in ["rag", "sql", "hybrid"]:
            strategy = "hybrid" # Default
        return {"strategy": strategy, "repair_count": 0, "errors": []}

    def retrieve_docs(self, state: AgentState):
        docs = self.retriever.retrieve(state["question"])
        return {"context": docs}

    def plan_query(self, state: AgentState):
        context_str = str(state.get("context", []))
        pred = self.planner(question=state["question"], context=context_str)
        return {"plan": {"date_range": pred.date_range, "entities": pred.entities, "kpi_formula": pred.kpi_formula}}

    def generate_sql(self, state: AgentState):
        schema = self.sqlite_tool.get_schema()
        plan_str = str(state.get("plan", {}))
        
        # If we are in repair mode, maybe add error context?
        # For now, simple generation.
        pred = self.sql_generator(question=state["question"], db_schema=schema, plan=plan_str)
        
        # Clean SQL (remove markdown blocks if present)
        sql = pred.sql_query.replace("```sql", "").replace("```", "").strip()
        return {"sql_query": sql}

    def execute_sql(self, state: AgentState):
        result = self.sqlite_tool.execute_query(state["sql_query"])
        if result["error"]:
            return {"sql_result": result, "errors": [result["error"]]}
        return {"sql_result": result}

    def synthesize_answer(self, state: AgentState):
        # Check if we have SQL errors
        if state.get("errors"):
             # If we have errors and haven't exhausted retries, we might want to skip synthesis or synthesize an error message?
             # But the edge logic handles the loop.
             pass

        pred = self.synthesizer(
            question=state["question"],
            sql_query=state.get("sql_query", ""),
            sql_result=str(state.get("sql_result", "")),
            context=str(state.get("context", [])),
            format_hint=state["format_hint"]
        )
        
        # Parse citations
        citations = pred.citations
        if isinstance(citations, str):
            try:
                citations = json.loads(citations)
            except:
                citations = [citations] # Fallback
        
        # Validate format (basic check)
        # In a real scenario, we'd do more robust validation here.
        
        return {
            "final_answer": pred.final_answer,
            "explanation": pred.explanation,
            "citations": citations
        }

    def repair_step(self, state: AgentState):
        # This node just increments the counter and maybe adjusts the prompt (not implemented here)
        return {"repair_count": state["repair_count"] + 1}
