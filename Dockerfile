FROM python:3.11-slim

WORKDIR /app

# OpenCV と docling に必要なシステムライブラリをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# デフォルトコマンド: 接続テスト
CMD ["python", "-c", "from src.llm import test_connection; test_connection()"]
