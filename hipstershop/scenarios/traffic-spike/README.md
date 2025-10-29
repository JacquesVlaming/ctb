# Scenario: **traffic-spike**


## Difficulty: **Easy**

* Each service shows a clear correlation between request latency and request rate


## Description

A huge influx of customers floods the website, causing significant latency and downtime for nearly all services.

If this were a real situation, the excessive latency and downtime would encourage customers to leave the website and potentially use a competitor.


## Expected alerts

* High Latency - frontend
* High Latency - [*]Service
* CPU Saturation - recommendationService
* CPU Saturation - currencyService
* Downtime - advertService
* Downtime - frontend


## Expected path to identify the root cause

1. (APM) View transactions of affected services
2. (APM) See a spike in transactions per minute or requests per minute that correlates with a spike in latency.


## Proposed solution(s)

* Increase the number of replicas for each service, and possibly increase the number of nodes in the Kubernetes cluster
