# Scenario: **card-validation-error**


## Difficulty: **Medium**

* Requires basic understanding of software logic


## Description

A logical error in the card validation function of paymentService prevents payments from being processed.

If this were a real situation, customers would not be able to purchase products, and the business would lose revenue.


## Expected alerts

* High Error Rate - paymentService
* Downtime - paymentService


## Expected path to find the root cause

1. (Logs) View logs of paymentService and notice spike in errors:
    `Sorry, we cannot process mastercard credit cards. Only VISA or MasterCard is accepted.`
2. (APM) View transactions of paymentService and notice a spike in the error rate
3. (APM) View details of errors of paymentService
4. (APM) Exeption at highlighted line of code with logical error:
    * Actual logic: `if (!(cardType === 'visa' && cardType === 'mastercard'))`
    * Expected logic: `if (!(cardType === 'visa' || cardType === 'mastercard'))`


## Proposed solution(s)

* Change the conditional logic to use OR (`||`) instead of AND (`&&`)
