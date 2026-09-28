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

oidc_file="resources/svc.plus/prod/aws/github-actions-oidc.json"
test -f "${oidc_file}" || {
  echo "Missing GitHub Actions AWS OIDC declaration: ${oidc_file}" >&2
  exit 1
}

command -v jq >/dev/null 2>&1 || {
  echo "jq is required to validate the GitHub Actions AWS OIDC declaration" >&2
  exit 1
}

jq -e '
  .apiVersion == "gitops.svc.plus/v1alpha1" and
  .kind == "GitHubActionsOIDCConfig" and
  .metadata.project == "svc.plus" and
  .metadata.environment == "prod" and
  .metadata.provider == "aws" and
  .spec.provider_url == "https://token.actions.githubusercontent.com" and
  .spec.audience == "sts.amazonaws.com" and
  (.spec.aws.account_id | test("^[0-9]{12}$")) and
  (.spec.aws.region | test("^[a-z]+-[a-z]+-[0-9]+$")) and
  (.spec.aws.role_name | test("^[A-Za-z0-9+=,.@_-]+$")) and
  .spec.aws.role_arn == ("arn:aws:iam::" + .spec.aws.account_id + ":role/" + .spec.aws.role_name) and
  (.spec.subjects | type == "array" and length > 0) and
  (.spec.subjects | index("repo:ai-workspace-infra/platform-ops-toolkit:ref:refs/heads/main")) and
  (.spec.subjects | index("repo:ai-workspace-infra/platform-ops-toolkit:ref:refs/tags/v*"))
' "${oidc_file}" >/dev/null

echo "Validated GitHub Actions AWS OIDC declaration"

uat_oidc_file="resources/svc.plus/uat/aws/github-actions-oidc.json"
test -f "${uat_oidc_file}" || {
  echo "Missing UAT GitHub Actions AWS OIDC declaration: ${uat_oidc_file}" >&2
  exit 1
}

jq -e '
  .apiVersion == "gitops.svc.plus/v1alpha1" and
  .kind == "GitHubActionsOIDCConfig" and
  .metadata.project == "svc.plus" and
  .metadata.environment == "uat" and
  .metadata.provider == "aws" and
  .spec.provider_url == "https://token.actions.githubusercontent.com" and
  .spec.audience == "sts.amazonaws.com" and
  (.spec.aws.account_id | test("^[0-9]{12}$")) and
  (.spec.aws.region | test("^[a-z]+-[a-z]+-[0-9]+$")) and
  (.spec.aws.role_name | test("^[A-Za-z0-9+=,.@_-]+$")) and
  .spec.aws.role_arn == ("arn:aws:iam::" + .spec.aws.account_id + ":role/" + .spec.aws.role_name) and
  (.spec.subjects | type == "array" and length > 0) and
  (.spec.subjects | index("repo:ai-workspace-infra/platform-ops-toolkit:ref:refs/heads/main")) and
  (.spec.subjects | index("repo:ai-workspace-infra/platform-ops-toolkit:ref:refs/tags/uat-daily-build-*")) and
  (.spec.subjects | index("repo:ai-workspace-infra/platform-ops-toolkit:environment:uat"))
' "${uat_oidc_file}" >/dev/null

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
