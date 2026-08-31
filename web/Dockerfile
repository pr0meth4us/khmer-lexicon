FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the internal khmerlex package
COPY khmerlex/ /app/khmerlex/
# Copy the dataset
COPY dist/ /app/dist/
# Copy the web application
COPY web/ /app/

# khmer-nltk ships a CRF model that loads on first use. Warm it at build time so
# the first request is not a 2-second stall in front of an audience.
RUN python -c "from khmernltk import word_tokenize; word_tokenize('សួស្តី')"

ENV PORT=8000
EXPOSE 8000
# One worker: the automaton and the CRF model are ~200 MB resident and every
# worker builds its own. Threads handle the concurrency a demo needs.
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 60 \
    --preload app:app
