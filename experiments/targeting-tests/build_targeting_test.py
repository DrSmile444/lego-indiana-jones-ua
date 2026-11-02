"""Stage v0.1.9 plus the targeting glyph fix for local game testing.

Historical releases remain immutable. Four Font 1 aliases and default custom
character name ID 85 change; the rebuilt ASI adds safe editor name rendering.
Loader, textures and Font 2 stay identical.
"""
import hashlib
import json
from pathlib import Path
import struct

from release_text_update import resources, pack
import txt_format

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / 'targeting-test-dist'
NAMES = {'STUFF/TEXT/' + name for name in
         ('FONT_PC.FNT', 'PC_FONT.FNT', 'PC_FONT_PC.FNT', 'PC_FONT_NGC.FNT')}


def main():
    baseline = ROOT / 'releases/v0.1.9'
    previous = json.loads((baseline / 'manifest.json').read_text(encoding='utf-8'))
    bundle = {name: (baseline / name).read_bytes() for name in previous['files']}
    for name, value in bundle.items():
        assert hashlib.sha256(value).hexdigest() == previous['files'][name]['sha256'], name
    old = resources(bundle['scripts/UKRAINIAN.uap'])
    text_name = 'STUFF/TEXT/ENGLISH.TXT'
    changed_names = NAMES | {text_name}
    new = [(name, (ROOT / 'release' / name).read_bytes() if name in changed_names else data)
           for name, data in old]
    assert {name for (name, a), (_, b) in zip(old, new) if a != b} == changed_names
    before_text = dict(old)[text_name].decode('utf-8-sig').splitlines()
    after_text = dict(new)[text_name].decode('utf-8-sig').splitlines()
    differences = [(a, b) for a, b in zip(before_text, after_text) if a != b]
    assert len(before_text) == len(after_text) and len(differences) == 1
    left, right = (txt_format.ENTRY_RE.match(line) for line in differences[0])
    assert left and right and left['id'] == right['id'] == '85'
    assert left['text'] == 'Незнайомець' and right['text'] == 'Форелька'
    for (name, a), (_, b) in zip(old, new):
        if name not in NAMES:
            continue
        # The alias must preserve the full texture descriptor, DDS and footer.
        dds = 8 + struct.unpack_from('<I', a, 8)[0]
        assert len(a) == len(b) and a[dds - 128:] == b[dds - 128:]
    bundle['scripts/UKRAINIAN.uap'] = pack(new)
    assert resources(bundle['scripts/UKRAINIAN.uap']) == new
    bundle['scripts/UKRAINIAN.asi'] = (ROOT / 'runtime/asi/dist/scripts/UKRAINIAN.asi').read_bytes()
    bundle['scripts/UKRAINIAN/README.txt'] += (
        '\nТЕСТОВЕ ВИПРАВЛЕННЯ 2026-10-31\n'
        'Відновлено нижній трикутник прицілу U+00AB. '
        'Loader незмінний; ASI адаптує відображення UTF-8 імен.\n'
        'Папка audio є штатною частиною гри та має залишатися на місці.\n'
        'Початкові імена власних персонажів: Форелька та Льоля.\n'
        'Редактор відображає повні UTF-8 літери в комірках імені.\n'
        'Виправлено переповнення 16-байтового буфера повного імені.\n'
        'Тимчасовий автопропуск катсцен: scripts/UKRAINIAN-test.ini, '
        '[Practice] SkipCutscenes=1. Для повернення катсцен: 0 і перезапуск гри.\n'
        'У режимі автопропуску звук катсцени може продовжувати грати.\n'
    ).encode('utf-8')
    bundle['scripts/UKRAINIAN-test.ini'] = b'[Practice]\r\nSkipCutscenes=0\r\n'
    manifest = {
        'version': '0.1.9-targeting-forelka-lolia-test',
        'baseline': '0.1.9',
        'supported_exe_sha256': previous['supported_exe_sha256'],
        'changed_resources': sorted(changed_names),
        'files': {},
    }
    for name, data in bundle.items():
        destination = OUT / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        manifest['files'][name] = {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
