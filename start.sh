#!/bin/bash
mkdir -p data/pdfs

if [ ! -f "data/prior_auth_rag.db" ]; then
    echo "Downloading knowledge base PDFs..."
    python -c "
import urllib.request
try:
    urllib.request.urlretrieve('https://static.cigna.com/assets/chcp/pdf/coveragePolicies/pharmacy/ph_1403_coveragepositioncriteria_oncology.pdf', 'data/pdfs/cigna_oncology_policy.pdf')
    print('Cigna PDF downloaded')
except Exception as e:
    print(f'Cigna download failed: {e}')
"
    echo "Running ingest..."
    python ingest.py
fi

uvicorn server.main:app --host 0.0.0.0 --port 8000 &
sleep 5
streamlit run frontend/app.py --server.port 7860 --server.address 0.0.0.0 --server.headless true