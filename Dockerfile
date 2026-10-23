FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATABASE_PATH=/app/data/cuenca.sqlite
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 1000 --create-home cuenca
# Permit the unprivileged Python process to bind the requested port 84.
RUN apt-get update && apt-get install -y --no-install-recommends libcap2-bin \
    && setcap 'cap_net_bind_service=+ep' "$(readlink -f /usr/local/bin/python3)" \
    && rm -rf /var/lib/apt/lists/*
COPY --chown=cuenca:cuenca app ./app
RUN mkdir -p /app/data && chown cuenca:cuenca /app/data
USER cuenca
EXPOSE 84
VOLUME ["/app/data"]
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:84/api/health',timeout=3)"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","84"]
