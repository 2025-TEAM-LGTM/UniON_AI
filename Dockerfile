FROM python:3.11-slim

WORKDIR /app

# 필요한 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "match_server:app", "--host", "0.0.0.0", "--port", "8000"]
