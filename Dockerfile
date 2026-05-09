FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

RUN mkdir -p /app/data

ENTRYPOINT ["sh", "-c", "alembic upgrade head && python -m app.main"]
