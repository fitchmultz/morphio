# Security Policy

## Supported Versions

This repository follows rolling support on the `main` branch.

- Security fixes are applied to `main` first.
- Tagged releases receive best-effort backports when practical.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately.

1. Open a private GitHub Security Advisory (preferred), or
2. Email: `mitchfultz+security@users.noreply.github.com`

Please include:
- affected component/file
- reproduction steps or proof-of-concept
- impact assessment
- suggested remediation (if available)

## Response Targets

- Initial acknowledgement: within 3 business days
- Triage and severity assessment: within 7 business days
- Remediation plan or mitigation guidance: as soon as validated

## Secrets Handling Expectations

- Secrets must never be committed.
- Only root `/.env` and `/.env.example` are allowed.
- `/.env` is local-only; CI guardrails enforce this policy.
