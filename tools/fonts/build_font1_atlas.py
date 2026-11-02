"""
Builds the patched Font 1 atlas texture (the mip0 PNG that
build_font1_ukrainian.py later splices into the .FNT as a DXT5 DDS).

Renders the 8 Ukrainian glyphs (I i Yi yi Ye ye Ghe-upturn ghe-upturn) from
Franklin Gothic Medium and paints them into the exact pixel rects of the 8
donor Polish glyphs (Ą Ć Ę ę Ł ń Ś ś) in the already-Cyrillic-extended
community atlas, then writes the composited PNG.

IMPORTANT (fixed after real in-game testing): native glyphs in this atlas are
NOT hollow outlines -- sampling an existing glyph (Latin "I") showed a solid
white (255,255,255,255) interior with a dark (41,40,41,255) outline baked
directly into the texture. An earlier version of this script rendered with a
transparent fill (outline only), which looked fine in an on-white-background
PNG preview (indistinguishable from solid fill against a white backdrop!) but
showed up in the actual game as unfilled/hollow "i"-shaped holes -- visually
broken, especially at larger on-screen text sizes. Always render with a solid
white fill.

Run from repo root:
    python tools/build_font1_atlas.py
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402
ATLAS_SRC = paths.BUILD / "fonts/pcfont_0.png"  # decoded from the community patch's DDS (see local/research/fnt-format-findings.md)
FRANKLIN = paths.FONTS / "Franklin Gothic Medium Regular.ttf"
OUT_PNG = paths.BUILD / "fonts/pcfont_patched_ukrainian.png"

# Donor Polish glyph -> target Ukrainian glyph, rects taken from the now-
# decoded glyph metrics table (tools/fnt_tool.py get_glyph_metrics /
# local/research/fnt-format-findings.md section "Glyph metrics table --
# SOLVED"), NOT eyeballed off the PNG anymore. See section 4 for the
# corresponding codepoint remap.
#
# IMPORTANT (6th real bug, found after decoding the metrics table): the
# previous version of this list used hand-measured rects (483-527 / 529-575,
# heights 44/46) that turned out to be WRONG -- the authoritative metrics
# table says every row in this atlas is exactly 48px tall (matching the
# font's own `height` header field) and the two donor rows sit back-to-back
# at y=(480,528) and y=(528,576) with zero gap. The first row (donor pair
# used for I_upper/Yi_upper) was off by 3px, the second row (used for the
# other six) by only 1px -- which lines up exactly with I_upper/Yi_upper
# being the visibly worse-misaligned/oversized pair in real gameplay
# testing. The baseline pixel values below are kept unchanged: they were
# measured directly off neighboring donor letters' actual ink, not derived
# from these rect boundaries, so they remain valid.
# IMPORTANT (15th real bug -- not really a bug, a simplification requested
# after the user noticed it themselves): "І"/"і" used to be rendered here
# from Franklin Gothic like the other 6, painted into their own donor rect
# (glyph_index 160 / 168). But Cyrillic "І"/"і" are visually IDENTICAL to
# Latin "I"/"i" in essentially every font -- confirmed directly: even
# Franklin Gothic Medium's own Cyrillic "І" glyph has the exact same
# FreeType bounding box as its Latin "I" (both (7,0,20,67) at the same
# render size). Repainting a second copy of the same shape only meant
# double the chances of a compression/positioning bug for a letter that
# already existed, pristine and never recompressed, elsewhere in this same
# atlas. These two are no longer painted here at all -- see LATIN_REUSE in
# build_font1_ukrainian.py, which instead points their metrics straight at
# the existing Latin "I"/"i" glyph's own (X, Y, Width).
TARGETS = [
    ("Ї", "Yi_upper",  (247, 480, 279, 528)),  # was donor glyph_index 162
    ("Є", "Ye_upper",  (2,   528, 32,  576)),  # was donor glyph_index 164
    ("є", "ye_lower",  (35,  528, 64,  576)),  # was donor glyph_index 165
    ("Ґ", "Ghe_upper", (69,  528, 99,  576)),  # was donor glyph_index 166
    ("ї", "yi_lower",  (160, 528, 192, 576)),  # was donor glyph_index 169
    ("ґ", "ghe_lower", (197, 528, 224, 576)),  # was donor glyph_index 170
]

# IMPORTANT (12th real bug, found via direct in-game observation, visible
# only in a heavily contrast-boosted screenshot -- too subtle for a normal
# screenshot or even a lossless one at normal contrast): a faint "dirty
# line" a few pixels beside some of our glyphs (reported: left of "і", right
# of "ї"). Root cause is texture-atlas bleeding: our clear step (below) only
# ever cleared the DECLARED rect expanded to the nearest 4px block boundary
# -- a few pixels short of the true gap to the next real glyph in the row
# (measured directly from the metrics table: donor rows pack glyphs only
# 3-7px apart). Whatever the exact GPU-side mechanism (mip generation,
# bilinear sampling reaching past our declared UV rect, or both), it's close
# enough to visibly blend in a sliver of the neighboring glyph's own ink --
# most visible for "і" (its left neighbor at this donor row's packing is the
# unused Polish "ł", only 6px away) since a thin glyph has little of its own
# ink to visually dominate over a faint intruder.
#
# Fixed: clear the FULL gap up to each real neighbor's own declared rect
# edge (touching it, not just approaching it), not just up to a rounded
# block boundary. For gaps between two of OUR OWN 8 glyphs this is free (we
# own both sides). For gaps to an unrelated donor glyph (Latin Ą/Ć next to
# I_upper/Yi_upper's row, Polish ł next to Ghe_upper/i_lower) this
# deliberately erases a couple of pixels of that neighbor's own antialiased
# edge -- accepted: none of these particular leftover Polish/Latin-Extended
# glyphs are used by any codepoint left in the Ukrainian release.
CLEAR_X_OVERRIDE = {
    # name: (left edge, right edge) -- replaces TARGETS' own x0/x1 as the
    # horizontal clear boundary, still expanded to the block grid afterward.
    "Yi_upper":  (242, 285),  # left: Latin "ą" ends 242; right: "ć" (idx163) starts 285
    "Ye_upper":  (2,   36),   # right: touches our own ye_lower at 36 (widened, 13th/16th-bug note below)
    "ye_lower":  (36,  69),   # left: our own Ye_upper ends 36; right: our own Ghe_upper at 69
    "Ghe_upper": (64,  103),  # left: our own ye_lower ends 64; right: Polish "ł" (idx167) starts 103
    "yi_lower":  (153, 197),  # left: where "i_lower" used to end (now unpainted, no longer ours -- see TARGETS note); right: our own ghe_lower at 197
    "ghe_lower": (192, 224),  # left: our own yi_lower ends 192; right: no further neighbor found
}

RENDER_SIZE = 300
RENDER_STROKE = round(RENDER_SIZE * 3 / 46)  # user-verified 46pt/3pt ratio
FILL_COLOR = (255, 255, 255, 255)   # sampled from the atlas's own "I" interior
STROKE_COLOR = (41, 40, 41, 255)    # sampled from the atlas's own "I" outline

# Reference measured directly off EXISTING, already-correctly-sized Cyrillic
# glyphs already in this atlas (not Latin, not the Polish donor rects):
#   Cyrillic "O" (row "MNOPRSTUF", y=674-714): cap-height 39px
#   Cyrillic "a" (row "-EEYaYaabvg", y=769-810): x-height 31px
#
# IMPORTANT (fixed after real in-game testing, 2nd pass): the first fix used a
# PER-GLYPH scale that stretched each rendered character to fill its whole
# donor rect. That made lowercase glyphs (i, yi, ye, ghe-upturn) render far
# too tall -- a rect inherited from a Polish donor letter is sized for that
# row's overall line height, not for one specific glyph's natural bounding
# box, so "fit tightly to rect" ignored the real uppercase/lowercase height
# difference entirely. Fix: calibrate ONE global scale from cap-height and
# apply it uniformly to every glyph, preserving Franklin Gothic's own natural
# relative proportions between capitals, x-height letters, and dotted
# ascenders.
CAP_HEIGHT_TARGET = 39

# IMPORTANT (fixed after real in-game testing, 3rd pass): baseline-aligning to
# (rect_bottom - 1) was itself wrong for the two donor rows used here. Those
# rows reserve extra space *below* the true baseline for descenders/cedillas
# on letters like Ę/ę/Ą/ą (which dip below baseline) -- but our 8 glyphs have
# no descenders, so bottom-aligning to the row's outer edge made them sit
# visibly too low ("sticks out below the line" in-game). Measured the TRUE
# baseline directly from neighboring donor letters *without* descenders,
# still present untouched in the same rows (Ł/l-with-stroke/n-acute/S-acute/
# s-acute all bottom out at y=568 despite their row spanning to y=575; C-acute/
# c-acute bottom out at y=520 despite their row spanning to y=527) rather than
# assuming "row bottom - 1" generically.
#
# IMPORTANT (fixed after decoding the glyph metrics table, 6th pass): the
# dict keys below used to be the hand-measured (wrong) row tops 483/529.
# The keys are updated to the now-confirmed true row tops (480/528) so
# lookups by TARGETS' rect y0 still hit.
#
# IMPORTANT (9th real bug, found in real gameplay testing against a drawn
# reference line): the values (520/568) were measured by eye off neighboring
# donor letters' ink and were still a little too high -- real words
# ("Увiмк.", a diagnostic string) showed our glyphs sitting above where
# Latin reference letters on the same line actually bottom out. First
# nudged down by 2px (522/570); user feedback after live testing that build
# said 2px overshot ("трошечки нижче, ніж має бути") -- settled on 1px
# (521/569).
BASELINE_BY_ROW_Y0 = {
    480: 521,  # row y=(480,528) -- I_upper, Yi_upper
    528: 569,  # row y=(528,576) -- Ye_upper, ye_lower, Ghe_upper, i_lower, yi_lower, ghe_lower
}

# Horizontal side bearing added after each glyph's own ink width when
# writing its advance Width into the metrics table (see
# build_font1_ukrainian.py). Reference gaps measured directly in this atlas:
# wide, already-correct Cyrillic capitals sit ~8px apart (U+0411 Б to U+0412
# В: 8px; U+0413 Г to U+0414 Д: 8px), but narrow Latin letters sit almost
# flush (U+0069 i to U+006A j: 1px; U+006C l to U+006D m: 1px).
#
# IMPORTANT (8th real bug, found in real gameplay testing on a longer word):
# a flat +6 was tuned looking at the wider glyphs in this set (Ye/Ghe, ~28px
# ink) and never re-checked against the narrowest one (i_lower, ~18px ink,
# closer in spirit to Latin "i"/"l" than to a full-width Cyrillic capital).
# +6 on an 18px-wide glyph is a much bigger relative gap than +6 on a 28px
# one, and it showed up as visibly too much whitespace after "і" in a real
# word ("Дітріх" rendered with an odd gap, almost reading as two words).
# Lowered to +3 -- still a believable gap for the wider glyphs, much closer
# to the narrow-Latin reference for the narrow ones.
SIDE_BEARING = 3

# DXT5 compresses in fixed 4x4-pixel blocks (see build_font1_dds.py, which
# only re-encodes the blocks a rect touches). expand_to_block() rounds a
# rect outward to the enclosing block boundary.
BLOCK = 4


def expand_to_block(x0, y0, x1, y1):
    return (x0 // BLOCK * BLOCK, y0 // BLOCK * BLOCK,
            -(-x1 // BLOCK) * BLOCK, -(-y1 // BLOCK) * BLOCK)


def clear_rect_for(name, x0, y0, x1, y1):
    """The actual pixel region to clear-then-repaint for a TARGETS entry --
    CLEAR_X_OVERRIDE's full-gap horizontal bounds (see its comment) expanded
    to the DXT5 block grid. build_font1_dds.py imports this so its block
    splice range always matches exactly what got cleared/repainted here."""
    cx0, cx1 = CLEAR_X_OVERRIDE.get(name, (x0, x1))
    return expand_to_block(cx0, y0, cx1, y1)


# IMPORTANT (14th real bug, found by the user directly in the glyph viewer):
# "Ґ" (Ghe_upper, row y=480-528... no: y=528-576) visibly intersects a "dirty"
# smudge at its bottom edge. Root cause: donor rows in this atlas sit
# back-to-back with ZERO gap (see TARGETS' 6th-bug comment above), and
# directly below Ghe_upper's row, at the very first pixel row of the next
# donor row (y=576), sits the diacritic stroke of Latin Small Letter Z With
# Acute ("z_acute", U+017A) -- confirmed via direct pixel scan (opaque ink
# starting at y=576 with no gap at all under Ghe_upper's own column x=64-103).
# Same underlying mechanism as the known, deferred bug #12 (GPU bilinear/mip
# filtering samples a fraction of a pixel past a glyph's declared UV rect),
# but here there's no room to dodge it by nibbling or repositioning: Height
# isn't stored per-glyph (always the font's own `height`, see the .FNT format
# section in README.md), so Ghe_upper's Y can't be nudged without instead
# sampling into a DIFFERENT neighboring row.
#
# Fix: since neither "ź" nor its uppercase pair "Ż" are Ukrainian letters or
# referenced anywhere in translations/ (checked directly), there is nothing
# lost by erasing the offending glyph outright -- simpler and more robust
# than chasing the bleed via UV-rect tricks. Its mapping-table entry and
# metrics are left untouched (still "supported", just blank) since nothing
# in this release's text ever renders it.
KILL_RECTS = [
    ("z_acute", (63, 576, 87, 624)),  # 'ź' U+017A -- see comment above
]


def kill_rect_for(name, x0, y0, x1, y1):
    """Same block-alignment as clear_rect_for, for KILL_RECTS entries that
    get erased outright rather than cleared-then-repainted."""
    return expand_to_block(x0, y0, x1, y1)


def available_w_for(name, x0, x1):
    """The REAL horizontal room available before touching a genuine neighbor
    glyph, per CLEAR_X_OVERRIDE -- NOT the original TARGETS rect width.

    IMPORTANT (16th real bug, found by the user comparing our rendered "Є"
    against a correctly-drawn one): "Є" (Ye_upper) looked visibly squished
    and narrow. Root cause: the anti-overflow clamp in compute_all_metrics()
    used TARGETS' own rect_w (30px, inherited from the Polish donor "Ę"
    glyph's cell) as the width ceiling -- but Franklin Gothic's natural,
    correctly-proportioned "Є" at the calibrated cap-height scale is 36px
    wide, so the clamp squished it down to 28px (a ~22% width reduction),
    visibly distorting the backward-C-plus-bar shape into something
    narrower than it should be. The donor cell was simply too narrow for
    this particular letterform -- but the REAL constraint isn't that cell,
    it's where the ACTUAL next neighbor's own ink starts, which
    CLEAR_X_OVERRIDE already tracks separately for the bleed fix (12th
    bug). Using that wider, real bound here (and widening the Ye_upper/
    ye_lower split itself from 32/35 to 36/36 -- both entirely OUR OWN
    glyphs, safe to move together) cuts the squish down to just 36->34px
    (~5%), much closer to Franklin Gothic's natural proportions."""
    cx0, cx1 = CLEAR_X_OVERRIDE.get(name, (x0, x1))
    return cx1 - cx0


def _measure_scale() -> float:
    f = ImageFont.truetype(str(FRANKLIN), RENDER_SIZE)
    tmp = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    bb = d.textbbox((100, 100), "O", font=f, stroke_width=RENDER_STROKE)
    rendered_cap_height = bb[3] - bb[1]
    return CAP_HEIGHT_TARGET / rendered_cap_height


def render_char(ch: str, scale: float) -> Image.Image:
    f = ImageFont.truetype(str(FRANKLIN), RENDER_SIZE)
    tmp = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    bb = d.textbbox((150, 150), ch, font=f, stroke_width=RENDER_STROKE)
    d.text((150, 150), ch, font=f, fill=FILL_COLOR,
            stroke_width=RENDER_STROKE, stroke_fill=STROKE_COLOR)
    glyph = tmp.crop(bb)
    new_w = max(1, round(glyph.width * scale))
    new_h = max(1, round(glyph.height * scale))
    return glyph.resize((new_w, new_h), Image.LANCZOS)


def compute_all_metrics(scale: float) -> list[dict]:
    """Computes, for every TARGETS entry, exactly what gets painted and where
    -- WITHOUT touching the atlas image. Single source of truth shared by
    main() (which paints the PNG) and build_font1_ukrainian.py (which needs
    the same numbers to write a correct metrics-table Width for each glyph,
    instead of leaving the inherited Polish donor's width in place)."""
    results = []
    for ch, name, (x0, y0, x1, y1) in TARGETS:
        rect_w, rect_h = x1 - x0, y1 - y0
        avail_w = available_w_for(name, x0, x1)
        baseline = BASELINE_BY_ROW_Y0[y0]
        # Available vertical room ABOVE the baseline, inside this row, before
        # painting would spill into whatever unrelated glyph sits in the row
        # above (rows are back-to-back with zero gap -- see TARGETS comment).
        max_h_above_baseline = baseline - y0

        glyph_scaled = render_char(ch, scale)
        new_w, new_h = glyph_scaled.size
        # Safety clamp: the globally-calibrated scale is correct for height
        # consistency, but a handful of glyphs (e.g. the open "Ye" curve,
        # naturally wide relative to its height in Franklin Gothic) don't fit
        # their rect's width at that height. Never let a glyph overflow its
        # rect's pixel budget -- that would bleed into the neighboring glyph
        # in the shared texture.
        #
        # IMPORTANT (fixed after real in-game testing, 4th pass): the first
        # version of this clamp shrunk BOTH dimensions uniformly whenever
        # width overflowed, which defeated the whole point of the cap-height
        # calibration -- "Ye_upper" (Є) came out only ~30px tall instead of
        # the intended 39px cap-height, landing close to "ye_lower" (є)'s
        # x-height and making upper/lowercase nearly indistinguishable by
        # size. Squish WIDTH ONLY when only width overflows, so the
        # calibrated height (the more visually important, load-bearing
        # dimension for matching neighboring text) is preserved exactly.
        if new_w > avail_w - 2 and new_h <= rect_h - 2:
            new_w = max(1, avail_w - 2)
            glyph_scaled = glyph_scaled.resize((new_w, new_h), Image.LANCZOS)
        elif new_h > rect_h - 2:
            shrink = min((avail_w - 2) / new_w, (rect_h - 2) / new_h)
            new_w = max(1, round(new_w * shrink))
            new_h = max(1, round(new_h * shrink))
            glyph_scaled = glyph_scaled.resize((new_w, new_h), Image.LANCZOS)

        # IMPORTANT (7th real bug, found while re-verifying after decoding the
        # metrics table): the clamp above only checked the glyph against the
        # rect's TOTAL height, not against how much of that height is left
        # ABOVE the baseline once the glyph is placed bottom-up at
        # `baseline - new_h`. Letters with marks that rise above plain
        # cap-height -- "Ї" (diaeresis dots) and "Ґ" (upturned hook) -- render
        # taller than the calibrated 39px cap-height, overflowed upward past
        # the row's top edge, and would have painted into the unrelated
        # glyph living in the row above. Real accented capitals (compare the
        # already-correct "Й" elsewhere in this atlas) solve this by drawing
        # the BASE letter slightly shorter than plain cap-height, leaving
        # headroom for the mark, rather than letting the mark push the total
        # height past the row -- so shrinking a mark-bearing glyph to fit is
        # the visually-correct behavior, not just a safety fallback.
        if new_h > max_h_above_baseline:
            shrink = max_h_above_baseline / new_h
            new_w = max(1, round(new_w * shrink))
            new_h = max_h_above_baseline
            glyph_scaled = glyph_scaled.resize((new_w, new_h), Image.LANCZOS)

        # Left-aligned (1px margin) rather than centered: measured donor
        # letters in these rows (e.g. "n-acute", "S-acute") fill ~96-100% of
        # their cell width with only ~1px of margin -- centering a narrower
        # glyph (like our thin "i") inside a cell sized for a wider donor
        # letter left big, visually "floating" gaps on both sides. Left
        # alignment matches how the existing glyphs actually sit and puts
        # all the leftover space where inter-letter spacing normally goes
        # (after the glyph), not split awkwardly on both sides.
        px = x0 + 1
        py = baseline - new_h

        # Declared advance width for the metrics table: the painted glyph's
        # own width plus a believable side bearing, but never wider than the
        # real cleared/repainted area (avail_w - 1, see available_w_for) --
        # past that boundary sits whatever glyph actually lives next in this
        # row, and the metrics table must not claim pixels we didn't
        # clear/repaint.
        declared_width = min(new_w + SIDE_BEARING, avail_w - 1)

        # IMPORTANT (still investigating the "halo" bug after the 10th fix):
        # preserving untouched DXT5 blocks (build_font1_dds.py) stops us from
        # corrupting a NEIGHBORING glyph, but it doesn't stop contamination
        # INSIDE our own rect: our own painted ink rarely fills the whole
        # declared rect (e.g. narrow "i" ink vs its wider donor cell), so a
        # block straddling the true rect edge can still mix [a couple of
        # untouched original-donor-edge pixels just outside x0/x1] with [our
        # freshly cleared/painted pixels just inside] -- and that block then
        # gets re-encoded and IS kept (it's inside our block-expanded splice
        # range), quietly shifting those few original neighbor-edge pixels'
        # color. Clearing to the full block-aligned rect up front (verified
        # safe: sampled every padding pixel this adds across all 8 targets,
        # only 4px at ~alpha=2 -- i.e. already near-invisible -- get zeroed)
        # means every block we ever touch is 100% ours, never a mix.
        clear_rect = clear_rect_for(name, x0, y0, x1, y1)

        results.append({
            "ch": ch, "name": name, "rect": (x0, y0, x1, y1),
            "clear_rect": clear_rect,
            "rect_w": rect_w, "rect_h": rect_h,
            "image": glyph_scaled, "new_w": new_w, "new_h": new_h,
            "px": px, "py": py, "baseline": baseline,
            "declared_width": declared_width,
        })
    return results


def main():
    scale = _measure_scale()
    print(f"global scale factor (cap-height calibrated): {scale:.4f}")

    atlas = Image.open(ATLAS_SRC).convert("RGBA")
    patched = atlas.copy()
    for m in compute_all_metrics(scale):
        cx0, cy0, cx1, cy1 = m["clear_rect"]
        clear = Image.new("RGBA", (cx1 - cx0, cy1 - cy0), (0, 0, 0, 0))
        patched.paste(clear, (cx0, cy0))
        patched.alpha_composite(m["image"], (m["px"], m["py"]))
        print(f"{m['name']}: rect={m['rect_w']}x{m['rect_h']} glyph={m['new_w']}x{m['new_h']} "
              f"pos=({m['px']},{m['py']}) baseline={m['baseline']} declared_width={m['declared_width']}")

    for name, (x0, y0, x1, y1) in KILL_RECTS:
        kx0, ky0, kx1, ky1 = kill_rect_for(name, x0, y0, x1, y1)
        clear = Image.new("RGBA", (kx1 - kx0, ky1 - ky0), (0, 0, 0, 0))
        patched.paste(clear, (kx0, ky0))
        print(f"{name}: erased {kx1 - kx0}x{ky1 - ky0} at ({kx0},{ky0}) "
              f"(unused donor glyph removed, see 14th-bug note above)")

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    patched.save(OUT_PNG)
    print(f"saved {OUT_PNG} {patched.size}")


if __name__ == "__main__":
    main()
