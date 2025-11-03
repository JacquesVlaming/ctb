FROM python:2.7-slim

# show python logs as they occur
ENV PYTHONUNBUFFERED=0
ENV DEBIAN_FRONTEND=noninteractive

# update apt and install packages, retry once in case of mirror issues
RUN apt-get update -qqy || apt-get update -qqy && \
    apt-get install -qqy wget g++ && \
    rm -rf /var/lib/apt/lists/*

# download the grpc health probe
RUN GRPC_HEALTH_PROBE_VERSION=v0.2.0 && \
    wget -qO/bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64 && \
    chmod +x /bin/grpc_health_probe

# set working directory
WORKDIR /recommendationservice

# install python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# copy app files
COPY . .

# expose port
EXPOSE 3000

# entrypoint
ENTRYPOINT ["python", "/recommendationservice/recommendation_server.py"]
