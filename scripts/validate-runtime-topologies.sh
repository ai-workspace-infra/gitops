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
