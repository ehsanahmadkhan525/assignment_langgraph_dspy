# Retail Analytics Copilot

A local, privacy-focused AI agent that answers retail analytics questions using a hybrid approach combining RAG (Retrieval-Augmented Generation) over documents and SQL queries over a SQLite database.

## Architecture

### Graph Design
The agent uses LangGraph to orchestrate a multi-node workflow:

1. **Router**: Classifies queries as `rag`, `sql`, or `hybrid` using DSPy ChainOfThought
2. **Retriever**: TF-IDF-based document retrieval from markdown files in `docs/`
3. **Planner**: Extracts constraints (dates, entities, KPI formulas) from retrieved context
4. **SQL Generator**: Converts natural language to SQLite queries using schema introspection
5. **Executor**: Runs SQL queries and captures results/errors
6. **Synthesizer**: Produces typed answers with citations matching the required format
7. **Repair Loop**: Retries up to 2 times on SQL errors or invalid outputs

### Flow Paths
- **RAG-only**: Router → Retriever → Synthesizer
- **SQL-only**: Router → SQL Generator → Executor → Synthesizer  
- **Hybrid**: Router → Retriever → Planner → SQL Generator → Executor → Synthesizer

## DSPy Optimization

**Module Optimized**: Router (query classification)

The Router module uses DSPy's ChainOfThought to classify incoming questions into one of three strategies. The optimization approach would involve:

- Creating a training set of 20-40 labeled examples
- Using `BootstrapFewShot` or `MIPROv2` to optimize prompts
- Measuring classification accuracy before/after optimization

**Expected Improvement**: 15-25% increase in correct strategy selection, reducing unnecessary retrieval or SQL generation steps.

## Key Implementation Details

### Database
- **Northwind SQLite**: Classic retail database with Orders, Products, Customers, etc.
- **Schema Introspection**: Dynamic schema loading via `PRAGMA table_info`
- **Compatibility Views**: Created lowercase views for simpler SQL generation

### Retrieval
- **TF-IDF Vectorization**: Using scikit-learn for document chunking and similarity search
- **Chunk IDs**: Format `{filename}::chunk{N}` for citation tracking
- **Top-K Retrieval**: Returns top 3 relevant chunks with similarity scores

### LLM Integration
- **Primary**: OpenAI GPT-4o-mini (fast, cost-effective)
- **Alternative**: Phi-3.5-mini-instruct via Ollama (commented out, local option)
- **DSPy LM**: Uses `dspy.LM` with OpenAI backend
- **Tracing**: LangSmith integration for debugging and observability

### Citations
All answers include:
- **DB Tables**: Every table accessed during SQL execution
- **Doc Chunks**: Every document chunk used in planning/synthesis

### Assumptions
- **Cost of Goods**: Approximated as 70% of UnitPrice when not available in the database
- **Date Parsing**: Relies on LLM to extract date ranges from marketing calendar
- **Confidence Scoring**: Simple heuristic based on error presence (1.0 if no errors, 0.5 otherwise)

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Download database
mkdir -p data
curl -L -o data/northwind.sqlite \
  https://raw.githubusercontent.com/jpwhite3/northwind-SQLite3/main/dist/northwind.db

# Create compatibility views
sqlite3 data/northwind.sqlite <<'SQL'
CREATE VIEW IF NOT EXISTS orders AS SELECT * FROM Orders;
CREATE VIEW IF NOT EXISTS order_items AS SELECT * FROM "Order Details";
CREATE VIEW IF NOT EXISTS products AS SELECT * FROM Products;
CREATE VIEW IF NOT EXISTS customers AS SELECT * FROM Customers;
SQL

# Set up environment variables
# Add OPENAI_API_KEY to .env file
```

## Usage

```bash
python run_agent_hybrid.py \
  --batch sample_questions_hybrid_eval.jsonl \
  --out outputs_hybrid.jsonl
```

## Output Format

Each line in `outputs_hybrid.jsonl`:

```json
{
  "id": "question_id",
  "final_answer": <typed_value>,
  "sql": "SELECT ...",
  "confidence": 0.0-1.0,
  "explanation": "Brief explanation",
  "citations": ["Orders", "Products", "kpi_definitions::chunk0"]
}
```

## Trade-offs

- **OpenAI vs Ollama**: Using OpenAI for speed and reliability. Ollama code is preserved (commented) for local/offline use.
- **Simple Chunking**: Using paragraph-based chunking instead of markdown-aware parsing for simplicity.
- **Basic Confidence**: Heuristic-based confidence scoring rather than calibrated probabilities.
