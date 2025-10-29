# Scenario: **redirect-loop**


## Difficulty: **Hard**

* The only alert gives no technical details
* There are no errors, downtime, or saturation
* Helps to understand the concept of a [URL Fragment](https://tools.ietf.org/html/rfc3986#section-3.5)


## Description

Customers who view products become trapped in a redirect loop, and never can view or purchase products. When a user visits a product page, the frontend product handler redirects the user to the same page but with the `session_id` embedded in the URL. The intent was to track the purchasing journey of the user, but the implementation was erroneous. The `session_id` parameter was placed after a hash symbol (`#`) in the URL, which web browsers ignore when request pages or following redirects.

If this were a real situation, customers would be unable to view products, add them to the cart, and purchase them, resulting in a loss of revenue for the business.


## Expected alerts

* No Purchases


## Expected path to identify the root cause

1. (APM) Observe spike in requests per minute for frontend, and a dip for all others
2. (Logs) Observe multiple repeated 302 redirects per second
3. (Logs) Observe that the redirect is never correctly resolved (see example below)
4. Reproduce the behavior on the Hipster Shop website

Example from frontend.log:

```
[][access]   "GET /product/1YMWWN1N4O HTTP/" 302
request started
redirecting to session-tracked url: /product/1YMWWN1N4O?#session_id=da296491-bc3a-48bc-baf2-5a775f51b1a0
[][access]   "GET /product/1YMWWN1N4O? HTTP/" 302
```

Notice that frontend redirects the user to the same page with a `session_id` appended to the URL. After the user is redirected, the log shows that the URL omitted everything from the hash symbol (`#`) onward. This part of the URL is called the [fragment](https://tools.ietf.org/html/rfc3986#section-3.5). Web browsers exclude fragments from URLs before submitting requests. In this case, customers are being redirected to same product page every time they view a product.


## Proposed solution(s)

* Remove the hash symbol (`#`) from the redirected URLs.
