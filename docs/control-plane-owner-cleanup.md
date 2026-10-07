# Control-plane owner cleanup declarations

The existing-host declaration stores groups and service domains; runtime host/user selectors are consumed by the IaC renderer and are not stored in GitOps. IaC must label those facts explicit-target rather than invent a Provider instance.

The UAT serverless cleanup policy is intentionally disabled. It declares only three UAT Cloud Run services. Enable it only after reviewing the pinned owner/caller plan and real deletion/convergence receipt. It does not authorize PROD, persistent data deletion or blanket image pruning.

XConnect Gateway/One hosts remain dynamic same-run IaC facts, not fixed values in these declarations.
