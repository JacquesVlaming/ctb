# Scenario: **cart-tls-required**


## Difficulty: **Easy**

* Requires knowing or quickly researching the meaning of [HTTP 426](https://tools.ietf.org/html/rfc2817)


## Description

The cart page is requiring TLS (HTTPS), but the frontend is serving only on HTTP. The frontend is sending HTTP 426 status codes instructing the browser to upgrade from HTTP to HTTPS, but the frontend will not serve HTTPS, either.

If this were a real situation, customers would not be able to purchase products, and the business would lose revenue.


## Expected alerts

* High Error Rate - frontend (`upgrade required`)


## Expected path to identify the root cause

1. (APM) View errors for frontend service
2. Research the meaning of [HTTP 426](https://tools.ietf.org/html/rfc2817)
3. Reproduce the behavior using a web browser, and confirm that the frontend does not serve HTTPS.


## Proposed solution(s)

* Serve frontend on HTTPS, or remove the TLS upgrade requirement
* Consider [HSTS](https://tools.ietf.org/html/rfc6797) instead of [HTTP 426](https://tools.ietf.org/html/rfc2817) for better security
