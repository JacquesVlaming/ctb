# Scenario: **unicode-encode-error**


## Difficulty: **Hard**

* Requires a basic understanding of character encoding (e.g. UTF-8 and ASCII), which may be difficult for a novice to research quickly
* Requires inspecting multiple layers of stack traces and local variables


## Description

An influx of orders is placed from customers in Vietnam. emailService is failing to properly encode the characters of the Vietnamese shipping addresses causing many confirmation emails to fail.

If this were a real situation, customers from Vietnam (or anywhere with non-ASCII characters in the names of the shipping addresses) would not receive emailed receipts upon placing orders. This could lead to a degraded experience for those customer segments.


## Expected alerts

* High Error Rate - emailService
* High Error Rate - checkoutService


## Expected path to identify the root cause

1. (APM) View errors of emailService
2. (APM) View local variables of errors
3. (APM) See that `encode()` function reduces the character set to ASCII and back to UTF-8, causing a loss of fidelity to the Vietnamese strings.


## Proposed solution(s)

* Remove the function that converts the strings to ASCII; Python 3 already treats strings as Unicode
