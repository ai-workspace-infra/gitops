#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
manifest="${1:-${repo_root}/resources/svc.plus/uat/iam/identity-integrations.yaml}"
command -v ruby >/dev/null 2>&1 || { echo "ruby is required" >&2; exit 1; }
test -f "$manifest" || { echo "IAM manifest not found: $manifest" >&2; exit 1; }

MANIFEST="$manifest" ruby <<'RUBY'
require "yaml"
require "uri"

def keys!(object, required, optional = [])
  fail "expected mapping" unless object.is_a?(Hash)
  fail "missing keys: #{required - object.keys}" unless (required - object.keys).empty?
  fail "unknown or secret keys: #{object.keys - required - optional}" unless (object.keys - required - optional).empty?
end

def https!(value)
  fail "URL must be a string" unless value.is_a?(String)
  uri = URI.parse(value)
  fail "URL must be absolute HTTPS without credentials, fragments or wildcards" unless uri.is_a?(URI::HTTPS) && uri.host && !uri.host.empty? && !uri.userinfo && !uri.fragment && !value.include?("*")
end

path = ENV.fetch("MANIFEST")
doc = YAML.safe_load(File.read(path), aliases: false)
keys!(doc, %w[apiVersion kind metadata spec])
fail "unexpected apiVersion" unless doc["apiVersion"] == "identity.svc.plus/v1alpha1"
fail "unexpected kind" unless doc["kind"] == "IdentityIntegrationSet"
metadata = doc.fetch("metadata")
spec = doc.fetch("spec")
keys!(metadata, %w[name project environment])
fail "invalid environment" unless %w[sit uat prod].include?(metadata["environment"])
fail "invalid metadata name" unless metadata["name"].is_a?(String) && metadata["name"].match?(/\A[a-z0-9-]+\z/)
fail "invalid project" unless metadata["project"].is_a?(String) && !metadata["project"].strip.empty?
keys!(spec, %w[issuer integrations])
https!(spec.fetch("issuer"))
integrations = spec.fetch("integrations")
fail "integrations must be an array" unless integrations.is_a?(Array)
expected = %w[gcp aws linode vultr ucloud-global grafana]
fail "providers must be exactly #{expected.join(', ')}" unless integrations.map { |item| item.fetch("provider") }.sort == expected.sort

integrations.each do |integration|
  keys!(integration, %w[name provider flows])
  fail "invalid integration name" unless integration["name"].is_a?(String) && integration["name"].match?(/\A[a-z0-9-]+\z/)
  flows = integration.fetch("flows")
  fail "flows must be a nonempty array" unless flows.is_a?(Array) && !flows.empty?
  purposes = flows.map { |f| f.fetch("purpose") }
  expected_purposes = integration["provider"] == "grafana" ? %w[application] : %w[workforce workload]
  fail "missing, duplicate or inappropriate purpose" unless purposes.sort == expected_purposes.sort
  integration.fetch("flows").each do |flow|
    keys!(flow, %w[purpose protocol oidc_supported capability_evidence_url vault_ref], %w[selection_reason redirect_uris role_claim])
    protocol = flow.fetch("protocol")
    oidc_supported = flow.fetch("oidc_supported")
    fail "invalid protocol" unless %w[oidc saml vault-api-token].include?(protocol)
    fail "oidc_supported must be boolean" unless [true, false].include?(oidc_supported)
    https!(flow["capability_evidence_url"])
    fail "invalid role claim" if flow.key?("role_claim") && (!flow["role_claim"].is_a?(String) || flow["role_claim"].strip.empty?)
    if protocol == "vault-api-token"
      fail "API credentials only allowed for workload without verified OIDC" unless flow["purpose"] == "workload" && oidc_supported == false
      fail "API fallback needs reason" if flow.fetch("selection_reason", "").strip.empty?
    end
    if protocol == "saml" && oidc_supported
      fail "#{integration.fetch('name')}/#{flow.fetch('purpose')}: SAML requires oidc_supported=false"
    end
    if protocol == "saml" && flow.fetch("selection_reason", "").strip.empty?
      fail "#{integration.fetch('name')}/#{flow.fetch('purpose')}: SAML requires selection_reason"
    end
    if protocol == "oidc" && !oidc_supported
      fail "#{integration.fetch('name')}/#{flow.fetch('purpose')}: OIDC requires oidc_supported=true"
    end
    ref = flow.fetch("vault_ref")
    fail "invalid Vault ref" unless ref.is_a?(String) && ref.split('/').none? { |part| part.empty? || %w[. ..].include?(part) }
    env = metadata.fetch("environment")
    if protocol == "vault-api-token"
      fail "cross-environment API credential ref" unless ref.match?(%r{\Akv/CICD/#{env}(?:/[A-Za-z0-9._-]+)*\z})
    else
      provider = integration.fetch("provider")
      purpose = flow.fetch("purpose")
      fail "Vault identity ref must match environment, provider and purpose" unless ref.match?(%r{\Akv/iam/#{env}/#{provider}/[A-Za-z0-9][A-Za-z0-9._-]{0,62}/#{purpose}\z})
    end
    fail "redirect_uris must be an array" if flow.key?("redirect_uris") && !flow["redirect_uris"].is_a?(Array)
    (flow["redirect_uris"] || []).each do |redirect|
      https!(redirect)
    end
  end
end
puts "validate-iam-integrations: PASS (#{metadata.fetch('environment')}, #{integrations.length} providers)"
RUBY
