# --- Build Stage ---
FROM openjdk:8-slim as builder

WORKDIR /app

# Pass Elasticsearch version as build arg
ARG ELASTICSEARCH_VERSION=7.17.0
#ENV ELASTICSEARCH_VERSION=${ELASTICSEARCH_VERSION}

RUN mkdir /app/libs

# Copy Gradle wrapper and build files
COPY ["build.gradle", "gradlew", "./"]
COPY gradle gradle
RUN chmod +x gradlew

# Download dependencies with Gradle
RUN ./gradlew downloadRepos -PelasticsearchVersion=${ELASTICSEARCH_VERSION} --stacktrace --no-daemon

# Copy the full source
COPY . .

# Build the project
RUN chmod +x gradlew
RUN ./gradlew installDist -PelasticsearchVersion=${ELASTICSEARCH_VERSION} --stacktrace --no-daemon

# --- Runtime Stage ---
FROM openjdk:8-slim

# Install wget for gRPC health probe
RUN apt-get -y update && apt-get install -qqy wget && rm -rf /var/lib/apt/lists/*

# Download gRPC health probe
RUN GRPC_HEALTH_PROBE_VERSION=v0.2.1 && \
    wget -qO/bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64 && \
    chmod +x /bin/grpc_health_probe

WORKDIR /app
COPY --from=builder /app .

EXPOSE 10000
ENTRYPOINT ["/app/build/install/hipstershop/bin/AdService"]
