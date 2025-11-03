FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq && \
    apt-get install -qqy wget g++ && \
    rm -rf /var/lib/apt/lists/*

# download grpc health probe
RUN GRPC_HEALTH_PROBE_VERSION=v0.2.0 && \
    wget -qO/bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64 && \
    chmod +x /bin/grpc_health_probe

WORKDIR /recommendationservice
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 3000
ENTRYPOINT ["python", "/recommendationservice/recommendation_server.py"]
