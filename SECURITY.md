# Security Policy

## Scope

This project is a development scaffold for an ADAS trust-monitoring integration. Security reports are welcome for the repository's source, protocol validation, build configuration, and documentation. The project makes no claim that the scaffold is secure enough for a vehicle, production fleet, or safety-critical deployment.

## Reporting a vulnerability

Please do **not** disclose suspected vulnerabilities in a public issue. Use GitHub's private vulnerability reporting feature for this repository when it is enabled. If it is not enabled, contact the repository maintainers through a private contact listed in the repository's GitHub settings.

Include:

- a concise description and impact;
- affected file, version, commit, or configuration;
- reproducible steps or a minimal proof of concept;
- any suggested mitigation;
- whether the report includes sensitive data (do not attach credentials, private keys, customer data, or vehicle logs unless specifically requested through a secure channel).

Please allow maintainers reasonable time to investigate before public disclosure. Do not use this project or its demo as a target for unsafe real-vehicle testing.

## Supported versions

The latest version on the default branch is the only version expected to receive fixes. There is currently no long-term support or security-backport program.

## Security boundaries

The protocol documentation explicitly leaves authentication, encryption, replay protection, framing, retry, and clock synchronization to the integrator. Treat all transport input as untrusted, keep credentials out of the repository, and perform a qualified cybersecurity and functional-safety review before hardware deployment.
