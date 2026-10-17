import requests
import chromadb
from chromadb.utils import embedding_functions

# ============================================================
# OLLAMA CONFIGURATION
# ============================================================
OLLAMA_CHAT_URL = "http://localhost:11434/v1/chat/completions"
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
OLLAMA_MODEL = "qwen2.5:7b"

# ============================================================
# CHROMADB INITIALIZATION
# ============================================================
print("[SYSTEM] Initializing ChromaDB Persistent Client...")
chroma_client = chromadb.PersistentClient(path="./chroma_db")

print("[SYSTEM] Connecting to Ollama for Embeddings (all-minilm)...")
ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    url=OLLAMA_EMBED_URL,
    model_name="all-minilm"
)

# Collection name aligned with build_mock_db.py
collection = chroma_client.get_or_create_collection(
    name="fssai_rules",
    embedding_function=ollama_ef
)

# ============================================================
# VECTOR RETRIEVAL
# ============================================================
def query_regulation(rule_id: str, n_results: int = 3) -> list:
    """
    Queries ChromaDB for the relevant FSSAI regulation using Ollama embeddings.
    """
    try:
        query_text = rule_id.replace("_", " ")
        if collection.count() == 0:
            print("[RAG WARNING] ChromaDB collection is empty! Did you run build_mock_db.py?")
            return []
            
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        if not results.get("documents") or not results["documents"][0]:
            return []
            
        docs = []
        for i in range(len(results["documents"][0])):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            docs.append({
                "clause": metadata.get("clause", "FSSAI Statutory Standard"),
                "text": results["documents"][0][i]
            })
        return docs
    except Exception as e:
        print(f"[RAG ERROR] ChromaDB query failed for rule '{rule_id}': {e}")
        return []

# ============================================================
# LEGAL SYNTHESIS GENERATOR
# ============================================================
def generate_legal_justification(audit_result: dict, context: list) -> str:
    """
    Synthesizes grounded legal explanations for PASS, REVIEW, and FLAGGED statuses
    using Ollama's OpenAI-compatible chat endpoint.
    """
    if context:
        legal_text = "\n".join([f"- {doc['clause']}: {doc['text']}" for doc in context])
    else:
        legal_text = "- FSSAI General Principles: General labelling standards and claim validation requirements apply."

    status = audit_result.get("status", "REVIEW")
    
    system_prompt = (
        "You are an expert FSSAI regulatory compliance officer. "
        "Your task is to provide a concise, highly professional audit statement based STRICTLY on the "
        "provided Audit Evidence and Retrieved FSSAI Legal Context.\n\n"
        "Guidelines per status:\n"
        "- If FLAGGED: State the exact regulatory violation and mathematical threshold overrun.\n"
        "- If PASS: Formulate a Compliance Affirmation stating why the claim is legally valid under the standard.\n"
        "- If REVIEW: Explain why automated verification is incomplete and specify the required statutory documentation.\n\n"
        "Do not hallucinate sections or rules outside the provided context. Output a single cohesive paragraph."
    )
    
    user_prompt = f"""Claim: {audit_result.get('claim')}
Audit Status: {status}
Rule ID: {audit_result.get('rule_id')}

Mathematical & Audit Evidence:
{audit_result.get('evidence')}

Retrieved FSSAI Legal Context:
{legal_text}

Generate the formal audit statement:"""

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=180)
        response.raise_for_status()
        
        response_json = response.json()
        choices = response_json.get("choices", [])
        if choices and "message" in choices[0]:
            return choices[0]["message"].get("content", "").strip()
        return "Synthesis complete, but response payload was empty."
    except requests.exceptions.RequestException as e:
        return f"Error connecting to local LLM synthesizer: {str(e)}"