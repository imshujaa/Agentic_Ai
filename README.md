**Agentic AI for Information Retrieval: An Autonomous Query Refinement System**

This project is a fully functional prototype of an agentic Information Retrieval (IR) system, developed for the Information Retrieval course at the Università degli Studi di Napoli Federico II (A.Y. 2024-25).

The system addresses the long-standing vocabulary mismatch problem in search. Instead of relying on the user to find the perfect keywords, this application uses a Large Language Model (LLM) as an intelligent agent to autonomously refine the user's query, leading to significantly more relevant search results.

**Key Features**
Agentic Query Refinement: Uses the Google Gemini API to analyze a user's query and generate three semantically diverse, alternative queries.

Multi-Query Search: Executes searches for the original query plus all agent-generated queries to improve both precision and recall.

Transparent Agent Reasoning: The user interface includes an "Agent Insights" panel that explicitly shows the user the refined queries, making the AI's reasoning process clear.

Robust Architecture: Employs a decoupled, two-script architecture to separate the heavy, one-time indexing process from the lightweight web application.

Large-Scale Data: Designed to work with the large and complex OpenWebText corpus.

**System Architecture**
The project uses a two-script design to ensure the user-facing application is fast and responsive.

create_index.py (The Indexer): A standalone script that is run only once. Its job is to read the entire raw OpenWebText corpus from your local machine, process the nested .tar.xz archives, and build a highly optimized search index using the Whoosh library.

app.py (The Web Server): A lightweight Flask application that loads the pre-built index. It serves the frontend UI and provides a /search API endpoint that orchestrates the agentic query refinement and retrieval workflow.

**Technology Stack**
Backend: Python 3, Flask, Whoosh

Frontend: HTML, Tailwind CSS, Vanilla JavaScript

AI Agent: Google Gemini API

Libraries: requests, tqdm, tarfile
