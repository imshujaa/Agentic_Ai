import os
import requests
from tqdm import tqdm
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from whoosh.index import open_dir, exists_in
from whoosh.query import Or, Term
from whoosh.highlight import highlight, HtmlFormatter, SentenceFragmenter

# --- Configuration ---
INDEX_DIR = "indexdir"

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# Global variable to hold the search index
ix = None

# --- Gemini API Configuration ---
API_KEY = "AIzaSyCe-ng_tvZ36ImJLTI_-KvX07R5vvm42ig"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"


def get_refined_queries(user_query):
    """
    Uses the Gemini API to generate refined search queries based on the user's input.
    """
    if not API_KEY:
        print("WARNING: GEMINI_API_KEY environment variable not set. Skipping query refinement.")
        return []

    system_prompt = (
        "You are an expert search query refinement agent. Your goal is to help a user find the most relevant "
        "documents from a large text corpus. Based on the user's query, generate a JSON object containing a "
        "list of three alternative, more specific search queries. Decompose the original query, add synonyms, "
        "or rephrase it to cover different aspects of the user's intent. The list should be named 'refined_queries'. "
        "Return ONLY the JSON object and nothing else."
    )

    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": { "responseMimeType": "application/json" }
    }

    try:
        response = requests.post(GEMINI_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        json_text = data['candidates'][0]['content']['parts'][0]['text']
        refined_data = json.loads(json_text)
        queries = refined_data.get("refined_queries", [])
        
        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            return queries
        else:
            print(f"Warning: LLM returned unexpected format: {queries}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"Error parsing Gemini API response: {e}")
        print(f"Raw response: {response.text}")
    
    return []

def load_index():
    """
    Loads the pre-built search index. If the index is not found, it exits with an error.
    """
    global ix
    if not os.path.exists(INDEX_DIR) or not exists_in(INDEX_DIR):
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"FATAL: Index directory '{INDEX_DIR}' not found or is invalid.")
        print("Please run the 'create_index.py' script first to build the search index.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        os._exit(1)
    
    print(f"Opening existing index at '{INDEX_DIR}'...")
    ix = open_dir(INDEX_DIR)
    print(f"SUCCESS: Index loaded and contains {ix.doc_count()} documents.")


@app.route('/')
def serve_frontend():
    """Serves the index.html file."""
    return send_from_directory('.', 'index.html')


@app.route('/search', methods=['POST'])
def search():
    if not ix:
        return jsonify({"error": "Index is not available."}), 500

    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Query not provided."}), 400

    original_query = data['query']
    print(f"\n--- NEW SEARCH ---")
    print(f"Received original query: {original_query}")

    refined_queries = get_refined_queries(original_query)
    print(f"Agent refined queries: {refined_queries}")

    all_queries = [original_query] + refined_queries
    unique_results = {}

    try:
        with ix.searcher() as searcher:
            analyzer = ix.schema["content"].analyzer
            original_query_tokens = {token.text for token in analyzer(original_query)}
            
            for q_str in all_queries:
                if not q_str: continue
                
                try:
                    tokens = [token.text for token in analyzer(q_str)]
                    if not tokens: continue
                    term_queries = [Term("content", token) for token in tokens]
                    query = Or(term_queries)
                except Exception as e:
                    print(f"Warning: Could not build query for '{q_str}'. Error: {e}. Skipping.")
                    continue 
                
                results = searcher.search(query, limit=10)
                
                print(f"  -> Query '{q_str}' found {len(results)} results.")
                
                for hit in results:
                    if hit['path'] not in unique_results:
                        
                        # This will create a snippet with matching words wrapped in HTML tags.
                        snippet = highlight(
                            hit['content'],
                            original_query_tokens,
                            analyzer,
                            fragmenter=SentenceFragmenter(maxchars=200),
                            formatter=HtmlFormatter(),
                            top=1
                        )
                        if not snippet:
                            # If no highlights, fall back to a plain text snippet
                            snippet = hit['content'][:250] + "..."

                        unique_results[hit['path']] = {
                            "path": hit['path'],
                            "score": hit.score,
                            "snippet": snippet,
                        }

        sorted_results = sorted(unique_results.values(), key=lambda item: item['score'], reverse=True)

        return jsonify({
            "original_query": original_query,
            "refined_queries": refined_queries,
            "documents": sorted_results[:20]
        })

    except Exception as e:
        print(f"An error occurred during search: {e}")
        return jsonify({"error": "An error occurred during search."}), 500


if __name__ == '__main__':
    print("--- Autonomous Query Refinement Agent ---")
    load_index()
    print("Backend is ready. Starting Flask server...")
    app.run(host='0.0.0.0', port=5000)

