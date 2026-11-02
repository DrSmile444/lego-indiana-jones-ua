"""
Assembles the final patched FONT2_PC.FNT (Font 2, "Adventure"-style
title-card font): grows the pristine original's tables with 33 new
Ukrainian Cyrillic uppercase glyphs (see build_font2_atlas.py for why only
33, not 66) and splices in the freshly-built 1024x1024 DDS (from
build_font2_dds.py) in place of the original 512x512 one.

Unlike build_font1_ukrainian.py (which only ever remaps EXISTING glyph
slots in place, same file size throughout), this GROWS the file --
tools/fnt_tool.py's append_glyphs_and_mappings() appends new glyph metrics
records and new mapping entries, replaces DDS, and preserves/rebuilds the
engine texture descriptor and relocation footer. See
docs/research/font2-crash-investigation.md for the live crash diagnosis.

Applies tools/glyph_viewer/manual_overrides2.json last, if present -- same
mechanism as build_font1_ukrainian.py's manual_overrides.json, exported from
viewer.html's "Copy Python code" button while Font 2 is selected there.
These win over the computed layout for the same glyph_index, and survive a
full rebuild instead of being silently discarded.

Run from repo root:
    python tools/build_font2_ukrainian.py
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp1252, can't print Cyrillic
sys.path.insert(0, str(Path(__file__).parent))
from ua.formats.fnt import FntFile, GlyphMetrics  # noqa: E402
from build_font2_atlas import TARGETS, _measure_scale, compute_layout  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402
SRC = paths.GAME / "GAME/STUFF/TEXT/FONT2_PC.FNT"
NEW_DDS = paths.BUILD / "fonts/font2_patched.dds"
OUT = paths.BUILD / "fonts/font2/FONT2_PC.FNT"
MANUAL_OVERRIDES = paths.ASSETS / "fonts/font2/overrides.json"


def load_manual_overrides() -> list[dict]:
    if not MANUAL_OVERRIDES.exists():
        return []
    return json.loads(MANUAL_OVERRIDES.read_text(encoding="utf-8"))


def main():
    f = FntFile(str(SRC))
    print(f"source: {SRC} ({len(f.data)} bytes)")

    scale = _measure_scale()
    layout = compute_layout(scale)
    assert len(layout) == len(TARGETS)

    new_metrics = [GlyphMetrics(x=float(g["x"]), y=float(g["y"]), width=float(g["declared_width"])) for g in layout]
    new_dds_bytes = NEW_DDS.read_bytes()

    # glyph_index assignment is deterministic (see append_glyphs_and_mappings:
    # new indices are old_glyph_count, old_glyph_count+1, ...) -- predict it
    # up front so we can build BOTH the upper- and lower-case mapping entry
    # for each of the 33 new glyphs (this font's own convention: lowercase
    # codepoints just point at the same glyph_index as their uppercase
    # counterpart, see build_font2_atlas.py's module docstring) in one pass.
    _start, _end, _entries = f.find_mapping_table()
    old_glyph_count = max((e.glyph_index for e in _entries), default=-1) + 1
    predicted_indices = list(range(old_glyph_count, old_glyph_count + len(new_metrics)))

    mapping_entries = []
    for g, gi in zip(layout, predicted_indices):
        mapping_entries.append((g["upper_cp"], gi))
        mapping_entries.append((g["lower_cp"], gi))
        print(f"  glyph_index={gi} {g['ch']!r}: U+{g['upper_cp']:04X}/U+{g['lower_cp']:04X} "
              f"x={g['x']} y={g['y']} w={g['declared_width']}")

    new_indices = f.append_glyphs_and_mappings(new_metrics, mapping_entries, new_dds_bytes)
    assert new_indices == predicted_indices

    overrides = load_manual_overrides()
    if overrides:
        print(f"applying {len(overrides)} manual override(s) from "
              f"{MANUAL_OVERRIDES.relative_to(REPO)} (hand-tuned via tools/glyph_viewer/viewer.html)")
        for o in overrides:
            gi = o["glyph_index"]
            before = f.get_glyph_metrics(gi)
            f.set_glyph_metrics(gi, x=float(o["x"]), y=float(o["y"]), w=float(o["width"]))
            print(f"  glyph_index={gi} (U+{o['codepoint']:04X} {o['char']!r}) "
                  f"x {before.x:.0f}->{o['x']:.0f} y {before.y:.0f}->{o['y']:.0f} "
                  f"w {before.width:.0f}->{o['width']:.0f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    f.save(str(OUT))
    print(f"wrote {OUT} ({len(f.data)} bytes, source was {SRC.stat().st_size} bytes)")

    # self-check: re-read and confirm mapping + dds offset still consistent
    check = FntFile(str(OUT))
    info = check.inspect()
    print("self-check inspect():", info)
    assert info["header_math_ok"], "dds header pointer no longer matches DDS signature location!"
    assert info["dds_width"] == 1024 and info["dds_height"] == 1024, info
    mapping = check.list_mapping()
    got = {e.codepoint: e.glyph_index for e in mapping}
    codepoints_in_order = [e.codepoint for e in mapping]
    assert codepoints_in_order == sorted(codepoints_in_order), \
        "post-write self-check FAILED: mapping table is not sorted ascending by codepoint"
    override_by_gi = {o["glyph_index"]: o for o in overrides}
    for g, gi in zip(layout, new_indices):
        assert got[g["upper_cp"]] == gi, f"U+{g['upper_cp']:04X} missing/wrong glyph_index"
        assert got[g["lower_cp"]] == gi, f"U+{g['lower_cp']:04X} missing/wrong glyph_index"
        m = check.get_glyph_metrics(gi)
        if gi in override_by_gi:
            o = override_by_gi[gi]
            assert (m.x, m.y, m.width) == (float(o["x"]), float(o["y"]), float(o["width"])), \
                f"glyph_index={gi} override not applied: {m}"
        else:
            assert (m.x, m.y, m.width) == (float(g["x"]), float(g["y"]), float(g["declared_width"])), \
                f"glyph_index={gi} metrics mismatch: {m}"
    # Every pre-existing entry must still be present, untouched -- compared
    # as a multiset of (codepoint, glyph_index) pairs, NOT via the `got`
    # dict above: the original table has a couple of genuine duplicate
    # codepoints (e.g. U+00EC appears twice, at two different glyph
    # indices), which a dict would silently collapse to just the last one.
    from collections import Counter
    orig = FntFile(str(SRC))
    orig_pairs = Counter((e.codepoint, e.glyph_index) for e in orig.list_mapping())
    new_pairs = Counter((e.codepoint, e.glyph_index) for e in mapping)
    missing = orig_pairs - new_pairs
    assert not missing, f"pre-existing entries changed or lost: {missing}"
    print(f"self-check OK: {len(mapping)} total mapping entries "
          f"({len(orig.list_mapping())} original + {len(mapping_entries)} new), "
          f"{len(new_metrics)} new glyphs (glyph_index {new_indices[0]}..{new_indices[-1]})")

    # These are compatibility filenames for the PC loose-file install.
    # They all receive the same PC resource; this does not claim NGC support.
    for name in ("FONT2.FNT", "FONT2_NGC.FNT"):
        alias = OUT.with_name(name)
        alias.write_bytes(OUT.read_bytes())
        print(f"wrote PC compatibility alias: {alias}")


if __name__ == "__main__":
    main()
