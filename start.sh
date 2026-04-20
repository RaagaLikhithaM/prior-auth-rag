#!/bin/bash
set -e
mkdir -p data/pdfs
if [ ! -f "data/pdfs/pembrolizumab_fda_label.pdf" ]; then
    python -c "import urllib.request; urllib.request.urlretrieve('https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/125514s103lbl.pdf', 'data/pdfs/pembrolizumab_fda_label.pdf'); print('PDF downloaded')"
fi
if [ ! -f "data/prior_auth_rag.db" ]; then
    python ingest.py
fi
uvicorn server.main:app --host 0.0.0.0 --port 8000 &
sleep 60
streamlit run frontend/app.py --server.port 7860 --server.address 0.0.0.0 --server.headless true
