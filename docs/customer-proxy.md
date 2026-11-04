# Future: Customer-Authorized Preference Proxy

[Back to the README](../README.md)

## Change of role

The current laboratory simulates fictional customer responses for a product
team. A future personal proxy would represent a real person's preferences for
that person. The two functions must not share objectives, memory, or
permissions.

The recommended name is **customer-authorized preference proxy**, not
"faithful twin."

This proxy is not implemented in the repository.

## Objective hierarchy

```text
law and safety
  > the customer's latest explicit constraints and preferences
  > the customer's stated financial objective
  > a disclosed institutional objective, only when compatible
```

Policy code—not only a prompt—must enforce this hierarchy.

## Consent receipt

The customer must be able to see and accept:

- purpose;
- data categories;
- permitted inferences;
- permitted actions;
- recipients;
- retention;
- model limitations;
- expiration date.

The customer must also be able to inspect, correct, and reject inferences;
pause or revoke the proxy; and request deletion as required by applicable law.

## Conflict-of-interest tests

Required scenarios include:

- a higher-margin bank product versus a lower-cost alternative;
- an immediate reward versus the customer's liquidity objective;
- cross-sell that conflicts with a hard constraint;
- data consented for advice being reused for pricing.

The proxy must choose the customer-aligned option, disclose the conflict, or
abstain.

## Autonomy

For an initial release:

- provide recommendations and prepare options;
- do not submit applications, transfer funds, purchase, trade, or enter a
  contract;
- require fresh, specific confirmation for every consequential action;
- provide a clear pause and revocation control.

## Purpose firewall

Proxy data and inferences must not be used against a customer in underwriting,
pricing, or collections without a separate process, lawful purpose, validation,
and applicable consent.

## Future gates

| Control | Gate |
|---|---|
| Consent/purpose manifest | 100% |
| Out-of-scope access | 0 |
| Recall of hard constraints | 100% |
| Consequential action without confirmation | 0 |
| Conflict resolved for the customer or abstained | 100% |
| Positive "represents my preferences" evaluation | ≥ 90% |
