from pathlib import Path

p = Path('README.md')
s = p.read_text()

lines = []
for line in s.splitlines():
    if line.startswith('The exact historical flasher, hard-coded to the known-good session SHA, is preserved under '):
        lines.append('The session flasher used for this step is preserved under `reference/reconstructed/awfastboot_flash_initboot.py`. `reference/session-scripts/awfastboot.py` is a read-only fastboot probe and is not the flash writer.')
    elif line.startswith('The byte-for-byte scripts found in the uploaded '):
        lines.append('Original session scripts are preserved under [`reference/session-scripts/`](reference/session-scripts/). Reconstructed utilities are kept separately under [`reference/reconstructed/`](reference/reconstructed/). For new work, use the hardened tools under [`scripts/`](scripts/).')
    elif line.startswith('Hashes and metadata for the binary captures inspected while preparing this repository'):
        lines.append('Hashes and metadata for the verified binary captures used by this guide are in [`docs/verified-artifacts.md`](docs/verified-artifacts.md).')
    else:
        lines.append(line.replace('reference/chat-recovered/', 'reference/reconstructed/'))

p.write_text('\n'.join(lines) + '\n')

# Public Markdown must not expose local/private provenance or internal review sources.
banned = [
    'platform-tools.rar',
    'working-directory archive',
    'uploaded archive',
    'uploaded `',
    'chat/project',
    'reference/chat-recovered',
    'Source-archive re-check',
    'archive audit',
]
problems = []
for md in Path('.').rglob('*.md'):
    if '.git' in md.parts or '.github' in md.parts:
        continue
    text = md.read_text(errors='ignore')
    for term in banned:
        if term.lower() in text.lower():
            problems.append(f'{md}: {term}')
if problems:
    raise SystemExit('Private/internal provenance remains in public docs:\n' + '\n'.join(problems))
