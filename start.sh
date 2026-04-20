#!/bin/bash
mkdir -p data/pdfs
uvicorn server.main:app --host 0.0.0.0 --port 8000 &
sleep 5
streamlit run frontend/app.py --server.port 7860 --server.address 0.0.0.0 --server.headless true