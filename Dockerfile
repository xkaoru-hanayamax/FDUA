FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# デフォルトコマンド: 接続テスト
CMD ["python", "-c", "from src.llm import test_connection; test_connection()"]
