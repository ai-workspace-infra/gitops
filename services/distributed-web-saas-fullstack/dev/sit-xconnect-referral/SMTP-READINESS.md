# SIT SMTP configuration readiness

SIT uses smtp.gmail.com:587 with STARTTLS and certificate verification. The account template requires SMTP_USERNAME and SMTP_PASSWORD from the existing accounts runtime Secret, sourced through an authorized consumer of kv/dev/platform/smtp/google. Sender identity follows the authenticated username rather than an unverified feature-domain address.

The standard Kubernetes NetworkPolicy permits Accounts public IPv4 TCP587 because it cannot select a DNS hostname. Private and link-local destinations are excluded; hostname and TLS certificate validation remain application responsibilities. This does not constitute a hostname-level egress allowlist.

Do not mark SMTP ready before the secret injector and trusted deploy workflow are implemented and a real delivery receipt exists. This change configures SIT only; UAT promotion remains a separate stage.
