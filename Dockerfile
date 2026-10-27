FROM python:3.12-slim

# Empêche la génération des fichiers .pyc et assure des logs Django en direct
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances système pour psycopg et healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Mise en cache et installation des dépendances Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copie de l'ensemble du projet
COPY . /app/

# Exposition du port HTTP
EXPOSE 8000

# Démarrage du serveur de développement sur toutes les interfaces réseau
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
