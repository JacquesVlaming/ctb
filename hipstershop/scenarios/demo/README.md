# Scenario: **demo**


## Difficulty: **Easy**

* Instructor walks through the symptoms and root cause
* Root cause is obvious in the code snippet of the APM Error UI


## Description

This simple scenario introduces participants to the expectations of Capture the Bug.

recommendationService calls `simulate_issue()` when listing recommendations. The function has a 90% chance of calculating a large factorial, and then it divides by zero. This causes high CPU saturation, latency, and error rates on recommendationService, which also affects the frontend.


## Expected alerts

* Downtime - recommendationService
* CPU Saturation - recommendationService
* High Latency - recommendationService
* High Error Rate - recommendationService
* High Latency - frontend
* High Error Rate - frontend


## Expected path to identify the root cause

1. (APM) View errors for recommendationService
2. (APM) View code snippet of ZeroDivisionError
3. (APM) Observe the culprit of saturation, latency, and errors in `simulate_issue()`


## Proposed solution(s)

* Remove `simulate_issue()` from recommendationService
