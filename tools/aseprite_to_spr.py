#!/usr/bin/env python3
"""Convert an Aseprite animation into MDBASIC .spr sprite-data file(s).

Each frame of the source animation becomes one C64 hardware sprite image; the
frames are written as a .spr file ready to LOAD into an MDBASIC program and
animate with PLAY SPRITE. Requires only Python 3 (standard library, no Pillow
or the Aseprite CLI): the .aseprite file is parsed directly. Every visible
layer is composited per frame, so exporting a PNG first is unnecessary.

THE .spr FORMAT
    MDBASIC sprites are standard C64 hardware sprites, 24x21 pixels, stored as
    3 bytes per row for 21 rows (63 bytes) in 64-byte blocks. A .spr file is a
    PRG-style binary: a 2-byte little-endian load address followed by
    consecutive 64-byte sprite blocks (mirroring the bird.spr example on the
    MDBASIC disk). MDBASIC's sprite "data index" is address / 64 within the
    active 16K VIC-II bank, so the load address determines which index the
    images occupy.

COLOUR MODES
    hires (default) - 1 bit per pixel, 24x21, single colour. A source pixel is
        "on" wherever the artwork is opaque, i.e. the result is a silhouette.
    multicolor      - 2 bits per pixel, 12x21 (double-wide pixels), up to 3
        colours plus transparent. The three colours are picked automatically
        from the C64 palette by frequency and reported so you can set the
        matching SPRITE colour and SPRCOL values.

SPLITTING LARGER ARTWORK
    One hardware sprite covers only 24x21 pixels. --split CxR tiles the artwork
    across a C-by-R grid of sprites at native resolution (C*24 by R*21 pixels),
    writing one .spr per grid cell (each holding every animation frame). The
    sampling window is positioned over the union bounding box of all frames to
    avoid clipping; if the artwork is larger than the grid, the number of
    clipped pixels is reported so you can widen the grid. Split files are named
    OUTPUT_rRcC.spr and get consecutive load addresses.

LAYERS
    Layers named in --skip-layers (default "BG") are ignored, along with hidden
    or "background"-flagged layers. This drops the character-template backdrop
    that would otherwise fill the whole frame.

USAGE
    aseprite_to_spr.py INPUT.aseprite OUTPUT.spr [--multicolor] [--split 2x2]
        [--load-addr 0x2000 | --index N [--bank B]] [--threshold 0.5]
        [--scale fit|native] [--skip-layers BG] [--invert] [--preview]

    The first sprite's location is given either as an absolute --load-addr or
    as a --index (0-255) within a --bank (0-3); they relate by
    address = index*64 + bank*16384.

EXAMPLES
    # One sprite per frame, scaled to fit 24x21, loading at index 128 ($2000):
    aseprite_to_spr.py run.aseprite run.spr

    # Full-resolution 2x2 tiling (four files) into clean upper RAM (bank 3):
    aseprite_to_spr.py run.aseprite run.spr --split 2x2 --index 16 --bank 3

    # Multicolor, previewing each sprite as ASCII art on stderr:
    aseprite_to_spr.py run.aseprite run.spr --multicolor --preview

THE RESULT IN MDBASIC
    A file reported at "$2000 (indexes 128-135)" holds 8 frames at data
    indexes 128-135:
        LOAD"RUN.SPR",8,1          : REM binary-load to the stored address
        SPRITE 0,1,7,0,128         : REM sprite 0 on, colour 7, data index 128
        PLAY SPRITE 0,128,135,5    : REM cycle frames 128-135, 5 jiffies each
"""
import argparse
import math
import struct
import sys
import zlib

SPR_PX_W, SPR_PX_H = 24, 21    # C64 hardware sprite dimensions (pixels)
BLOCK = 64                     # bytes per sprite data block (63 used + 1 pad)
BANK_SIZE = 16384              # bytes per VIC-II 16K video bank


def addr_to_index(addr):
    """Return (bank, data_index) for an absolute address. A data index is
    bank-relative (0-255), matching the sprite pointer byte:
    address = index*64 + bank*16384."""
    return addr // BANK_SIZE, (addr % BANK_SIZE) // BLOCK

# Pepto PAL palette for the 16 C64 colours (index, name, r, g, b).
C64_PALETTE = [
    (0, "black", 0, 0, 0), (1, "white", 255, 255, 255),
    (2, "red", 104, 55, 43), (3, "cyan", 112, 164, 178),
    (4, "purple", 111, 61, 134), (5, "green", 88, 141, 67),
    (6, "blue", 53, 40, 121), (7, "yellow", 184, 199, 111),
    (8, "orange", 111, 79, 37), (9, "brown", 67, 57, 0),
    (10, "light red", 154, 103, 89), (11, "dark grey", 68, 68, 68),
    (12, "grey", 108, 108, 108), (13, "light green", 154, 210, 132),
    (14, "light blue", 108, 94, 181), (15, "light grey", 149, 149, 149),
]


# --------------------------------------------------------------------------- #
# Aseprite parsing
# --------------------------------------------------------------------------- #
def parse_aseprite(path, skip_layers=()):
    """Return (width, height, [frame, ...]) where each frame is a flat list of
    (r, g, b, a) tuples of length width*height, top-to-bottom, left-to-right.

    Layers whose name matches skip_layers (case-insensitive) are ignored, as
    are layers with the "background" flag or that are not visible."""
    d = open(path, "rb").read()
    _fsize, magic, nframes, w, h, depth = struct.unpack("<IHHHHH", d[0:14])
    if magic != 0xA5E0:
        raise ValueError("not an Aseprite file (bad magic)")
    if depth != 32:
        raise ValueError("only 32-bit RGBA Aseprite files are supported")

    skip = {s.lower() for s in skip_layers}
    layer_hidden = {}
    layer_idx = 0

    frames = []
    pos = 128
    for _ in range(nframes):
        (fbytes, fmagic, old_chunks, _dur, _r0, new_chunks) = struct.unpack(
            "<IHHHHI", d[pos:pos + 16]
        )
        if fmagic != 0xF1FA:
            raise ValueError("bad frame magic")
        nchunks = new_chunks if new_chunks != 0 else old_chunks
        cpos = pos + 16

        canvas = [(0, 0, 0, 0)] * (w * h)
        for _c in range(nchunks):
            (csize, ctype) = struct.unpack("<IH", d[cpos:cpos + 6])
            cdata = d[cpos + 6:cpos + csize]
            if ctype == 0x2004:  # layer chunk
                flags, _ltype = struct.unpack("<HH", cdata[0:4])
                nlen = struct.unpack("<H", cdata[16:18])[0]
                name = cdata[18:18 + nlen].decode("utf-8", "replace")
                hidden = (not flags & 1) or bool(flags & 8) or name.lower() in skip
                layer_hidden[layer_idx] = hidden
                layer_idx += 1
            elif ctype == 0x2005:  # cel chunk
                layer, cx, cy, _op, cel_type = struct.unpack("<HhhBH", cdata[0:9])
                if not layer_hidden.get(layer) and cel_type in (0, 2):
                    cw, ch = struct.unpack("<HH", cdata[16:20])
                    raw = cdata[20:]
                    if cel_type == 2:
                        raw = zlib.decompress(raw)
                    _composite(canvas, w, h, raw, cw, ch, cx, cy)
            cpos += csize
        frames.append(canvas)
        pos += fbytes
    return w, h, frames


def _composite(canvas, w, h, raw, cw, ch, ox, oy):
    """Alpha-over a raw RGBA cel (cw x ch at offset ox,oy) onto canvas."""
    for y in range(ch):
        ty = oy + y
        if ty < 0 or ty >= h:
            continue
        for x in range(cw):
            tx = ox + x
            if tx < 0 or tx >= w:
                continue
            i = (y * cw + x) * 4
            sr, sg, sb, sa = raw[i], raw[i + 1], raw[i + 2], raw[i + 3]
            if sa == 0:
                continue
            di = ty * w + tx
            dr, dg, db, da = canvas[di]
            a = sa / 255.0
            canvas[di] = (
                int(sr * a + dr * (1 - a)),
                int(sg * a + dg * (1 - a)),
                int(sb * a + db * (1 - a)),
                max(sa, da),
            )


# --------------------------------------------------------------------------- #
# Sampling & colour helpers
# --------------------------------------------------------------------------- #
def sample_region(canvas, w, h, x0, y0, x1, y1):
    """Sample the source rectangle [x0,x1) x [y0,y1). Returns (coverage,
    avg_rgb) where coverage is the fraction of the region that is opaque
    (pixels off-canvas count as transparent) and avg_rgb averages the opaque
    pixels (or None when nothing is opaque)."""
    ix0, iy0 = int(math.floor(x0)), int(math.floor(y0))
    ix1, iy1 = int(math.ceil(x1)), int(math.ceil(y1))
    total = max(1, (ix1 - ix0) * (iy1 - iy0))
    covered = 0
    rs = gs = bs = 0
    for py in range(iy0, iy1):
        if py < 0 or py >= h:
            continue
        base = py * w
        for px in range(ix0, ix1):
            if px < 0 or px >= w:
                continue
            r, g, b, a = canvas[base + px]
            if a > 127:
                covered += 1
                rs += r
                gs += g
                bs += b
    if covered == 0:
        return 0.0, None
    return covered / total, (rs / covered, gs / covered, bs / covered)


def nearest_c64(rgb):
    """Return the (index, name, r, g, b) palette entry nearest to rgb."""
    r, g, b = rgb
    best = None
    best_d = None
    for entry in C64_PALETTE:
        _i, _n, pr, pg, pb = entry
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if best_d is None or d < best_d:
            best_d, best = d, entry
    return best


def choose_mc_palette(frames, w, h):
    """Pick the three most-used C64 colours across all opaque pixels. Returns a
    list of up to three palette entries, most frequent first."""
    counts = {}
    for canvas in frames:
        for r, g, b, a in canvas:
            if a > 127:
                entry = nearest_c64((r, g, b))
                counts[entry] = counts.get(entry, 0) + 1
    ordered = sorted(counts, key=lambda e: counts[e], reverse=True)
    return ordered[:3]


# --------------------------------------------------------------------------- #
# Rasterisation
# --------------------------------------------------------------------------- #
def raster_cell(canvas, w, h, rect, multicolor, threshold, invert, mc_palette):
    """Rasterise one sprite from the source rectangle rect=(x0,y0,x1,y1).
    Returns 21 rows; each row is a list of ints (0/1 for hires, 0-3 for
    multicolor)."""
    x0, y0, x1, y1 = rect
    lx = 12 if multicolor else 24
    ly = 21
    rows = []
    for j in range(ly):
        sy0 = y0 + j * (y1 - y0) / ly
        sy1 = y0 + (j + 1) * (y1 - y0) / ly
        row = []
        for i in range(lx):
            sx0 = x0 + i * (x1 - x0) / lx
            sx1 = x0 + (i + 1) * (x1 - x0) / lx
            cov, avg = sample_region(canvas, w, h, sx0, sy0, sx1, sy1)
            if not multicolor:
                on = cov >= threshold
                row.append(int((not on) if invert else on))
            else:
                if cov < threshold or avg is None or not mc_palette:
                    row.append(0)
                else:
                    # nearest of the chosen palette colours -> bit pair.
                    # freq rank 0 -> 10 (sprite colour), 1 -> 01 (sc1),
                    # 2 -> 11 (sc2).
                    values = [2, 1, 3]
                    best = None
                    best_d = None
                    for k, entry in enumerate(mc_palette):
                        _i, _n, pr, pg, pb = entry
                        d = ((avg[0] - pr) ** 2 + (avg[1] - pg) ** 2
                             + (avg[2] - pb) ** 2)
                        if best_d is None or d < best_d:
                            best_d, best = d, values[k]
                    row.append(best)
        rows.append(row)
    return rows


def sprite_bytes(rows, multicolor):
    """Pack 21 rows into a 64-byte C64 sprite block."""
    out = bytearray()
    for row in rows:
        if not multicolor:
            for byte_idx in range(3):
                b = 0
                for bit in range(8):
                    if row[byte_idx * 8 + bit]:
                        b |= 1 << (7 - bit)
                out.append(b)
        else:
            for byte_idx in range(3):
                b = 0
                for pair in range(4):
                    v = row[byte_idx * 4 + pair] & 3
                    b |= v << (6 - pair * 2)
                out.append(b)
    out.append(0)  # pad to a 64-byte block
    return bytes(out)


# --------------------------------------------------------------------------- #
# Window placement (native tiling)
# --------------------------------------------------------------------------- #
def place_window(frames, w, h, gw, gh):
    """Choose the top-left (wx, wy) of a gw x gh window that captures the most
    opaque pixels across all frames. Returns (wx, wy, total, captured)."""
    # weight[y][x] = number of frames in which the pixel is opaque.
    weight = [[0] * w for _ in range(h)]
    for canvas in frames:
        for y in range(h):
            base = y * w
            row = weight[y]
            for x in range(w):
                if canvas[base + x][3] > 127:
                    row[x] += 1

    # Summed-area table for O(1) window sums.
    sat = [[0] * (w + 1) for _ in range(h + 1)]
    for y in range(h):
        for x in range(w):
            sat[y + 1][x + 1] = (weight[y][x] + sat[y][x + 1]
                                 + sat[y + 1][x] - sat[y][x])

    def rectsum(a, b, c, d):  # [a,c) x [b,d), clamped to canvas
        a, b = max(0, a), max(0, b)
        c, d = min(w, c), min(h, d)
        if a >= c or b >= d:
            return 0
        return sat[d][c] - sat[b][c] - sat[d][a] + sat[b][a]

    total = rectsum(0, 0, w, h)

    def axis_positions(size, span):
        if size >= span:
            return [(span - size) // 2]      # window covers the whole axis
        return list(range(0, span - size + 1))

    # Centroid for tie-breaking toward a centred window.
    sx = sy = sw = 0
    for y in range(h):
        for x in range(w):
            ww = weight[y][x]
            sx += x * ww
            sy += y * ww
            sw += ww
    cx = sx / sw if sw else w / 2
    cy = sy / sw if sw else h / 2

    best = None
    for wy in axis_positions(gh, h):
        for wx in axis_positions(gw, w):
            captured = rectsum(wx, wy, wx + gw, wy + gh)
            centre_d = (wx + gw / 2 - cx) ** 2 + (wy + gh / 2 - cy) ** 2
            key = (-captured, centre_d)
            if best is None or key < best[0]:
                best = (key, wx, wy, captured)
    _key, wx, wy, captured = best
    return wx, wy, total, captured


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def split_output_name(output, r, c):
    if output.lower().endswith(".spr"):
        stem = output[:-4]
        return f"{stem}_r{r}c{c}.spr"
    return f"{output}_r{r}c{c}.spr"


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--multicolor", "--multi", action="store_true",
                    help="produce multicolor (12x21, 3-colour) sprites")
    ap.add_argument("--split", default="1x1", metavar="CxR",
                    help="tile artwork across a C-by-R grid of sprites "
                         "(e.g. 2x2). Default 1x1.")
    ap.add_argument("--scale", choices=("fit", "native"), default=None,
                    help="'fit' scales whole artwork into the grid (no "
                         "clipping); 'native' tiles at 1:1 and may clip. "
                         "Default: fit for 1x1, native when splitting.")
    where = ap.add_mutually_exclusive_group()
    where.add_argument("--load-addr", default=None,
                       help="absolute load address of the first sprite file "
                            "(default 0x2000 = bank 0, data index 128); split "
                            "files follow consecutively")
    where.add_argument("--index", type=lambda v: int(v, 0), default=None,
                       metavar="N",
                       help="data index (0-255) for the first sprite, as an "
                            "alternative to --load-addr; combined with --bank "
                            "as address = index*64 + bank*16384")
    ap.add_argument("--bank", type=lambda v: int(v, 0), default=0,
                    choices=(0, 1, 2, 3),
                    help="VIC-II 16K bank (0-3) that --index is relative to "
                         "(default 0); ignored when --load-addr is given")
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="opacity coverage (0-1) needed to turn a pixel on")
    ap.add_argument("--invert", action="store_true",
                    help="invert the hires silhouette")
    ap.add_argument("--skip-layers", default="BG",
                    help="comma-separated layer names to ignore (default: BG)")
    ap.add_argument("--preview", action="store_true",
                    help="print an ASCII preview of every sprite to stderr")
    args = ap.parse_args(argv)

    try:
        cols, rows_ = (int(v) for v in args.split.lower().split("x"))
    except ValueError:
        ap.error("--split must look like CxR, e.g. 2x2")
    if cols < 1 or rows_ < 1:
        ap.error("--split dimensions must be >= 1")

    scale = args.scale or ("fit" if cols * rows_ == 1 else "native")
    if args.index is not None:
        if not 0 <= args.index <= 255:
            ap.error("--index must be 0-255")
        load_addr = args.index * BLOCK + args.bank * BANK_SIZE
    elif args.load_addr is not None:
        load_addr = int(args.load_addr, 0)
    else:
        load_addr = 0x2000
    skip = [s.strip() for s in args.skip_layers.split(",") if s.strip()]

    w, h, frames = parse_aseprite(args.input, skip_layers=skip)
    nframes = len(frames)
    gw, gh = cols * SPR_PX_W, rows_ * SPR_PX_H

    mc_palette = choose_mc_palette(frames, w, h) if args.multicolor else None

    # Decide the source window each grid cell samples from.
    if scale == "native":
        wx, wy, total, captured = place_window(frames, w, h, gw, gh)
        clipped = total - captured
        if clipped:
            print(f"WARNING: {clipped} of {total} opaque pixel-instances fall "
                  f"outside the {gw}x{gh} window at ({wx},{wy}); they will be "
                  f"clipped. Increase --split to cover more area.",
                  file=sys.stderr)
            for n, canvas in enumerate(frames):
                fc = sum(1 for y in range(h) for x in range(w)
                         if canvas[y * w + x][3] > 127
                         and not (wx <= x < wx + gw and wy <= y < wy + gh))
                if fc:
                    print(f"  frame {n}: {fc} pixels clipped", file=sys.stderr)
        else:
            print(f"No clipping: {gw}x{gh} window at ({wx},{wy}) contains all "
                  f"artwork.", file=sys.stderr)

        def cell_rect(r, c):
            return (wx + c * SPR_PX_W, wy + r * SPR_PX_H,
                    wx + (c + 1) * SPR_PX_W, wy + (r + 1) * SPR_PX_H)
    else:  # fit: map the whole canvas into the grid
        def cell_rect(r, c):
            return (c * w / cols, r * h / rows_,
                    (c + 1) * w / cols, (r + 1) * h / rows_)

    # Emit one .spr per grid cell, each holding all animation frames.
    file_idx = 0
    outputs = []
    for r in range(rows_):
        for c in range(cols):
            body = bytearray()
            preview_rows = []
            for n, canvas in enumerate(frames):
                cells = raster_cell(canvas, w, h, cell_rect(r, c),
                                    args.multicolor, args.threshold,
                                    args.invert, mc_palette)
                body += sprite_bytes(cells, args.multicolor)
                if args.preview:
                    preview_rows.append((n, cells))

            addr = load_addr + file_idx * nframes * BLOCK
            name = (args.output if cols * rows_ == 1
                    else split_output_name(args.output, r, c))
            with open(name, "wb") as f:
                f.write(struct.pack("<H", addr))
                f.write(bytes(body))
            outputs.append((name, r, c, addr))

            if args.preview:
                _bank, base_index = addr_to_index(addr)
                for n, cells in preview_rows:
                    print(f"--- {name} frame {n} "
                          f"(index {base_index + n}) ---", file=sys.stderr)
                    for row in cells:
                        if args.multicolor:
                            print("".join(" .+#@"[v + 1] * 2 for v in row),
                                  file=sys.stderr)
                        else:
                            print("".join("#" if v else "." for v in row),
                                  file=sys.stderr)
            file_idx += 1

    # Summary.
    mode = ("multicolor 12x21" if args.multicolor else "hires 24x21")
    print(f"{args.input}: {nframes} frames ({w}x{h}) -> {mode}, "
          f"{cols}x{rows_} grid, {scale} scale")
    for name, r, c, addr in outputs:
        bank, index = addr_to_index(addr)
        last = index + nframes - 1
        print(f"  {name}: row {r} col {c}, {nframes} frames @ ${addr:04X} "
              f"(bank {bank}, indexes {index}-{last})")
        if last > 255:
            print(f"    WARNING: index range exceeds 255 / crosses a bank "
                  f"boundary; the sprite pointer byte cannot reach these "
                  f"images.", file=sys.stderr)

    if args.multicolor and mc_palette:
        names = [e[1] for e in mc_palette]
        idx = [e[0] for e in mc_palette]
        print("Multicolor palette (set before displaying):")
        print(f"  SPRITE colour (bit 10) = {idx[0]} ({names[0]})")
        if len(mc_palette) > 1:
            sc1 = idx[1]
            sc2 = idx[2] if len(mc_palette) > 2 else idx[1]
            print(f"  SPRCOL {sc1},{sc2}   "
                  f":' sc1(01)={names[1]}"
                  + (f", sc2(11)={names[2]}" if len(mc_palette) > 2 else ""))


if __name__ == "__main__":
    main()
