#!/usr/bin/env bash
set -euo pipefail

command -v ruby >/dev/null 2>&1 || {
  echo "Ruby is required to validate runtime topology declarations" >&2
  exit 1
}

validated_count=0
while IFS= read -r topology_file; do
  ruby -ryaml -e '
    document = YAML.safe_load(File.read(ARGV.fetch(0)), aliases: false)
    migration = document.dig("spec", "runtime", "data", "migration")
    abort("#{ARGV.fetch(0)}: migration topology missing") unless migration.is_a?(Hash)
    abort("#{ARGV.fetch(0)}: migration execution flag must be absent") if migration.key?("enabled")
    abort("#{ARGV.fetch(0)}: migration strategy must remain async") unless migration["strategy"] == "async"
    abort("#{ARGV.fetch(0)}: migration must remain single-writer") unless migration["single_writer"] == true
    abort("#{ARGV.fetch(0)}: migration lag target must remain 60 seconds") unless migration["max_lag_seconds"] == 60
    abort("#{ARGV.fetch(0)}: migration must require a quiesce window") unless migration["require_quiesce_for_cutover"] == true
  ' "${topology_file}"
  validated_count=$((validated_count + 1))
done < <(find topology -path '*/runtime-topology.yaml' -type f -print | sort)

if [[ "${validated_count}" -eq 0 ]]; then
  echo "No runtime topology declarations found" >&2
  exit 1
fi

echo "Validated ${validated_count} runtime topology declaration(s)"

oidc_file="resources/svc.plus/prod/aws/github-actions-oidc.yaml"
test -f "${oidc_file}" || {
  echo "Missing GitHub Actions AWS OIDC declaration: ${oidc_file}" >&2
  exit 1
}

OIDC_FILE="${oidc_file}" EXPECTED_ENV=prod EXPECTED_TAG_SUBJECT='repo:ai-workspace-infra/platform-ops-toolkit:ref:refs/tags/v*' ruby -ryaml <<'RUBY'
file = ENV.fetch('OIDC_FILE')
document = YAML.safe_load(File.read(file), aliases: false)
spec = document.fetch('spec')
metadata = document.fetch('metadata')
aws = spec.fetch('aws')
abort "#{file}: invalid OIDC apiVersion/kind" unless document['apiVersion'] == 'gitops.svc.plus/v1alpha1' && document['kind'] == 'GitHubActionsOIDCConfig'
abort "#{file}: invalid metadata" unless metadata['project'] == 'svc.plus' && metadata['environment'] == ENV.fetch('EXPECTED_ENV') && metadata['provider'] == 'aws'
abort "#{file}: invalid provider URL/audience" unless spec['provider_url'] == 'https://token.actions.githubusercontent.com' && spec['audience'] == 'sts.amazonaws.com'
abort "#{file}: invalid AWS account/region" unless aws['account_id'].to_s.match?(/\A\d{12}\z/) && aws['region'].to_s.match?(/\A[a-z]+-[a-z]+-\d+\z/)
abort "#{file}: invalid role ARN" unless aws['role_name'].to_s.match?(/\A[A-Za-z0-9+=,.@_-]+\z/) && aws['role_arn'] == "arn:aws:iam::#{aws['account_id']}:role/#{aws['role_name']}"
subjects = spec.fetch('subjects')
abort "#{file}: missing subjects" unless subjects.is_a?(Array) && subjects.include?('repo:ai-workspace-infra/platform-ops-toolkit:ref:refs/heads/main') && subjects.include?(ENV.fetch('EXPECTED_TAG_SUBJECT'))
RUBY

echo "Validated GitHub Actions AWS OIDC declaration"

uat_oidc_file="resources/svc.plus/uat/aws/github-actions-oidc.yaml"
test -f "${uat_oidc_file}" || {
  echo "Missing UAT GitHub Actions AWS OIDC declaration: ${uat_oidc_file}" >&2
  exit 1
}

OIDC_FILE="${uat_oidc_file}" EXPECTED_ENV=uat EXPECTED_TAG_SUBJECT='repo:ai-workspace-infra/platform-ops-toolkit:ref:refs/tags/uat-daily-build-*' ruby -ryaml <<'RUBY'
file = ENV.fetch('OIDC_FILE')
document = YAML.safe_load(File.read(file), aliases: false)
spec = document.fetch('spec')
metadata = document.fetch('metadata')
aws = spec.fetch('aws')
abort "#{file}: invalid OIDC apiVersion/kind" unless document['apiVersion'] == 'gitops.svc.plus/v1alpha1' && document['kind'] == 'GitHubActionsOIDCConfig'
abort "#{file}: invalid metadata" unless metadata['project'] == 'svc.plus' && metadata['environment'] == ENV.fetch('EXPECTED_ENV') && metadata['provider'] == 'aws'
abort "#{file}: invalid provider URL/audience" unless spec['provider_url'] == 'https://token.actions.githubusercontent.com' && spec['audience'] == 'sts.amazonaws.com'
abort "#{file}: invalid AWS account/region" unless aws['account_id'].to_s.match?(/\A\d{12}\z/) && aws['region'].to_s.match?(/\A[a-z]+-[a-z]+-\d+\z/)
abort "#{file}: invalid role ARN" unless aws['role_name'].to_s.match?(/\A[A-Za-z0-9+=,.@_-]+\z/) && aws['role_arn'] == "arn:aws:iam::#{aws['account_id']}:role/#{aws['role_name']}"
subjects = spec.fetch('subjects')
abort "#{file}: missing subjects" unless subjects.is_a?(Array) && subjects.include?('repo:ai-workspace-infra/platform-ops-toolkit:ref:refs/heads/main') && subjects.include?(ENV.fetch('EXPECTED_TAG_SUBJECT')) && subjects.include?('repo:ai-workspace-infra/platform-ops-toolkit:environment:uat')
RUBY

echo "Validated UAT GitHub Actions AWS OIDC declaration"

uat_aws_agent_proxy="resources/svc.plus/uat/aws/agent-proxy-jp.yaml"
test -f "${uat_aws_agent_proxy}" || {
  echo "Missing UAT AWS Agent Proxy declaration: ${uat_aws_agent_proxy}" >&2
  exit 1
}
for required in \
  'provider: aws-cloud' \
  'account: "081434641398"' \
  'workspace: agent-proxy-jp' \
  'state_namespace: agent-proxy-jp' \
  'aws_region: ap-northeast-1' \
  "plan: {{ env.get('AGENT_PROXY_PLAN_API', 't4g.small') }}" \
  'billing_mode: on_demand' \
  'service_domains:' \
  'jp-xconnect.svc.plus'; do
  grep -Fq -- "${required}" "${uat_aws_agent_proxy}" || {
    echo "UAT AWS Agent Proxy declaration is missing: ${required}" >&2
    exit 1
  }
done

echo "Validated UAT AWS Agent Proxy declaration"

# The UAT apply refuses any delete or replacement, so a routed AWS host that
# follows the Debian "most recent" AMI lookup blocks every Daily as soon as
# Debian publishes a new image. Each such host must pin the image it runs.
ruby -ryaml <<'RUBY'
matrix = YAML.safe_load(File.read('topology/uat/hybrid/resource-matrix.yaml'), aliases: false)
rows = matrix.fetch('spec').fetch('resources').select do |row|
  row['provider'] == 'aws-cloud' && %w[terraform terraform+serverless].include?(row['management_mode'])
end
abort 'UAT Hybrid has no AWS Terraform lanes to validate' if rows.empty?
rows.each do |row|
  path = File.join('resources/svc.plus/uat/aws', "#{row.fetch('namespace')}.yaml")
  abort "#{row['namespace']}: missing AWS manifest #{path}" unless File.file?(path)
  # Jinja expressions are not YAML; their values are irrelevant here.
  hosts = YAML.safe_load(File.read(path).gsub(/\{\{.*?\}\}/, 'templated')).fetch('hosts')
  abort "#{path}: declares no hosts" if hosts.nil? || hosts.empty?
  hosts.each do |host|
    next if host['ami_id'].to_s.match?(/\Aami-[0-9a-f]{8,17}\z/)
    abort "#{path}: host #{host['name']} must pin ami_id; the AMI lookup replaces the instance on every new upstream image"
  end
end
puts 'Validated pinned AMIs on routed UAT AWS Terraform hosts'
RUBY

# GCP enforces compute.requireOsLogin in the UAT project. Resolve business
# manifests from the active Hybrid matrix so a provider switch cannot leave a
# newly selected GCP workload with unsupported metadata SSH authentication.
ruby -ryaml <<'RUBY'
matrix = YAML.safe_load(File.read('topology/uat/hybrid/resource-matrix.yaml'), aliases: false)
rows = matrix.fetch('spec').fetch('resources').select do |row|
  row['provider'] == 'gcp-cloud' && row['release_scope'] == 'business' &&
    %w[terraform terraform+serverless].include?(row['management_mode'])
end
abort 'UAT Hybrid has no GCP business workloads to validate' if rows.empty?

roots = %w[resources/onwalk.net/uat/gcp resources/svc.plus/uat/gcp]
rows.each do |row|
  namespace = row.fetch('namespace')
  paths = roots.map { |root| File.join(root, "#{namespace}.yaml") }.select { |path| File.file?(path) }
  abort "#{namespace}: expected exactly one GCP manifest, found #{paths.length}" unless paths.length == 1
  spec = YAML.safe_load(File.read(paths.first), aliases: false).fetch('spec')
  abort "#{namespace}: wrong GCP project" unless spec.fetch('project_id') == 'open-platform-uat'
  vms = spec.fetch('resources').fetch('spot_vms')
  abort "#{namespace}: each Spot VM must enable OS Login" unless vms.any? && vms.all? { |vm| vm['enable_oslogin'] == true }
end
puts "Validated OS Login for #{rows.length} UAT GCP business declaration(s)"
RUBY
