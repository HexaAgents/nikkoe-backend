FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "python -c 'from app.main import app; print(\"Import OK\")' && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
