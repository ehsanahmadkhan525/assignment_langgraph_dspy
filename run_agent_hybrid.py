import click
import json
import dspy
import os
from dotenv import load_dotenv
from agent.graph_hybrid import HybridAgent
from typing import List, Dict

# Load environment variables for LangSmith tracing
load_dotenv()

@click.command()
@click.option('--batch', required=True, help='Path to input JSONL file')
@click.option('--out', required=True, help='Path to output JSONL file')
def run(batch, out):
    """Run the Retail Analytics Copilot."""
    
    # Setup DSPy with Ollama (DSPy 3.x syntax)
    lm = dspy.LM(model='ollama/phi3.5:3.8b-mini-instruct-q4_K_M', api_base='http://localhost:11434')
    
    # OpenAI configuration (faster, but requires API key)
    # lm = dspy.LM(model='gpt-4o-mini', max_tokens=2000)
            
    dspy.configure(lm=lm)
    
    # Initialize Agent
    db_path = "data/northwind.sqlite"
    docs_dir = "docs"
    agent = HybridAgent(db_path, docs_dir)
    
    results = []
    
    with open(batch, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            question_id = item['id']
            question = item['question']
            format_hint = item['format_hint']
            
            print(f"Processing: {question_id}")
            
            initial_state = {
                "question": question,
                "format_hint": format_hint,
                "strategy": "",
                "context": [],
                "plan": {},
                "sql_query": "",
                "sql_result": {},
                "final_answer": None,
                "citations": [],
                "explanation": "",
                "errors": [],
                "repair_count": 0
            }
            
            final_state = agent.graph.invoke(initial_state)
            
            output_item = {
                "id": question_id,
                "final_answer": final_state.get("final_answer"),
                "sql": final_state.get("sql_query", ""),
                "confidence": 1.0 if not final_state.get("errors") else 0.5, # Simple heuristic
                "explanation": final_state.get("explanation", ""),
                "citations": final_state.get("citations", [])
            }
            
            results.append(output_item)
            
    # Write results
    with open(out, 'w') as f:
        for item in results:
            f.write(json.dumps(item) + "\n")
            
    print(f"Done. Results written to {out}")

if __name__ == '__main__':
    run()
