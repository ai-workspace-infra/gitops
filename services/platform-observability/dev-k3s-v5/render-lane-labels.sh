#!/bin/sh
# Render vmagent metric_relabel rules from lane namespace labels (source of truth).
# Lane namespaces carry: websaas.io/environment=sit|uat, websaas.io/feature-id, xlane.io/candidate.
# On SIT->UAT promotion: relabel the namespace (environment=uat), re-run this, reload vmagent.
kubectl get ns -l websaas.io/feature-id -o jsonpath='{range .items[*]}{.metadata.name} {.metadata.labels.websaas\.io/environment} {.metadata.labels.websaas\.io/feature-id} {.metadata.labels.xlane\.io/candidate}{"\n"}{end}' |
while read ns env fid cand; do
  echo "  - {source_labels: [namespace], regex: '$ns', target_label: environment, replacement: '$env'}"
  echo "  - {source_labels: [namespace], regex: '$ns', target_label: feature_id, replacement: '$fid'}"
  echo "  - {source_labels: [namespace], regex: '$ns', target_label: candidate, replacement: '$cand'}"
done
