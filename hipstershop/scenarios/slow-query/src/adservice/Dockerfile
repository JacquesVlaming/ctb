FROM openjdk:8-slim as builder

WORKDIR /app

ARG ELASTICSEARCH_VERSION
ENV ELASTICSEARCH_VERSION ${ELASTICSEARCH_VERSION}

RUN mkdir /app/libs

# used for non-public dependencies. Might need this in the future
# ADD https://storage.cloud.google.com/eden-files/observe/advertService/apm-agent-attach-1.15.1-SNAPSHOT.jar /app/libs/

COPY ["build.gradle", "gradlew", "./"]
COPY gradle gradle
RUN chmod +x gradlew
RUN ./gradlew downloadRepos

COPY . .
RUN chmod +x gradlew
RUN ./gradlew installDist

FROM openjdk:8-slim

# Download Stackdriver Profiler Java agent
RUN apt-get -y update && apt-get install -qqy \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN GRPC_HEALTH_PROBE_VERSION=v0.2.1 && \
    wget -qO/bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64 && \
    chmod +x /bin/grpc_health_probe

WORKDIR /app
COPY --from=builder /app .

EXPOSE 10000
ENTRYPOINT ["/app/build/install/hipstershop/bin/AdService"]
