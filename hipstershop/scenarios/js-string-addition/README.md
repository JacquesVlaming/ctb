# Scenario: **js-string-addition**


## Difficulty: **Medium**

* Requires understanding how JavaScript treats addition of mixed data types
* Alerts take the user to the root cause quickly


## Description

paymentService is rejecting all payments due to expired credit cards, even though the credit cards have not expired. The JavaScript code that validates the expiration date has a mistake where the current month (an integer such as `9`) is added with `'1'` (a string). JavaScript would evaluate this expression as `91` instead of `10`, which creates problems for other mathematical operations in the validation code.

If this were a real situation, customers would be unable to purchase products and the business would lose revenue.


## Expected alerts

* Downtime - Payment Service
* High Error Rate - Payment Service
* High Error Rate - Checkout Service


## Expected path to identify the root cause

1. (APM) View errors for paymentService (`Your credit card (ending ****) expired on **/****`)
2. (APM) View code snippet:

```javascript
const currentMonth = new Date().getMonth() + '1';
if ((currentYear * '12' + currentMonth) > (cardYear * '12' + cardMonth)) { throw new ExpiredCreditCard(cardNumber.replace('-', ''), cardMonth, cardYear); }
```

3. (APM) The highlighted line shows where the error was thrown. The line before it has the mistake in this case.

The expression `new Date().getMonth() + '1'` should be `new Date().getMonth() + 1`. The quotes around `'1'` treats the value as a string instead of an integer. JavaScript adds strings to integers by concatenating them instead of mathematically adding them. For example, if `new Date().getMonth()` is `9` (September), then `new Date().getMonth() + '1'` is `91` (an invalid month). The corrected expression `new Date().getMonth() + 1` is `10` (October).


## Proposed solution(s)

* Remove the quotes around the integers in the code snippet
