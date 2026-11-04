# Public-Release Checklist

[Back to the README](../README.md)

Keep the repository private until every applicable item has evidence and the
accountable owner approves release. This checklist is not legal, security, or
regulatory approval.

## 1. Ownership and scope

- [ ] Name an accountable repository owner and active maintainers in GitHub.
- [ ] Confirm the intended use remains synthetic scenario testing, not
      forecasting or financial decisioning.
- [ ] Confirm the release contains no claim of Microsoft or third-party
      endorsement.
- [ ] Review the roadmap so planned work is not represented as implemented.
- [ ] Record model-risk, privacy, security, legal, compliance, and open-source
      owner approvals in the organization's approved system of record.

## 2. Secrets, identifiers, and history

- [ ] Run an approved secret scanner over the working tree **and full Git
      history**, including deleted files and large-file storage if used.
- [ ] Review scanner findings; rotate and invalidate any credential that ever
      entered history before rewriting history.
- [ ] Scan tracked documentation, examples, fixtures, logs, screenshots, and
      metadata for personal names, email addresses, tenant/domain details,
      subscription/resource IDs, internal URLs, IP addresses, tokens, and
      connection strings.
- [ ] Verify `.env.example` contains names/placeholders only and that local
      `.env`, Azure environment files, output artifacts, caches, and IDE files
      are ignored and untracked.
- [ ] Review commit authorship and messages under the organization's privacy and
      contribution policy.

## 3. License and dependencies

- [ ] Obtain open-source owner/legal approval for the MIT license and all
      notices.
- [ ] Generate and review an SBOM or equivalent dependency inventory for Python,
      JavaScript, base images, GitHub Actions, and Azure SDKs.
- [ ] Review direct and transitive licenses, notices, export restrictions, and
      trademark usage.
- [ ] Verify model, Foundry, Azure service, and sample-data terms permit the
      documented public use.
- [ ] Remove or replace any artifact without clear redistribution rights.

## 4. Public documentation and Azure instructions

- [ ] Test the README quickstart from a clean clone with only public package
      registries and public documentation.
- [ ] Test `azd up` and `azd down --purge` in a clean, non-sensitive Azure
      environment using only generic values.
- [ ] Confirm all Azure commands use placeholders or values read from the local
      `azd` environment—never real tenant, subscription, resource, endpoint, or
      IP values.
- [ ] Verify the documented model/version/SKU is publicly available in at least
      one documented region, or clearly require deployers to choose an available
      alternative.
- [ ] Document required permissions, providers, quota, public endpoints,
      regional/data-zone implications, batch size, timeout, and cleanup.
- [ ] Validate every relative Markdown link and spot-check public external links.

## 5. Screenshots and accessibility

- [ ] Capture screenshots using synthetic data only and remove image metadata.
- [ ] Verify screenshots contain no browser profile, account, tenant, resource,
      notification, bookmark, URL, or desktop information.
- [ ] Add useful alternative text and avoid conveying essential information only
      through an image.
- [ ] Complete keyboard, focus-order, semantic-heading, form-label, zoom,
      reduced-motion, screen-reader, and color-contrast checks.
- [ ] Verify decision states are not distinguished by color alone.
- [ ] Record known accessibility limitations and remediation owners.

## 6. Security and threat model

- [ ] Review [SECURITY.md](../SECURITY.md) and enable GitHub private
      vulnerability reporting.
- [ ] Review and approve the [threat model](threat-model.md), including public
      endpoints, IP-only web restriction, global model processing, identity
      scopes, telemetry, supply chain, and output misuse.
- [ ] Verify managed identities, least-privilege RBAC, disabled local/shared-key
      auth, TLS, blob privacy, and ingress restrictions in a fresh deployment.
- [ ] Verify no raw profile or audit-sidecar content appears in telemetry.
- [ ] Define triage, incident response, credential rotation, and repository
      takedown owners before publication.

## 7. CI, CodeQL, and supply chain

- [ ] Run Python tests, Ruff, population validation, UI build/lint, and both
      Bicep builds successfully from the release commit.
- [ ] Confirm CI and CodeQL workflows have least-privilege permissions and pass
      for Python and JavaScript/TypeScript.
- [ ] Enable dependency alerts and review Dependabot configuration.
- [ ] Pin or approve third-party Actions according to organizational policy.
- [ ] Review base-image provenance, container vulnerabilities, lockfiles, and
      package integrity.

## 8. Responsible AI and model risk

- [ ] Verify the “synthetic scenario—not a forecast” warning is prominent in the
      README, UI, API metadata, and exported results.
- [ ] Verify `fit_score` is never described as probability and outputs are
      labeled `not calibrated`.
- [ ] Review prohibited uses, fairness/proxy limitations, human review,
      effective challenge, and revalidation triggers.
- [ ] Verify the five-agent documentation distinguishes provisioned definitions
      from the one agent currently invoked.
- [ ] Confirm the customer-authorized preference proxy is clearly future work.

## 9. Cost, support, and community readiness

- [ ] Verify the cost disclaimer covers model use, jobs, registry, data,
      telemetry, retention, quota, and scale-to-zero limitations.
- [ ] Test cleanup and independently confirm resources and retained data are
      removed.
- [ ] Review the code of conduct, contribution guide, support policy, issue/PR
      templates, changelog, citation metadata, and security policy.
- [ ] Set realistic maintainer response expectations and avoid any support SLA
      not backed by an owner.

## 10. Final manual publication

- [ ] Freeze the approved commit and record final owner sign-off.
- [ ] Re-run the secret/history scan and verify the exact publication diff.
- [ ] Configure branch protection, required checks, issue settings, private
      vulnerability reporting, and repository security features.
- [ ] **As the final manual action, an authorized repository owner changes
      GitHub visibility from private to public in repository settings. Do not
      automate this step.**
- [ ] Immediately verify the anonymous public view, clone, license, links,
      release assets, security channel, and absence of sensitive content.
