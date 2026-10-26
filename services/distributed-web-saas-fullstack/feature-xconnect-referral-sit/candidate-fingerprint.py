#!/usr/bin/env python3
"""Print reproducible declaration identity, never imply runtime acceptance.

Run from any directory. No network access, cluster access, credentials or dependencies.
A full candidate cannot be frozen until data baseline and runtime evidence exist.
"""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
names = ("candidate.yaml", "helmrelease.yaml", "kustomization.yaml", "namespace.yaml",
         "network-policy.yaml", "oci-repository.yaml", "values.yaml")
files = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
print(json.dumps({"declaration_sha256": hashlib.sha256(canonical).hexdigest(),
                  "files": files, "candidate_fingerprint": None,
                  "status": "BLOCKED",
                  "reason": "Data baseline and runtime reconciliation are not verified"},
                 sort_keys=True, indent=2))
