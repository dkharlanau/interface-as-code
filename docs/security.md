# Security and safe data handling

The specification stores expectations and references, never credentials, tokens, private keys, certificates or production payloads. `secret_ref` / `certificate_ref` may identify an external secret/certificate system but must never embed secret material.

Examples should use synthetic data. Security readiness checks cover exposed interfaces without authentication, transport encryption for personal data, and missing classification on critical interfaces.
