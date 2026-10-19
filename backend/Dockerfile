# Basiléia Encontros — API (FastAPI + LangGraph). Contexto de build: a pasta backend/
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY encontros ./encontros

# fotos e (no modo demonstração) o SQLite ficam aqui: monte um volume
VOLUME /app/dados
EXPOSE 8000
CMD ["python", "-m", "encontros"]
