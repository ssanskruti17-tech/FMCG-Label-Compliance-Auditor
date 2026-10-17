FMCG Label Auditor:
An AI-assisted system for automated screening of FMCG nutritional labels for potential regulatory non-compliance.

Problem
FMCG labels contain nutritional information, ingredients and front-of-pack claims that need to comply with food safety and advertising regulations. Manual auditing is time-consuming and difficult to scale.

Solution
The prototype automatically:

Processes product label images
Extracts text using OCR
Identifies ingredients, nutritional information and claims
Checks extracted information against the regulatory rules
Flags potential compliance issues with supporting evidence
Workflow
Product Image → OpenCV → EasyOCR → Information Extraction → Compliance Engine → Audit Result

Tech Stack
Python
OpenCV
EasyOCR
Streamlit
Regex-based NLP / Information Extraction
FSSAI Regulatory Rules
Current Prototype
The current prototype demonstrates automated screening of product claims and ingredients, including identification of potential inconsistencies requiring regulatory review.

Future Scope:
RAG-based retrieval of FSSAI regulations
Semantic ingredient matching
Expanded regulatory rule base
Automated monitoring of e-commerce product listings
Large-scale batch auditing
Running the Application
Prerequisites
Python 3.10+
Ollama installed and running locally
Startup Instructions
Pull the required embedding model (if not already done):

ollama pull all-minilm
Build the Vector Database:

python build_mock_db.py
(This ingests the real FSSAI rules from combined_fssai_labelling_and_lookup.json into a local ChromaDB)

Start the FastAPI Backend:

uvicorn api.main:app --reload --port 8000
(API docs available at http://localhost:8000/docs)

Start the Frontend (in a new terminal):

streamlit run app4.py
