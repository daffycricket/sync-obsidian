FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY app/ ./app/
COPY logging.yaml ./

# Créer le dossier data
RUN mkdir -p /app/data

# Exposer le port
EXPOSE 8000

# Variables d'environnement par défaut
ENV DATABASE_URL="sqlite+aiosqlite:///./data/syncobsidian.db"
ENV STORAGE_PATH="./data/storage"
ENV HOST="0.0.0.0"
ENV PORT="8000"

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Lancer l'application avec logs timestamps
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "logging.yaml"]
