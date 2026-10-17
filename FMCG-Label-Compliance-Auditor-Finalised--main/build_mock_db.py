import json
import chromadb
from chromadb.utils import embedding_functions

print("Initializing local ChromaDB in ./chroma_db...")
client = chromadb.PersistentClient(path="./chroma_db")

print("Connecting to Ollama for Embeddings (all-minilm)...")
ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    url="http://localhost:11434/api/embeddings",
    model_name="all-minilm"
)

# Clear out any existing collection from previous tests
try:
    client.delete_collection("fssai_rules")
except Exception:
    pass

collection = client.create_collection(
    name="fssai_rules",
    embedding_function=ollama_ef
)

print("Loading data from combined_fssai_labelling_and_lookup.json...")
try:
    with open('combined_fssai_labelling_and_lookup.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print("Error: combined_fssai_labelling_and_lookup.json not found!")
    exit(1)

texts = []
metadatas = []
ids = []

# 1. Load labelling records
labelling_records = data.get('records_from_labelling_display_json', [])
print(f"Processing {len(labelling_records)} labelling records...")

for record in labelling_records:
    # Skip if content is empty
    if not record.get('content') or str(record.get('content')).strip() == "":
        print(f"Skipping empty record {record.get('id')}")
        continue
        
    record_id = f"label_{record.get('id')}"
    text = f"{record.get('title')}\n\n{record.get('content')}"
    metadata = {
        "clause": record.get('section', 'Unknown Section'),
        "source": "FSSAI Labelling and Display Regulations 2020",
        "record_type": "regulation"
    }
    
    texts.append(text)
    metadatas.append(metadata)
    ids.append(record_id)

# 2. Load structured records (nutrition thresholds)
structured_records = data.get('records_from_structured_db', {}).get('nutrition_thresholds', [])
if isinstance(data.get('records_from_structured_db'), list):
    # In case it's a list, we saw in inspection it might be a list of dicts or something else.
    # From earlier inspection, structured db was a dict containing 'nutrition_thresholds' or just a list of items.
    pass

if not structured_records and isinstance(data.get('records_from_structured_db'), list):
    # Try parsing string if it was somehow nested differently
    pass

# We checked earlier: `records_from_structured_db` is a dict containing `nutrition_thresholds` list?
# Let's inspect the actual structure again if needed, but it seems to be list or dict.
# Earlier inspect said: `[{'id': 1, 'regulation_short_code': ...}]` meaning `records_from_structured_db` IS a list!
if isinstance(data.get('records_from_structured_db'), list):
    structured_records = data.get('records_from_structured_db')

print(f"Processing {len(structured_records)} structured records...")

for record in structured_records:
    if not isinstance(record, dict):
        continue
    record_id = f"struct_{record.get('id')}"
    text = f"Claim: {record.get('claim_type')} {record.get('nutrient')}. Condition: {record.get('condition_raw')}"
    metadata = {
        "clause": record.get('regulation_short_code', 'FSS-ADV-CLAIMS'),
        "source": "FSSAI Structured DB",
        "record_type": "threshold"
    }
    
    texts.append(text)
    metadatas.append(metadata)
    ids.append(record_id)

print(f"Total documents to insert: {len(texts)}")

if texts:
    print("Generating mathematical vectors via local Ollama...")
    collection.add(
        documents=texts,
        metadatas=metadatas,
        ids=ids
    )
    print("\n✅ Real database created successfully via Ollama! You can now run the app.")
else:
    print("\n⚠️ No documents were processed!")