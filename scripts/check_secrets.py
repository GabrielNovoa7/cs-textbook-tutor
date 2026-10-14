"""Scan tracked files and reachable Git blobs; print paths, never secret values."""
import re
import subprocess
from pathlib import Path


def git(*arguments):
    return subprocess.check_output(['git', *arguments])


pattern = re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}')
findings = set()
tracked = git('ls-files', '-z').decode().split('\0')
for name in filter(None, tracked):
    path = Path(name)
    if path.is_file() and pattern.search(path.read_bytes()):
        findings.add(name)
blobs_checked = 0
for line in git('rev-list', '--objects', '--all').decode().splitlines():
    object_id, _, name = line.partition(' ')
    if not name or git('cat-file', '-t', object_id).strip() != b'blob':
        continue
    blobs_checked += 1
    if pattern.search(git('cat-file', 'blob', object_id)):
        findings.add(name)
if findings:
    print('Possible keys found in paths: ' + ', '.join(sorted(findings)))
    raise SystemExit(1)
print(f'No OpenAI-key patterns found in {len(list(filter(None, tracked)))} tracked files or {blobs_checked} reachable Git blobs.')
