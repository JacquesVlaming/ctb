# Scenario: **slow-query**


## Difficulty: **Medium**

* Requires digging through multiple layers of data: trace > span > query
* Requires understanding the performance implications of the comment in the query


## Description

An app developer accidentally pushed a performance test query to production, causing an increased latency of advertService and the frontend.

If this were a real situation, the latency of advertService would cause a decrease in advertisement impressions and its revenue stream. Additionally, the load placed on the Elasticsearch cluster could cause other indices to be unresponsive and affect services that use them.


## Expected alerts

* High Latency - advertService
* High Latency - frontend


## Expected path to identify the root cause

1. (APM) View transactions of advertService
2. (APM) View trace sample: /hipstershop.AdService/getAds
3. (APM) See developer comment on slow-running query in the span details


## Proposed solution(s)

* Remove the slow query.
