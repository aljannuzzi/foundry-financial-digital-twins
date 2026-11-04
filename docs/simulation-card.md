# Simulation Card

[Back to the README](../README.md)

## Identification

- **System:** Foundry Financial Digital Twins
- **Segment:** Agro
- **Default population:** 120
- **Status:** non-production reference implementation
- **Behavioral calibration:** **not calibrated**
- **Decisioning approval:** none

## Purpose

Compare configurations of a synthetic financial proposition and generate
hypotheses for a real, governed pilot.

## Data

- events: 100% synthetic;
- period: 12 months;
- real customer data: none permitted;
- audit attributes: segregated sidecar;
- retention: removable demonstration environment plus local artifacts created
  by the operator.

## Models

- population generator: deterministic and versioned;
- baseline: deterministic utility decomposition;
- agent runtime: Microsoft Foundry Responses API;
- default deployment: `gpt-5.4-mini`, pinned version in the infrastructure
  parameters;
- automatic model upgrade: disabled;
- active simulation agent: `customer-twin`;
- auxiliary definitions: provisioned but not orchestrated.

Model and region availability must be checked at deployment time. A different
deployment is a material change requiring revalidation.

## Limitations

- anchors do not represent real prevalence;
- plausible language does not validate behavior;
- a model seed does not guarantee deterministic output;
- `fit_score` is not a probability;
- synthetic fairness tests do not establish real-world fairness or compliance;
- the current network and application-authentication posture is not suitable
  for banking production;
- no real financial decision is permitted.

## Approvals required before any real-data work

- accountable product owner;
- model risk management;
- privacy;
- compliance and fair lending;
- security;
- customer research;
- Agro domain expert;
- any additional legal or regulatory owner required by the institution.

Approval to conduct research is not approval for production decisioning.

## Revalidation

Revalidation is mandatory after any change to data, generator, profile, model,
prompt, agent, tool, evaluator, policy, infrastructure control, or intended use.

See [Methodology](methodology.md) and [Responsible AI](responsible-ai.md).
