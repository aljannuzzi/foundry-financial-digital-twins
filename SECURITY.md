# Security Policy

## Supported versions

Security fixes are applied on a best-effort basis to the current `main` branch
and, after public releases exist, to the latest supported release identified in
release notes. Older commits and forks are not supported.

This repository is a non-production reference implementation, not a supported
banking product or approved financial-decision system.

## Report a vulnerability privately

Use GitHub private vulnerability reporting:

1. open this repository's **Security** tab;
2. select **Advisories** and **Report a vulnerability**;
3. provide a minimal description, impact, affected version/commit, reproduction,
   and suggested mitigation.

Do not disclose exploitable details in an issue, pull request, discussion,
public fork, or social channel. Do not include real customer/personal data,
credentials, tenant details, subscription identifiers, internal URLs, or
confidential information. Use synthetic proof-of-concept data and redact logs.

Maintainers will acknowledge and triage reports as capacity permits; no response
or remediation SLA is offered. Coordinated disclosure timing will be discussed
in the private advisory.

## Security boundaries

The project permits synthetic data only. The Azure reference deployment uses
managed identities, RBAC, disabled local/shared-key authentication, and
CIDR-restricted web ingress. IP restriction is not user authentication, and the
reference topology retains public Azure service endpoints. It requires
additional controls before any production consideration.

See the [threat model](docs/threat-model.md) for assets, trust boundaries,
controls, and accepted residual risks.
