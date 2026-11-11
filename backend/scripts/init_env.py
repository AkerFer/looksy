"""Create a local development .env with new secrets; never overwrite an existing file."""
import os
from pathlib import Path
import secrets


def initialize(project_root: Path) -> bool:
    template = (project_root / '.env.example').read_text(encoding='utf-8')
    replacements = {
        'DJANGO_SECRET_KEY': secrets.token_urlsafe(48),
        'POSTGRES_PASSWORD': secrets.token_urlsafe(32),
    }
    lines = []
    for line in template.splitlines():
        key = line.partition('=')[0]
        lines.append(f'{key}={replacements[key]}' if key in replacements else line)
    try:
        fd = os.open(project_root / '.env', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write('\n'.join(lines) + '\n')
    return True


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    if initialize(root):
        print('Created .env with new local secrets. Secret values are not printed.')
    else:
        print('.env already exists; left unchanged.')
