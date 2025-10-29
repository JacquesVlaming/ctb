# Scenario: **null-pointer-exception**


## Difficulty: **Hard**

* Requires multiple UIs to diagnose
* Requires analyzing multiple symptoms to infer the root cause
* Requires understanding the concept of NullPointerException in Java


## Description

advertService has become unreliable. Sometimes it works as intended, and sometimes it throws a NullPointerException.

If this were a real situation, the business would lose some revenue due to the inconsistent availability of its advertisements.


## Expected alerts

* Downtime - advertService
* High Error Rate - advertService
* High Error Rate - frontend


## Expected path to identify the root cause

1. (APM) View errors for advertService
2. (APM) View culprit of NullPointerException (`hipstershop.AdService.getAdsByCategory(AdService.java:217)`)
3. (Logs) Filter logs by "advertservice" and "null" (quirk: "null" must have quotes)
4. (Logs) Broaden filter by just "advertservice"
5. (Logs) Observe that "received ad request (context_words=null)" appears periodically
6. (Logs or APM) Copy `trace.id` from log details or APM Error metadata
7. (APM) Filter traces by `trace.id`
8. (APM) Observe that messages with "context_words=null" occur only during homeHandler. Messages where "context_words" is NOT null occur during productHandler.

What these symptoms corroborate:

advertService fetches ads by category. The category is based on the product being viewed. If there is no product being viewed (i.e. the home page), then the category is null. When the category is null, advertService throws a NullPointerException.


## Proposed solution(s)

* Modify `hipstershop.AdService.getAdsByCategory` to handle cases where `context_words` is `null`
