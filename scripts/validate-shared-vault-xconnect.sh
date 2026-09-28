#!/usr/bin/env bash
set -euo pipefail

command -v ruby >/dev/null 2>&1 || {
  echo "Ruby is required to validate the shared Vault XConnect declaration" >&2
  exit 1
}

ruby -ryaml -e '
  path = "vpn-overlay/shared/xconnect-vault-shared.yaml"
  doc = YAML.safe_load(File.read(path))
  abort("wrong API version") unless doc["apiVersion"] == "gitops.svc.plus/v1alpha1"
  abort("wrong declaration kind") unless doc["kind"] == "XConnectOneNodeSet"
  metadata = doc.fetch("metadata")
  abort("wrong declaration name") unless metadata["name"] == "xconnect-vault-shared"
  abort("environment must be shared") unless metadata["environment"] == "shared"

  spec = doc.fetch("spec")
  network = spec.fetch("network")
  abort("wrong network ID") unless network["id"] == "net_shared_vault"
  abort("wrong overlay CIDR") unless network["cidr"] == "10.79.0.0/24"
  abort("overlay must not expose public WireGuard") unless network["public_wireguard_ingress"] == false
  transport = network.fetch("transport_profile")
  # The Gateway has its own hostname: vault.svc.plus stays on the existing
  # Vault node until cutover, so it cannot also front the overlay.
  gateway_host = "vault-xconnect.svc.plus"
  abort("gateway must use its dedicated TLS hostname") unless transport["host"] == gateway_host
  abort("the public /xconnect service must match the Gateway hostname") unless spec.dig("security", "allowed_public_service", "host") == gateway_host
  abort("gateway must use HTTPS port 443 and /xconnect") unless transport["port"] == 443 && transport["path"] == "/xconnect"
  abort("gateway must share Caddy TLS over its Unix socket") unless transport["frontend"] == "caddy-unix-h2c" && transport["listen_socket"] == "/run/xconnect-gateway/xray.sock"

  runtime = spec.fetch("runtime")
  %w[cli_release gateway_release xray_release].each do |key|
    abort("runtime.#{key} must be a pinned vX.Y.Z release") unless runtime[key].to_s.match?(/\Av\d+\.\d+\.\d+\z/)
  end

  gateway = spec.fetch("gateway")
  abort("vault-prod-0 must be the Gateway") unless gateway["id"] == "vault-prod-0" && gateway["role"] == "gateway"
  nodes = spec.fetch("fixed_nodes").map { |node| node.fetch("id") }.sort
  expected_nodes = %w[vault-prod-1 vault-prod-2]
  abort("One nodes must be vault-prod-1 and vault-prod-2") unless nodes == expected_nodes
  abort("all Vault nodes must require observability") unless spec.fetch("fixed_nodes").all? { |node| node["observability"] == "required" } && gateway["observability"] == "required"

  operator_id = "xconnect-darwin-haitaodemacbook-pro-rejoin.local"
  operators = spec.fetch("operator_devices")
  abort("the operator Mac must be declared once") unless operators.map { |item| item["id"] } == [operator_id]
  abort("operator enrollment must use a short-lived single-use invite") unless operators.first["enrollment"] == "short-lived-single-use-invite"
  operator_overlay_ip = operators.first.dig("xconnect", "overlay_ip")
  abort("operator Mac must use the reserved shared overlay address") unless operator_overlay_ip == "10.79.0.9"
  dns = spec.fetch("dns")
  abort("overlay DNS must be enabled on the Gateway address") unless dns["enabled"] == true && dns["interface"] == "xconone0" && dns["listen_address"] == "10.79.0.1"
  abort("overlay DNS must define its private zone and public recursive upstreams") unless dns["zone"] == "shared.internal" && dns["upstream_servers"] == %w[1.1.1.1 8.8.8.8]
  dns_alias = dns.fetch("records")
  expected_alias = [{"name" => "internal-xworkmate-bridge.svc.plus", "device_id" => "xconnect-linux-secops-shenlan-inspiron-5415-ops"}]
  abort("service DNS aliases must follow the enrolled One device address") unless dns_alias == expected_alias
  policy = spec.fetch("access_policy")
  abort("XConnect policy must default-deny") unless policy["default_action"] == "deny"
  rules = policy.fetch("rules")
  expected_targets = %w[vault-prod-0 vault-prod-1 vault-prod-2]
  ssh_rules = rules.select { |rule| Array(rule["ports"]) == [22] }
  valid_ssh = ssh_rules.length == 1 && ssh_rules.first["source_device_id"] == operator_id &&
    ssh_rules.first["destination_node_ids"].sort == expected_targets &&
    ssh_rules.first["protocol"] == "tcp" && ssh_rules.first["action"] == "allow"
  abort("only the operator Mac may SSH to the three Vault nodes") unless valid_ssh
  dns_rules = rules.select { |rule| Array(rule["ports"]) == [53] }
  dns_sources = %w[vault-prod-1 vault-prod-2 xconnect-linux-secops-shenlan-inspiron-5415-ops] + [operator_id]
  expected_dns = dns_sources.product(%w[tcp udp])
  valid_dns = dns_rules.length == expected_dns.length && expected_dns.all? do |source, protocol|
    dns_rules.any? do |rule|
      rule["source_device_id"] == source &&
        rule["destination_node_ids"] == ["vault-prod-0"] &&
        rule["protocol"] == protocol && rule["action"] == "allow"
    end
  end
  abort("only declared One devices may use TCP/UDP DNS on the Gateway") unless valid_dns
  abort("unexpected XConnect access policy rules") unless rules.length == ssh_rules.length + dns_rules.length

  gcp_path = "resources/xworktech.com/shared/gcp/vault-shared.yaml"
  gcp_doc = YAML.safe_load(File.read(gcp_path))
  abort("shared GCP declaration must target open-platform-prod") unless gcp_doc.dig("spec", "project_id") == "open-platform-prod"
  ssh_sources = gcp_doc.dig("spec", "ssh_source_ranges")
  access_mode = gcp_doc.dig("spec", "ssh_access_mode")
  case access_mode
  when "bootstrap-public"
    abort("bootstrap SSH firewall must allow only the operator egress /32") unless ssh_sources == ["35.79.83.48/32"]
  when "xconnect-zero"
    abort("zero-trust mode must remove the public SSH ingress rule") unless ssh_sources.empty?
    abort("zero-trust mode must not enable IAP") unless gcp_doc.dig("spec", "enable_iap_ssh") == false
  else
    abort("unknown shared Vault SSH access mode")
  end
  abort("shared GCP SSH sources must remain individual IPv4 /32s") unless ssh_sources.all? { |cidr| cidr.match?(/\A(?:\d{1,3}\.){3}\d{1,3}\/32\z/) }

  abort("runtime credential path must be Vault-backed") unless spec.dig("security", "credential_source") == "vault" && spec.dig("security", "credential_path") == "kv/data/CICD/shared/xconnect"
  scan = lambda do |value|
    case value
    when Hash
      value.each_value { |child| scan.call(child) }
    when Array
      value.each { |child| scan.call(child) }
    when String
      abort("private key material is forbidden") if value.match?(/-----BEGIN [^-]*PRIVATE KEY-----/)
      abort("invite/token-like values are forbidden") if value.match?(/(?:^|\s)(?:eyJ[a-zA-Z0-9_-]{10,}|hvs\.[a-zA-Z0-9_-]{12,})(?:$|\s)/)
    end
  end
  scan.call(doc)
  puts "Validated shared Vault XConnect topology, scoped DNS, and operator SSH policy"
'
