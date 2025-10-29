# Scenario: **bind-localhost**


## Difficulty: **Hard**

* Requires basic understanding of networking
* Requires following the symptoms of some services to a root cause in another service


## Description

shippingService binds to the loopback interface (`127.0.0.1`) making it unreachable to other services, particularly in the placeOrderHandler trace. Upstream services such as frontend and checkoutService produce errors when customers submit orders. But shippingService never produces errors because it isn't doing anything, so the root cause isn't obvious.

If this were a real situation, customers could be paying for products without receiving them, because shipping is never processed for those orders.


## Expected alerts

* Downtime - shippingService
* High Error Rate - frontend (`connection refused` when communicating with shippingService)
* High Error Rate - checkoutService (`connection refused` when communicating with shippingService)


## Expected path to find the root cause

1. (Uptime) View downtime for shippingService
2. (APM) View errors for frontend and checkoutService
3. (Logs) View logs for shippingService, and see binding to localhost:
    (`Shipping Service listening on 127.0.0.1:7000`)


## Proposed solution(s)

* Reconfigure shippingService to listen to all interfaces (`0.0.0.0`) instead of the loopback interface (`127.0.0.1`)
