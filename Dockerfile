FROM python:3.9-alpine
LABEL maintainer sftan@icloud.com

WORKDIR /app

# Create and activate python virtual environment
RUN python -m venv venv
RUN source venv/bin/activate

# Install all the necessary python packages into 
# virtual environment 
COPY requirements.txt .
RUN apk add --no-cache --virtual .build-deps \
    python3-dev \
    build-base \
    librdkafka-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del --no-cache .build-deps

# Install additional run-time library
# - librdkafka is required by confluent-kafka python package    
RUN apk add librdkafka

COPY . .
CMD ["python", "-m", "audit_consumer"]

