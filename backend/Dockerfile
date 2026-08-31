# syntax=docker/dockerfile:1

FROM python:3.12-slim AS python-deps

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Torch first, from the CPU-only index. Default PyPI wheels pull ~2.5 GB of
# nvidia-* CUDA packages this image can never use: compose reserves no GPU and
# every call site passes device='cpu'. Its own layer so the slowest download is
# repeated only when these pins change, not on every requirements.txt edit.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch==2.8.0 torchvision==0.23.0 \
        --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt


FROM python:3.12-slim AS runner

WORKDIR /app

COPY --from=python-deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY src/ ./src/
COPY wsgi.py gunicorn.conf.py ./

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]