FROM python:3.12-slim

LABEL org.opencontainers.image.title="HomeboxLabel" \
      org.opencontainers.image.description="External Homebox label renderer with 4x6 location labels" \
      org.opencontainers.image.source="https://github.com/kevinatlee/HomeboxLabel" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8787

CMD ["python", "/app/app.py"]
