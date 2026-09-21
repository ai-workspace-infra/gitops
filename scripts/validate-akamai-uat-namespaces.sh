#!/usr/bin/env bash
set -euo pipefail

command -v ruby >/dev/null 2>&1 || {
  echo "Ruby is required to validate UAT Akamai namespace declarations" >&2
  exit 1
}

ruby -ryaml -e '
  root = "resources/svc.plus/uat/akamai"
  expected = %w[web-saas open-platform ai-workspace agent-proxy-jp agent-proxy-us agent-proxy-sg]
  expected.each do |namespace|
    path = File.join(root, "#{namespace}.yaml")
    abort("missing UAT Akamai namespace manifest: #{path}") unless File.file?(path)
    doc = YAML.safe_load(File.read(path), aliases: false)
    global = doc.fetch("global")
    abort("#{path}: namespace/workspace mismatch") unless global["workspace"] == namespace
    abort("#{path}: provider/environment/account contract mismatch") unless
      global["provider"] == "akamai-cloud" && global["environment"] == "uat" && global["account"] == "manbuzhe2026"
    hosts = doc.fetch("hosts")
    abort("#{path}: each Terraform namespace must declare exactly one host") unless hosts.length == 1
    host = hosts.first
    abort("#{path}: old observability migration source must never be Terraform-managed") if
      host["name"] == "observability.svc.plus" || host["tags"].to_a.include?("observability-source")
    if namespace.start_with?("agent-proxy-")
      region = { "agent-proxy-jp" => "jp-tyo-3", "agent-proxy-us" => "us-lax", "agent-proxy-sg" => "sg-sin-2" }.fetch(namespace)
      abort("#{path}: Agent Proxy region mismatch") unless host["region"] == region && host.fetch("groups", []).include?("agent_proxy")
    end
    if namespace == "ai-workspace"
      abort("#{path}: AI Workspace must remain sg-sin-2 / g8-dedicated-8-4") unless
        global["region"] == "sg-sin-2" && global["type"] == "g8-dedicated-8-4"
    end
    if namespace == "web-saas"
      domains = host.dig("host_vars", "service_domains").to_a
      abort("#{path}: Selfhost Console FQDN mismatch") unless domains.include?("console-selfhost-uat.onwalk.net")
    end
    if namespace == "open-platform"
      domains = host.dig("host_vars", "service_domains").to_a
      abort("#{path}: permanent Open Platform domains missing") unless
        %w[observability.svc.plus vault.svc.plus].all? { |fqdn| domains.include?(fqdn) }
    end
  end

  # The previous aggregate file is retained for compatibility/region facts,
  # but it is not one of the six supported Terraform namespace manifests.
  puts "Validated exactly six independent UAT Akamai Terraform namespace manifests"
'
