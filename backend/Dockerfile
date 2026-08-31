# syntax=docker/dockerfile:1

FROM python:3.12-slim AS python-deps

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# The CPU-only torch pins and their extra index live in requirements.txt, so
# this one install covers them. Installing torch in a separate layer here as
# well would fight that: to pip, "torch==2.8.0" and "torch==2.8.0+cpu" are
# different versions, so it would download and install torch twice.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt


FROM python:3.12-slim AS runner

# Must also install libs in the runner stage!
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=python-deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY src/ ./src/
COPY wsgi.py gunicorn.conf.py ./

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]