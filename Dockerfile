FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc pkg-config libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY backend/ /code/

EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
