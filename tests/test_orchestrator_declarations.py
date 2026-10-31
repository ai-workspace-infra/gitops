"""Parity check for declarations migrated from Platform-Orchestrator (Task 5)."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_MODES = {"aws-oidc", "gcp-wif-vault", "azure-federated-identity", "vault-vultr-token",
                 "vault-linode-token", "vault-ucloud-api-key", "vault-existing-host-facts"}


def load(p):
    return yaml.safe_load((ROOT / p).read_text())


def test_environment_defaults_reference_registered_providers():
    envs = load("iac/environment-defaults.yaml")["spec"]["environments"]
    providers = load("iac/provider-registry.yaml")["spec"]["providers"]
    assert set(envs) == {"sit", "uat", "prod", "prod-v*"}
    for name, env in envs.items():
        assert env["cloud_provider"] in providers, name
        assert env["account"], name


def test_provider_registry_shape():
    providers = load("iac/provider-registry.yaml")["spec"]["providers"]
    for pid, p in providers.items():
        assert set(p) == {"provisioner", "gitops_provider", "terraform_tree", "credential_mode"}, pid
        assert p["credential_mode"] in ALLOWED_MODES
        assert (p["terraform_tree"] is None) == (p["provisioner"] == "existing")


def test_no_secret_like_values():
    for f in ("iac/environment-defaults.yaml", "iac/provider-registry.yaml"):
        text = (ROOT / f).read_text().lower()
        for bad in ("password", "private_key", "token:", "secret:"):
            assert bad not in text, (f, bad)


def test_cleanup_role_policy_pair():
    n = "github-actions-platform-ops-toolkit-uat-compute-cleanup"
    role = load(f"security/vault/roles/{n}.yaml")
    pol = load(f"security/vault/policies/{n}.yaml")
    assert role["spec"]["token_policies"] == [n]
    assert pol["metadata"]["name"] == n
    assert all(p["capabilities"] == ["read"] for p in pol["spec"]["paths"])
