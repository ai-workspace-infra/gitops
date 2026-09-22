#!/usr/bin/env bash
set -euo pipefail

command -v ruby >/dev/null 2>&1 || {
  echo "Ruby is required to validate Akamai UAT declarations" >&2
  exit 1
}

ruby -ryaml -e '
  root = "resources/svc.plus/uat/akamai"
  expected = {
    "agent-proxy-jp" => { "host" => "jpn-tky", "region" => "jp-tyo-3", "group" => "agent_proxy" },
    "agent-proxy-us" => { "host" => "us-ca", "region" => "us-lax", "group" => "agent_proxy" },
    "agent-proxy-sg" => { "host" => "sg", "region" => "sg-sin-2", "group" => "agent_proxy" },
    "ai-workspace" => { "host" => "node", "region" => "sg-sin-2", "type" => "g8-dedicated-8-4", "group" => "ai_workspace" },
    "open-platform" => { "host" => "open-platform", "group" => "open_platform" },
    "web-saas" => { "host" => "web-saas", "domain" => "console-selfhost-uat.onwalk.net", "groups" => %w[web_saas database] }
  }

  # AI Aggregator has its own independently managed Akamai states. This
  # validator owns only the six Selfhost UAT namespaces; keep the aggregator
  # declarations in the same provider directory without folding them into the
  # six-namespace contract.
  files = Dir.glob(File.join(root, "*.yaml")).sort
  files = files.reject { |path| File.basename(path, ".yaml").start_with?("ai-aggregator-") }
  actual = files.map { |path| File.basename(path, ".yaml") }.sort
  abort("expected exactly these six Akamai UAT declarations: #{expected.keys.sort.join(", ")}; found #{actual.join(", ")}") unless actual == expected.keys.sort

  namespaces = []
  files.each do |path|
    stem = File.basename(path, ".yaml")
    document = YAML.safe_load(File.read(path), aliases: false)
    global = document.fetch("global")
    hosts = document.fetch("hosts")
    wanted = expected.fetch(stem)

    abort("#{path}: provider must be akamai-cloud") unless global["provider"] == "akamai-cloud"
    abort("#{path}: environment must be uat") unless global["environment"] == "uat"
    abort("#{path}: project must be svc.plus") unless global["project"] == "svc.plus"
    abort("#{path}: account must be the concrete account manbuzhe2026") unless global["account"] == "manbuzhe2026"
    abort("#{path}: state_namespace must match filename #{stem}") unless global["state_namespace"] == stem
    abort("#{path}: workspace must match state_namespace #{stem}") unless global["workspace"] == stem
    abort("#{path}: shared selfhost namespace is forbidden") if [global["state_namespace"], global["workspace"]].any? { |value| value.to_s.downcase.include?("selfhost") }
    abort("#{path}: expected exactly one host") unless hosts.is_a?(Array) && hosts.length == 1

    host = hosts.fetch(0)
    abort("#{path}: expected host #{wanted.fetch("host")}") unless host["name"] == wanted.fetch("host")
    groups = host["groups"] || []
    Array(wanted["groups"] || wanted["group"]).each do |group|
      abort("#{path}: host must belong to #{group}") unless groups.include?(group)
    end
    if wanted["region"]
      actual_region = host["region"] || global["region"]
      abort("#{path}: region must be #{wanted["region"]}") unless actual_region == wanted["region"]
    end
    if wanted["type"]
      abort("#{path}: global type must be #{wanted["type"]}") unless global["type"] == wanted["type"]
      abort("#{path}: host type must be #{wanted["type"]}") unless host["type"] == wanted["type"]
    end
    if wanted["domain"]
      domains = host.dig("host_vars", "service_domains") || []
      abort("#{path}: web-saas must serve #{wanted["domain"]}") unless domains.include?(wanted["domain"])
    end
    if stem == "open-platform"
      domains = host.dig("host_vars", "service_domains") || []
      %w[observability.svc.plus vault.svc.plus].each do |domain|
        abort("#{path}: open-platform must include #{domain}") unless domains.include?(domain)
      end
    end

    # The old observability host is an external migration source. Its service
    # domain may be served by the new open-platform node, but it must never be
    # an Akamai host identity/address in this declaration tree.
    identity = %w[name host hostname address ansible_host].map { |key| host[key]&.to_s }.compact
    abort("#{path}: legacy observability host cannot be declared as an Akamai host") if identity.include?("observability.svc.plus")

    namespaces << global.fetch("state_namespace")

    walk = lambda do |value, trail = []|
      case value
      when Hash
        value.each do |key, child|
          if key.to_s.match?(/(?:token|password|secret|private[_-]?key|api[_-]?key)/i)
            abort("#{path}: secret-like field is forbidden: #{(trail + [key]).join(".")}")
          end
          walk.call(child, trail + [key])
        end
      when Array
        value.each_with_index { |child, index| walk.call(child, trail + [index]) }
      when String
        abort("#{path}: private key material is forbidden") if value.match?(/-----BEGIN [^-]*PRIVATE KEY-----/)
      end
    end
    walk.call(document)
  end

  abort("state namespaces must be unique") unless namespaces.uniq.length == 6
  puts "Validated six Akamai UAT declarations with unique state namespaces"
'
