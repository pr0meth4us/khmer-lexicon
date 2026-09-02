FROM python:3.11-slim

# The /admin page reads Cloud Logging through the gcloud CLI. Slim image, so
# install it; the service account carries roles/logging.viewer.
RUN apt-get update && apt-get install -y --no-install-recommends curl python3-crcmod \
 && curl -sSL https://sdk.cloud.google.com | bash -s -- --disable-prompts --install-dir=/opt \
 && rm -rf /var/lib/apt/lists/*
ENV PATH="/opt/google-cloud-sdk/bin:${PATH}"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Mirror the repository layout exactly. app.py resolves dist/ as BASE.parent, so
# flattening web/ into /app would make that resolve to / and the lexicon would
# never be found. Keep web/ a subdirectory and run from inside it.
COPY khmerlex/ /app/khmerlex/
COPY dist/ /app/dist/
COPY web/ /app/web/

# khmerlex is imported as a top-level package from web/app.py.
ENV PYTHONPATH=/app

# khmer-nltk ships a CRF model that loads on first use. Warm it at build time so
# the first request is not a two-second stall in front of an audience.
RUN python -c "from khmernltk import word_tokenize; word_tokenize('សួស្តី')"

WORKDIR /app/web
ENV PORT=8000
EXPOSE 8000
# One worker: the automaton and the CRF model are ~200 MB resident and each
# worker builds its own. Threads carry the concurrency a demo needs.
# No --preload: the lexicon is fetched at import time and preloading would run
# that fetch before the health check is listening.
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120 app:app
