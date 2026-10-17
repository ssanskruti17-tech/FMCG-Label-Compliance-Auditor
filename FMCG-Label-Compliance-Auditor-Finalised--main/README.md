# FMCG Label Auditor

An AI-assisted system for automated screening of FMCG nutritional labels for potential regulatory non-compliance.

## Problem

FMCG labels contain nutritional information, ingredients and front-of-pack claims that need to comply with food safety and advertising regulations. Manual auditing is time-consuming and difficult to scale.

## Solution

The prototype automatically:

1. Processes product label images
2. Extracts text using OCR
3. Identifies ingredients, nutritional information and claims
4. Checks extracted information against regulatory rules
5. Flags potential compliance issues with supporting evidence

## Workflow

Product Image
→ OpenCV
→ EasyOCR
→ Information Extraction
→ Compliance Engine
→ Audit Result

## Tech Stack

- Python
- OpenCV
- EasyOCR
- Streamlit
- Regex-based NLP / Information Extraction
- FSSAI Regulatory Rules

## Current Prototype

The current prototype demonstrates automated screening of product claims and ingredients, including identification of potential inconsistencies requiring regulatory review.

## Future Scope

- RAG-based retrieval of FSSAI regulations
- Semantic ingredient matching
- Expanded regulatory rule base
- Automated monitoring of e-commerce product listings
- Large-scale batch auditing

## Running the Application

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) installed and running locally

### Startup Instructions

1. **Pull the required embedding model (if not already done):**
   ```bash
   ollama pull all-minilm
   ```

2. **Build the Vector Database:**
   ```bash
   python build_mock_db.py
   ```
   *(This ingests the real FSSAI rules from `combined_fssai_labelling_and_lookup.json` into a local ChromaDB)*

3. **Start the FastAPI Backend:**
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```
   *(API docs available at `http://localhost:8000/docs`)*

4. **Start the Frontend (in a new terminal):**
   ```bash
   streamlit run app4.py
   ```


## 👥 Contributors

This project was collaboratively developed by our team of four.

- **Sanskruti Sonawane** — [GitHub](https://github.com/ssanskruti17-tech)
- **Kanishka Talwar** — [GitHub](https://github.com/kanishkatalwar)
- **Shrushti** — [GitHub](https://github.com/shrushtit06)
- **Ridhima Swarup** — [GitHub](https://github.com/ridhimaswarup)

