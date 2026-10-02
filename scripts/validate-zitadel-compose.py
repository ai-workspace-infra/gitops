"""Validate Compose structure in CI; runtime secret files remain mandatory."""
from pathlib import Path
import subprocess
import tempfile
import yaml

root = Path(__file__).resolve().parents[1]
source = root / 'compose/zitadel/docker-compose.yml'
document = yaml.safe_load(source.read_text())
# Older runner Compose validates host env_file existence even with
# --no-env-resolution. Only the disposable CI copy omits this host-only read.
# The source contract tests assert the required absolute secret-file paths.
for service in document['services'].values():
    service.pop('env_file', None)
with tempfile.TemporaryDirectory(prefix='zitadel-compose-ci-') as directory:
    rendered = Path(directory) / 'compose.yaml'
    rendered.write_text(yaml.safe_dump(document))
    subprocess.run(['docker', 'compose', '--env-file', str(source.parent / '.env.shared'),
                    '-f', str(rendered), 'config', '--quiet'], check=True)
