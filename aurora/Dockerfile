FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uvicorn[standard] fastapi pydantic websockets

COPY app/ /app/app/

EXPOSE 8001

CMD ["sh", "-c", "uvicorn app.server:create_app --factory --host 0.0.0.0 --port ${PORT:-8001}"]
