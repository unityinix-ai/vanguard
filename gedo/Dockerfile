FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uvicorn[standard] fastapi pydantic

COPY app/ /app/app/

EXPOSE 8000

CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
