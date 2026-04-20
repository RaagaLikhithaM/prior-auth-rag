FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 7860

RUN mkdir -p data/pdfs

CMD python ingest.py && uvicorn server.main:app --host 0.0.0.0 --port 8000 & sleep 30 && streamlit run frontend/app.py --server.port 7860 --server.address 0.0.0.0 --server.headless true