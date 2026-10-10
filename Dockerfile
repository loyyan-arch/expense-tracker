FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir -p /data \
    && chown app:app /data

COPY --chown=app:app . .

USER app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]