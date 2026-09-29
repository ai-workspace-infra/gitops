#!/usr/bin/env bash
set -euo pipefail

command -v ruby >/dev/null 2>&1 || {
  echo "Ruby is required to validate the open-platform-shared declarations" >&2
  exit 1
}

ruby -ryaml -e '
  declarations = {
    "vault" => {
      "path" => "resources/svc.plus/shared/gcp/open-platform-shared-vault.yaml",
      "namespace" => "open-platform-shared-vault",
      "host" => "vault-shared-0",
      "role" => "gateway",
      "machine_type" => "e2-highcpu-2",
      "domains" => ["vault.svc.plus"],
    },
    "observability" => {
      "path" => "resources/svc.plus/shared/gcp/open-platform-shared-observability.yaml",
      "namespace" => "open-platform-shared-observability",
      "host" => "observability-shared-0",
      "role" => "one",
      "machine_type" => "e2-medium",
      "domains" => ["observability.svc.plus"],
    },
    "iam" => {
      "path" => "resources/svc.plus/shared/gcp/open-platform-shared-iam.yaml",
      "namespace" => "open-platform-shared-iam",
      "host" => "iam-shared-0",
      "role" => "one",
      "machine_type" => "e2-medium",
      "domains" => ["iam.svc.plus"],
    },
  }

  declarations.each do |service, expected|
    path = expected.fetch("path")
    doc = YAML.safe_load(File.read(path), aliases: false)
    abort("#{service}: wrong API version") unless doc["apiVersion"] == "gitops.svc.plus/v1alpha1"
    abort("#{service}: wrong declaration kind") unless doc["kind"] == "GCPWorkloadNamespace"
    abort("#{service}: wrong metadata name") unless doc.dig("metadata", "name") == expected.fetch("namespace")
    abort("#{service}: shared environment required") unless doc.dig("metadata", "environment") == "shared"
    abort("#{service}: GCP provider required") unless doc.dig("metadata", "provider") == "gcp"

    spec = doc.fetch("spec")
    abort("#{service}: project/account must be open-platform-shared") unless
      spec["project_id"] == "open-platform-shared" && spec["gcp_account_id"] == "open-platform-shared"
    abort("#{service}: state namespace must be isolated") unless
      spec["workspace"] == expected.fetch("namespace") && spec["state_namespace"] == expected.fetch("namespace")
    expected_state = "terraform/shared/open-platform-shared/gcp-cloud/open-platform-shared/#{expected.fetch("namespace")}/terraform.tfstate"
    abort("#{service}: state key is incorrect") unless spec.dig("state", "key") == expected_state
    abort("#{service}: XConnect network must remain net_security_vault") unless spec.dig("xconnect", "network_id") == "net_security_vault"
    abort("#{service}: XConnect CIDR must remain 10.79.0.0/24") unless spec.dig("xconnect", "zero_trust_cidr") == "10.79.0.0/24"
    expected_mode = service == "vault" ? nil : "member"
    abort("#{service}: member-only XConnect mode is required") if expected_mode && spec["xconnect_mode"] != expected_mode
    abort("vault: the Gateway state must keep the default gateway mode") if service == "vault" && spec["xconnect_mode"]
    abort("#{service}: public SSH must be limited to the operator /32") unless spec["ssh_source_ranges"] == ["35.79.83.48/32"]
    abort("#{service}: target must remain persistent") unless spec.dig("resource", "lifecycle") == "persistent"

    nodes = spec.dig("resources", "vault_nodes") || []
    abort("#{service}: exactly one node is required") unless nodes.length == 1
    node = nodes.first
    abort("#{service}: unexpected node name") unless node["name"] == expected.fetch("host")
    abort("#{service}: unexpected XConnect role") unless node["xconnect_role"] == expected.fetch("role")
    abort("#{service}: unexpected machine type") unless node["machine_type"] == expected.fetch("machine_type")
    abort("#{service}: service domains are incomplete") unless node["service_domains"] == expected.fetch("domains")
  end

  vault = YAML.safe_load(File.read(declarations.fetch("vault").fetch("path")), aliases: false)
  migration = vault.fetch("spec").fetch("migration")
  abort("Vault migration source must remain open-platform-prod/vault-prod-0") unless
    migration["source_project_id"] == "open-platform-prod" && migration["source_instance"] == "vault-prod-0"
  abort("Vault migration source must be immutable") unless migration["source_mutation"] == "forbidden"
  oidc_path = "resources/svc.plus/shared/gcp/github-actions-oidc-open-platform-shared.yaml"
  oidc = YAML.safe_load(File.read(oidc_path), aliases: false)
  abort("OIDC declaration must target open-platform-shared") unless
    oidc.dig("spec", "project_id") == "open-platform-shared" && oidc.dig("spec", "gcp_account_id") == "open-platform-shared"
  abort("OIDC declaration must use the shared bootstrap state key") unless
    oidc.dig("spec", "state", "key") == "platform-ops-toolkit/shared/open-platform-shared/gcp-oidc-bootstrap/terraform.tfstate"
  abort("OIDC declaration must be restricted to the protected prod environment") unless
    oidc.dig("spec", "subjects") == [
      "repo:ai-workspace-infra/platform-ops-toolkit:environment:prod",
      "repo:ai-workspace-infra/platform-ops-toolkit:ref:refs/heads/main",
    ]
  puts "Validated three isolated open-platform-shared states for Vault, Observability, and IAM"
'
