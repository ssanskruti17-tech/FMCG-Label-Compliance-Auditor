import rag_engine
import chromadb
from chromadb.utils import embedding_functions

_is_initialized = False

def init_rag_system():
    global _is_initialized
    if _is_initialized:
        return
    
    try:
        print("[FASTAPI] Initializing RAG System...")
        rag_engine.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        rag_engine.ollama_ef = embedding_functions.OllamaEmbeddingFunction(
            url=rag_engine.OLLAMA_EMBED_URL,
            model_name="all-minilm"
        )
        rag_engine.collection = rag_engine.chroma_client.get_or_create_collection(
            name="fssai_rules",
            embedding_function=rag_engine.ollama_ef
        )
        _is_initialized = True
    except Exception as e:
        print(f"[FASTAPI ERROR] Could not initialize RAG system: {e}")

def get_justification(audit_result: dict) -> dict:
    init_rag_system()
    retrieved_docs = rag_engine.query_regulation(audit_result.get("rule_id", "GENERAL_FSSAI"))
    justification = rag_engine.generate_legal_justification(audit_result, retrieved_docs)
    
    return {
        "rule_id": audit_result.get("rule_id", ""),
        "justification": justification,
        "retrieved_docs": retrieved_docs
    }

def check_rag_health() -> str:
    try:
        import requests
        resp = requests.get("http://localhost:11434/", timeout=2)
        if resp.status_code == 200:
            return "connected"
        return "error"
    except:
        return "disconnected"
