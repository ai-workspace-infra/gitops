#!/usr/bin/env python3
"""Fail if an enforced env-scoped Vault policy references a non-env kv path
without an exact reviewed exception. Static only; never contacts Vault."""
import datetime, pathlib, re, sys
import yaml

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
vault = root / 'security/vault'
exc_doc = yaml.safe_load((root / 'security/vault-exceptions/cross-env-paths.yaml').read_text())
spec = exc_doc['spec']
enforced = set(spec.get('enforced_policies') or [])
today = datetime.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else datetime.date.today()
errors, allowed, used = [], {}, set()
for e in spec.get('exceptions') or []:
    for k in ('policy', 'path', 'capabilities', 'reason', 'owner', 'exit_criteria', 'review_by'):
        if not e.get(k):
            errors.append(f'exception {e.get("policy")}:{e.get("path")} missing {k}')
    caps = sorted(e.get('capabilities') or [])
    if set(caps) - {'read'}:
        errors.append(f'exception {e["policy"]}:{e["path"]} may only grant read, got {caps}')
    if '*' in e.get('path', '') or '+' in e.get('path', ''):
        errors.append(f'exception {e["policy"]}:{e["path"]} must not use globs')
    if datetime.date.fromisoformat(str(e['review_by'])) < today:
        errors.append(f'exception {e["policy"]}:{e["path"]} expired {e["review_by"]}')
    allowed[(e['policy'], e['path'])] = caps

seen = set()
for f in sorted((vault / 'policies').glob('*.yaml')):
    d = yaml.safe_load(f.read_text()); name = d['metadata']['name']
    if name not in enforced:
        continue
    seen.add(name)
    m = re.search(r'-(uat|sit|prod|dev|shared)(?:-|$)', name)
    if not m:
        errors.append(f'{f}: enforced policy name has no env segment'); continue
    env = m.group(1)
    ok = re.compile(rf'^kv/(data|metadata)/(CICD/)?{env}/')
    for p in d['spec']['paths']:
        path, caps = p['path'], sorted(p['capabilities'])
        if ok.match(path):
            continue
        key = (name, path)
        if key not in allowed:
            errors.append(f'{f}: {path} is outside {env} scope and has no reviewed exception')
        elif allowed[key] != caps:
            errors.append(f'{f}: {path} capabilities {caps} != exception {allowed[key]}')
        else:
            used.add(key)
for missing in enforced - seen:
    errors.append(f'enforced policy {missing} not found')
for stale in set(allowed) - used:
    errors.append(f'stale exception {stale[0]}:{stale[1]} (remove it)')
if errors:
    print('\n'.join(errors), file=sys.stderr); sys.exit(1)
print(f'vault env isolation OK: {len(enforced)} enforced policy(ies), {len(used)} exception(s)')
