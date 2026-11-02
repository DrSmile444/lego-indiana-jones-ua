"""
Assembles the final patched PC_FONT_PC.FNT (Font 1, main UI font):
1. Starts from the community-proven working Cyrillic PC_FONT_PC.FNT.
2. Splices in a patched mip0-mip4 DXT5 block (built by build_font1_dds.py)
   where the 8 unused Polish glyph slots (Ą Ć Ę ę Ł ń Ś ś) have been
   repainted with calibrated Franklin Gothic Medium Ukrainian glyphs, at
   their correct pixel rects (see build_font1_atlas.py TARGETS) at EVERY
   mip level down to 64x64 -- everything else in the file (header, mips
   5-10, every other glyph, at every level) is byte-identical to the
   source.
3. Repoints those 8 mapping-table entries' Unicode codepoint fields to the
   four Ukrainian letters (upper+lower), via fnt_tool.remap_and_resort — a
   2-byte-per-entry edit, no resize.
4. Writes a corrected advance Width into each of those 8 glyphs' metrics
   records (X/Y unchanged — they already correctly describe the donor rect;
   only Width is replaced), using the exact same numbers
   build_font1_atlas.py used to paint the pixels, so the rendered glyph and
   its advance width always agree. This was NOT possible before the glyph
   metrics table was decoded (see local/research/fnt-format-findings.md) —
   until now these 8 glyphs kept advancing by their old Polish donor's
   width, which no longer matched the (usually much narrower) painted
   Ukrainian glyph.
5. Applies tools/glyph_viewer/manual_overrides.json last, if present --
   hand-tuned X/Y/Width corrections exported from tools/glyph_viewer/
   viewer.html's "Copy Python code" button (pasted here as data instead of
   code so they survive a full rebuild instead of being silently discarded
   the next time this script regenerates everything from SRC). These win
   over anything computed above for the same glyph_index.
6. Restores Indiana Jones UI base=37 instead of the donor's base=0,
   needed when the engine switches to the separate controller-button font.
   Writes all four PC loose-file UI aliases with identical contents.
7. Adds U+00AB as an alias of the donor's U+00AC upward triangle so
   the engine-generated bottom targeting marker renders correctly.

Run from repo root:
    python tools/build_font1_ukrainian.py
"""
import json
import sys
import struct
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp1252, can't print Cyrillic
sys.path.insert(0, str(Path(__file__).parent))
from ua.formats.fnt import FntFile  # noqa: E402
from build_font1_atlas import _measure_scale, compute_all_metrics  # noqa: E402
from build_font1_dds import mip_levels, NUM_PATCHED_LEVELS  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402
SRC = paths.DONORS / "cyrillic-font-patch/PC_FONT_PC.FNT"
NEW_DDS = Path(sys.argv[1]) if len(sys.argv) > 1 else None  # patched DDS from build_font1_dds.py
OUT = paths.BUILD / "fonts/font1/PC_FONT_PC.FNT"
MANUAL_OVERRIDES = paths.ASSETS / "fonts/font1/overrides.json"
# The donor uses a different game's base=0. Indiana Jones switches to
# separate BUTTONS_* fonts inline; its UI base=37 must survive that switch.
UI_BASELINE = 37.0


def load_manual_overrides() -> list[dict]:
    if not MANUAL_OVERRIDES.exists():
        return []
    return json.loads(MANUAL_OVERRIDES.read_text(encoding="utf-8"))

REMAP = [
    (0x0104, 0x0406),  # Ą -> І
    (0x0106, 0x0407),  # Ć -> Ї
    (0x0118, 0x0404),  # Ę -> Є
    (0x0119, 0x0454),  # ę -> є
    (0x0141, 0x0490),  # Ł -> Ґ
    (0x0144, 0x0456),  # ń -> і
    (0x015A, 0x0457),  # Ś -> ї
    (0x015B, 0x0491),  # ś -> ґ
]

# "І"/"і" are visually IDENTICAL to Latin "I"/"i" in this atlas (see the
# 15th-bug note in build_font1_atlas.py TARGETS) -- rather than paint a
# second copy of the same shape, these two just reuse Latin's own (X, Y,
# Width) outright. No texture painting involved, only a metrics-table copy.
# Keyed by the NEW (Ukrainian) codepoint; value is the Latin codepoint whose
# metrics to copy.
LATIN_REUSE = {
    0x0406: ord("I"),  # І -> Latin I
    0x0456: ord("i"),  # і -> Latin i
}

# Total size of mip0..mip(NUM_PATCHED_LEVELS-1) combined -- see
# build_font1_dds.py's 11th-bug note for why only these levels are patched.
_levels = list(mip_levels())
PATCHED_SIZE = sum(nbytes for _level, _size, _offset, nbytes in _levels[:NUM_PATCHED_LEVELS])


def main():
    f = FntFile(str(SRC))
    struct.pack_into("<f", f.data, 0x28, UI_BASELINE)
    dds_off = f.dds_offset
    header_end = dds_off + 128
    print(f"source: {SRC}")
    print(f"dds_offset={dds_off}, patched range=[{header_end}, {header_end + PATCHED_SIZE}) "
          f"(mip0..mip{NUM_PATCHED_LEVELS - 1})")

    if NEW_DDS is not None:
        new_dds = open(NEW_DDS, "rb").read()
        new_mips = new_dds[128:128 + PATCHED_SIZE]
    else:
        raise SystemExit("pass the patched DDS path as argv[1] (built by build_font1_dds.py)")

    assert len(new_mips) == PATCHED_SIZE, len(new_mips)

    before = bytes(f.data[header_end:header_end + PATCHED_SIZE])
    f.data[header_end:header_end + PATCHED_SIZE] = new_mips
    after = bytes(f.data[header_end:header_end + PATCHED_SIZE])
    print(f"mip0..mip{NUM_PATCHED_LEVELS - 1} texture bytes changed: "
          f"{sum(a != b for a, b in zip(before, after))} / {PATCHED_SIZE}")

    remap_dict = dict(REMAP)
    sorted_items = f.remap_and_resort(remap_dict)
    print(f"remapped and re-sorted {len(sorted_items)} mapping entries "
          f"(was: in-place edit that left the table out of order -- "
          f"confirmed in a real game launch to break rendering for U+0456 'i')")
    for old_cp, new_cp in REMAP:
        print(f"  U+{old_cp:04X} -> U+{new_cp:04X}")

    # Write corrected metrics for the 8 repointed glyphs. For the 6 that got
    # freshly painted, X/Y are left untouched (they already correctly
    # describe the donor rect the pixels were painted into) -- only Width
    # changes, from the old Polish donor's width to the width actually
    # painted for the new Ukrainian glyph (plus a small side bearing). Uses
    # compute_all_metrics() from build_font1_atlas.py so this can never
    # drift from what was painted. For "І"/"і" (LATIN_REUSE), X/Y/Width are
    # all copied from the existing Latin glyph instead -- see LATIN_REUSE's
    # own comment above for why.
    scale = _measure_scale()
    metrics_by_char = {m["ch"]: m for m in compute_all_metrics(scale)}
    new_mapping = {e.codepoint: e.glyph_index for e in f.list_mapping()}
    for old_cp, new_cp in REMAP:
        glyph_index = new_mapping[new_cp]
        before_metrics = f.get_glyph_metrics(glyph_index)
        if new_cp in LATIN_REUSE:
            latin_gi = new_mapping[LATIN_REUSE[new_cp]]
            latin = f.get_glyph_metrics(latin_gi)
            f.set_glyph_metrics(glyph_index, x=latin.x, y=latin.y, w=latin.width)
            print(f"  glyph_index={glyph_index} (U+{new_cp:04X}) reused Latin "
                  f"{chr(LATIN_REUSE[new_cp])!r} (glyph_index={latin_gi}): "
                  f"x={latin.x:.0f} y={latin.y:.0f} w={latin.width:.0f}")
        else:
            ch = chr(new_cp)
            m = metrics_by_char[ch]
            f.set_glyph_metrics(glyph_index, w=float(m["declared_width"]))
            print(f"  glyph_index={glyph_index} (U+{new_cp:04X}) width {before_metrics.width:.0f} -> {m['declared_width']}")

    overrides = load_manual_overrides()
    if overrides:
        print(f"applying {len(overrides)} manual override(s) from "
              f"{MANUAL_OVERRIDES.relative_to(REPO)} (hand-tuned via tools/glyph_viewer/viewer.html)")
        for o in overrides:
            gi = o["glyph_index"]
            before_metrics = f.get_glyph_metrics(gi)
            f.set_glyph_metrics(gi, x=float(o["x"]), y=float(o["y"]), w=float(o["width"]))
            print(f"  glyph_index={gi} (U+{o['codepoint']:04X} {o['char']!r}) "
                  f"x {before_metrics.x:.0f}->{o['x']:.0f} y {before_metrics.y:.0f}->{o['y']:.0f} "
                  f"w {before_metrics.width:.0f}->{o['width']:.0f}")

    f.add_mapping_alias(0x00AB, 0x00AC)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    f.save(str(OUT))
    print(f"wrote {OUT} ({len(f.data)} bytes, source was {Path(SRC).stat().st_size} bytes)")
    assert len(f.data) == Path(SRC).stat().st_size, "file size must be unchanged"

    # self-check: re-read and confirm mapping + dds offset still consistent
    check = FntFile(str(OUT))
    info = check.inspect()
    print("self-check inspect():", info)
    assert info["header_math_ok"], "dds header pointer no longer matches DDS signature location!"
    assert check.base == UI_BASELINE, "UI baseline required for inline controller icons"
    mapping = check.list_mapping()
    got = {e.codepoint: e.glyph_index for e in mapping}
    for old_cp, new_cp in REMAP:
        assert new_cp in got, f"post-write self-check FAILED: U+{new_cp:04X} not in mapping table"
        assert old_cp not in got, f"post-write self-check FAILED: old U+{old_cp:04X} still present"
    codepoints_in_order = [e.codepoint for e in mapping]
    assert codepoints_in_order == sorted(codepoints_in_order), \
        "post-write self-check FAILED: mapping table is not sorted ascending by codepoint"
    override_by_gi = {o["glyph_index"]: o for o in overrides}
    for old_cp, new_cp in REMAP:
        gi = got[new_cp]
        actual = check.get_glyph_metrics(gi)
        if gi in override_by_gi:
            o = override_by_gi[gi]
            assert (actual.x, actual.y, actual.width) == (o["x"], o["y"], o["width"]), \
                f"post-write self-check FAILED: U+{new_cp:04X} override not applied: {actual}"
        elif new_cp in LATIN_REUSE:
            latin = check.get_glyph_metrics(got[LATIN_REUSE[new_cp]])
            assert (actual.x, actual.y, actual.width) == (latin.x, latin.y, latin.width), \
                f"post-write self-check FAILED: U+{new_cp:04X} doesn't match reused Latin glyph: {actual} vs {latin}"
        else:
            expected_w = metrics_by_char[chr(new_cp)]["declared_width"]
            assert actual.width == expected_w, \
                f"post-write self-check FAILED: U+{new_cp:04X} width {actual.width} != expected {expected_w}"
    print(f"self-check OK: all 8 target codepoints present, table sorted ascending, "
          f"widths match, {len(overrides)} manual override(s) applied, {len(mapping)} total mapping entries")

    # All loose-file UI slots must receive the same resource on rebuild.
    for name in ("FONT_PC.FNT", "PC_FONT.FNT", "PC_FONT_NGC.FNT"):
        alias = OUT.with_name(name)
        alias.write_bytes(OUT.read_bytes())
        print(f"wrote PC compatibility alias: {alias}")


if __name__ == "__main__":
    main()
