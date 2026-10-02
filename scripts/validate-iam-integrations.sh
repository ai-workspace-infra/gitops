#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
manifest="${1:-${repo_root}/resources/svc.plus/uat/iam/identity-integrations.yaml}"
command -v ruby >/dev/null 2>&1 || { echo "ruby is required" >&2; exit 1; }
test -f "$manifest" || { echo "IAM manifest not found: $manifest" >&2; exit 1; }

MANIFEST="$manifest" ruby <<'RUBY'
require "yaml"
require "uri"

path = ENV.fetch("MANIFEST")
doc = YAML.safe_load(File.read(path), aliases: false)
fail "document must be a mapping" unless doc.is_a?(Hash)
fail "unexpected apiVersion" unless doc["apiVersion"] == "identity.svc.plus/v1alpha1"
fail "unexpected kind" unless doc["kind"] == "IdentityIntegrationSet"
metadata = doc.fetch("metadata")
spec = doc.fetch("spec")
fail "issuer must be https" unless spec.fetch("issuer").start_with?("https://")
integrations = spec.fetch("integrations")
expected = %w[gcp aws linode vultr ucloud-global grafana]
fail "providers must be exactly #{expected.join(', ')}" unless integrations.map { |item| item.fetch("provider") }.sort == expected.sort

integrations.each do |integration|
  integration.fetch("flows").each do |flow|
    protocol = flow.fetch("protocol")
    oidc_supported = flow.fetch("oidc_supported")
    if protocol == "saml" && oidc_supported
      fail "#{integration.fetch('name')}/#{flow.fetch('purpose')}: SAML requires oidc_supported=false"
    end
    if protocol == "saml" && flow.fetch("selection_reason", "").strip.empty?
      fail "#{integration.fetch('name')}/#{flow.fetch('purpose')}: SAML requires selection_reason"
    end
    if protocol == "oidc" && !oidc_supported
      fail "#{integration.fetch('name')}/#{flow.fetch('purpose')}: OIDC requires oidc_supported=true"
    end
    fail "#{integration.fetch('name')}/#{flow.fetch('purpose')}: invalid Vault ref" unless flow.fetch("vault_ref").match?(%r{\Akv/(iam|CICD)/})
    (flow["redirect_uris"] || []).each do |redirect|
      uri = URI.parse(redirect)
      fail "#{redirect}: redirect URI must not contain a wildcard" if redirect.include?("*")
      fail "#{redirect}: redirect URI must be absolute HTTPS" unless uri.is_a?(URI::HTTPS) && uri.host
    end
  end
end
puts "validate-iam-integrations: PASS (#{metadata.fetch('environment')}, #{integrations.length} providers)"
RUBY
