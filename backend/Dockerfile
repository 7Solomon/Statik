# syntax=docker/dockerfile:1

FROM python:3.12-slim AS python-deps

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt


FROM python:3.12-slim AS runner

WORKDIR /app

COPY --from=python-deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY src/ ./src/
COPY wsgi.py gunicorn.conf.py ./

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]