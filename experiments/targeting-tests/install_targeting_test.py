"""Install the local targeting test bundle, preserving native game assets."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = Path(__file__).parent / 'targeting-test-dist'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def install(game):
    game = game.resolve()
    manifest = json.loads((BUNDLE / 'manifest.json').read_text(encoding='utf-8'))
    running = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq LEGOIndy.exe', '/FO', 'CSV', '/NH'],
                             capture_output=True, text=True, check=True)
    if 'legoindy.exe' in running.stdout.lower():
        raise RuntimeError('Close the game before installation')
    if digest(game / 'LEGOIndy.exe') != manifest['supported_exe_sha256']:
        raise ValueError('Unsupported game executable')
    baseline = json.loads((ROOT / 'releases/v0.1.9/manifest.json').read_text(encoding='utf-8'))
    proof = ROOT / 'docs/research/targeting-fix-installation.json'
    previous_test = json.loads(proof.read_text(encoding='utf-8')) if proof.exists() else {}
    previous_files = {item['name']: item['installed_sha256'] for item in previous_test.get('files', [])}
    for name, item in manifest['files'].items():
        if not (game / name).resolve().is_relative_to(game):
            raise ValueError('Target outside game directory')
        if digest(BUNDLE / name) != item['sha256']:
            raise ValueError(f'Bundle mismatch: {name}')
        if name in ('dinput8.dll', 'scripts/UKRAINIAN.asi', 'scripts/UKRAINIAN.uap') and (game / name).exists():
            if digest(game / name) not in (baseline['files'][name]['sha256'], item['sha256'], previous_files.get(name)):
                raise ValueError(f'Unexpected existing mod: {name}')
    audio = sorted((game / 'audio').rglob('*'))
    audio = [path for path in audio if path.is_file()]
    if len(audio) < 279:
        raise ValueError('Missing native audio; verify the game in Steam first')
    protected = audio + [game / name for name in
                         ('LEGOIndy.exe', 'GAME.DAT', 'RAIDERS.DAT', 'TEMPLE.DAT', 'CRUSADE.DAT', 'binkw32.dll')]
    before = {str(path.relative_to(game)): digest(path) for path in protected}
    backup = game / ('.legoindy-ua-before-targeting-test-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir()
    entries = []
    for name, item in manifest['files'].items():
        target = game / name
        entry = {'name': name, 'existed': target.exists(), 'installed_sha256': item['sha256']}
        if target.exists():
            saved = backup / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            entry['previous_sha256'] = digest(target)
            assert digest(saved) == entry['previous_sha256']
        entries.append(entry)
    state = {'version': manifest['version'], 'game': str(game), 'backup': str(backup),
             'phase': 'installing', 'files': entries}
    (backup / 'state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    changed = []
    try:
        for entry in entries:
            target = game / entry['name']
            target.parent.mkdir(parents=True, exist_ok=True)
            changed.append(entry)
            shutil.copy2(BUNDLE / entry['name'], target)
            assert digest(target) == entry['installed_sha256'], entry['name']
        assert before == {str(path.relative_to(game)): digest(path) for path in protected}, 'Native game assets changed'
    except Exception:
        for entry in reversed(changed):
            target = game / entry['name']
            if entry['existed']:
                shutil.copy2(backup / entry['name'], target)
            elif target.is_file():
                target.unlink()
        state['phase'] = 'rolled-back'
        (backup / 'state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
        raise
    state.update(phase='installed', audio_files_preserved=len(audio), protected_assets_verified=len(before))
    (backup / 'state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    proof.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(state, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    install(parser.parse_args().game)
