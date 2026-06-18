FROM python:3.12-slim

WORKDIR /app

COPY apps/api/pyproject.toml /app/apps/api/pyproject.toml
COPY apps/api/src /app/apps/api/src
RUN pip install --no-cache-dir -e /app/apps/api

EXPOSE 8000

CMD ["uvicorn", "mpost_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
