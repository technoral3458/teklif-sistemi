"""Parametrik dilimleme: 3B katı model (STL/OBJ) → panel kesitleri → CNC için DXF.

Kullanım akışı:
    tris  = load_mesh(data, filename)
    info  = mesh_info(tris)
    res   = build_panels(tris, axis='z', thickness=18, gap=0, scale=1.0)
    dxf   = export_dxf(res, sheet_w=2100, sheet_h=2800)
    svg   = export_svg(res)

Harici bağımlılık yok (DXF çıktısı için sadece ezdxf — zaten kurulu).
"""

import io
import math
import struct
import zipfile
from bisect import bisect_left, bisect_right

# Eksen → 2B izdüşüm indeksleri (dilimleme ekseni atılır)
_AXIS_IDX = {"x": 0, "y": 1, "z": 2}
_PROJ = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}

MAX_TRIANGLES = 900_000
MAX_PANELS = 400


# ══════════════════════════════════════════════════════════════════════════
#  1) Mesh okuma
# ══════════════════════════════════════════════════════════════════════════

def _load_stl_binary(data: bytes):
    if len(data) < 84:
        raise ValueError("STL dosyası çok kısa.")
    n = struct.unpack_from("<I", data, 80)[0]
    if 84 + n * 50 != len(data):
        raise ValueError("binary değil")
    if n > MAX_TRIANGLES:
        raise ValueError(f"Model çok büyük ({n:,} üçgen). En fazla {MAX_TRIANGLES:,} desteklenir.")
    tris = []
    add = tris.append
    up = struct.unpack_from
    off = 84
    for _ in range(n):
        v = up("<12f", data, off)
        add(((v[3], v[4], v[5]), (v[6], v[7], v[8]), (v[9], v[10], v[11])))
        off += 50
    return tris


def _load_stl_ascii(text: str):
    tris = []
    cur = []
    for line in text.splitlines():
        s = line.strip()
        if s[:6] == "vertex" or s[:6] == "VERTEX":
            p = s.split()
            if len(p) >= 4:
                cur.append((float(p[1]), float(p[2]), float(p[3])))
                if len(cur) == 3:
                    tris.append((cur[0], cur[1], cur[2]))
                    cur = []
        elif s[:8] == "endfacet":
            cur = []
        if len(tris) > MAX_TRIANGLES:
            raise ValueError(f"Model çok büyük. En fazla {MAX_TRIANGLES:,} üçgen desteklenir.")
    if not tris:
        raise ValueError("ASCII STL içinde üçgen bulunamadı.")
    return tris


def _load_obj(text: str):
    verts = []
    tris = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s[0] == "#":
            continue
        if s[0] == "v" and s[1:2] in (" ", "\t"):
            p = s.split()
            if len(p) >= 4:
                verts.append((float(p[1]), float(p[2]), float(p[3])))
        elif s[0] == "f" and s[1:2] in (" ", "\t"):
            idx = []
            for tok in s.split()[1:]:
                raw = tok.split("/")[0]
                if not raw:
                    continue
                i = int(raw)
                idx.append(verts[i - 1] if i > 0 else verts[i])
            # fan triangulation
            for k in range(1, len(idx) - 1):
                tris.append((idx[0], idx[k], idx[k + 1]))
            if len(tris) > MAX_TRIANGLES:
                raise ValueError(f"Model çok büyük. En fazla {MAX_TRIANGLES:,} üçgen desteklenir.")
    if not tris:
        raise ValueError("OBJ içinde yüzey (f) bulunamadı.")
    return tris


def load_mesh(data: bytes, filename: str = ""):
    """Dosya içeriğinden üçgen listesi üretir. Desteklenen: STL (binary/ASCII), OBJ."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()

    if ext == "obj":
        return _load_obj(data.decode("utf-8", "ignore"))

    if ext == "stl" or not ext:
        # Binary mi ASCII mi?
        try:
            return _load_stl_binary(data)
        except ValueError as e:
            if "çok büyük" in str(e):
                raise
        try:
            return _load_stl_ascii(data.decode("utf-8", "ignore"))
        except ValueError:
            raise ValueError(
                "STL dosyası okunamadı. Dosya bozuk olabilir veya desteklenmeyen bir biçimde."
            )

    raise ValueError(
        f"'.{ext}' uzantısı desteklenmiyor. CAD programınızdan STL veya OBJ olarak dışa aktarın."
    )


def mesh_info(tris):
    """Model sınırlarını ve üçgen sayısını döndürür."""
    xs_min = ys_min = zs_min = float("inf")
    xs_max = ys_max = zs_max = float("-inf")
    for t in tris:
        for v in t:
            x, y, z = v
            if x < xs_min: xs_min = x
            if x > xs_max: xs_max = x
            if y < ys_min: ys_min = y
            if y > ys_max: ys_max = y
            if z < zs_min: zs_min = z
            if z > zs_max: zs_max = z
    return {
        "tri_count": len(tris),
        "min": (xs_min, ys_min, zs_min),
        "max": (xs_max, ys_max, zs_max),
        "size": (xs_max - xs_min, ys_max - ys_min, zs_max - zs_min),
    }


# ══════════════════════════════════════════════════════════════════════════
#  2) Dilimleme
# ══════════════════════════════════════════════════════════════════════════

class _Welder:
    """Kayan nokta hatalarına dayanıklı nokta birleştirici (spatial hash)."""

    __slots__ = ("tol", "cell", "buckets", "pts")

    def __init__(self, tol):
        self.tol = tol
        self.cell = tol * 4.0
        self.buckets = {}
        self.pts = []

    def add(self, x, y):
        c = self.cell
        cx, cy = int(math.floor(x / c)), int(math.floor(y / c))
        tol2 = self.tol * self.tol
        b = self.buckets
        pts = self.pts
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                lst = b.get((cx + dx, cy + dy))
                if not lst:
                    continue
                for pid in lst:
                    px, py = pts[pid]
                    if (px - x) ** 2 + (py - y) ** 2 <= tol2:
                        return pid
        pid = len(pts)
        pts.append((x, y))
        b.setdefault((cx, cy), []).append(pid)
        return pid


def _chain_loops(segments, tol):
    """(p1,p2) segment listesini kapalı konturlara (loop) zincirler."""
    w = _Welder(tol)
    edges = []
    for (x1, y1), (x2, y2) in segments:
        a = w.add(x1, y1)
        b = w.add(x2, y2)
        if a != b:
            edges.append((a, b))
    if not edges:
        return [], 0

    adj = {}
    for i, (a, b) in enumerate(edges):
        adj.setdefault(a, []).append(i)
        adj.setdefault(b, []).append(i)

    used = bytearray(len(edges))
    pts = w.pts
    loops = []
    open_count = 0

    for start_edge in range(len(edges)):
        if used[start_edge]:
            continue
        used[start_edge] = 1
        a, b = edges[start_edge]
        chain = [a, b]
        cur = b
        closed = False
        while True:
            nxt = -1
            for ei in adj.get(cur, ()):
                if used[ei]:
                    continue
                p, q = edges[ei]
                other = q if p == cur else p
                used[ei] = 1
                nxt = other
                break
            if nxt < 0:
                break
            if nxt == chain[0]:
                closed = True
                break
            chain.append(nxt)
            cur = nxt

        if len(chain) < 3:
            continue
        if not closed:
            open_count += 1
        loops.append([pts[i] for i in chain])

    return loops, open_count


def _tri_plane_segment(tri, ai, plane, pu, pv):
    """Üçgen–düzlem kesişimi → 2B segment (yoksa None)."""
    d0 = tri[0][ai] - plane
    d1 = tri[1][ai] - plane
    d2 = tri[2][ai] - plane
    if d0 == 0.0: d0 = 1e-12
    if d1 == 0.0: d1 = 1e-12
    if d2 == 0.0: d2 = 1e-12

    out = []
    ds = (d0, d1, d2)
    for i in range(3):
        j = (i + 1) % 3
        a, b = ds[i], ds[j]
        if (a > 0.0) != (b > 0.0):
            t = a / (a - b)
            va, vb = tri[i], tri[j]
            out.append((va[pu] + t * (vb[pu] - va[pu]),
                        va[pv] + t * (vb[pv] - va[pv])))
            if len(out) == 2:
                break
    return out if len(out) == 2 else None


def _simplify(pts, tol):
    """Douglas-Peucker ile nokta sayısını azaltır."""
    if tol <= 0 or len(pts) < 4:
        return pts
    n = len(pts)
    keep = bytearray(n)
    keep[0] = keep[n - 1] = 1
    stack = [(0, n - 1)]
    tol2 = tol * tol
    while stack:
        i0, i1 = stack.pop()
        if i1 <= i0 + 1:
            continue
        x0, y0 = pts[i0]
        x1, y1 = pts[i1]
        dx, dy = x1 - x0, y1 - y0
        den = dx * dx + dy * dy
        best_d, best_i = -1.0, -1
        for k in range(i0 + 1, i1):
            px, py = pts[k]
            if den <= 0.0:
                d = (px - x0) ** 2 + (py - y0) ** 2
            else:
                t = ((px - x0) * dx + (py - y0) * dy) / den
                t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
                d = (px - (x0 + t * dx)) ** 2 + (py - (y0 + t * dy)) ** 2
            if d > best_d:
                best_d, best_i = d, k
        if best_d > tol2:
            keep[best_i] = 1
            stack.append((i0, best_i))
            stack.append((best_i, i1))
    return [pts[i] for i in range(n) if keep[i]]


def plan_positions(amin, amax, thickness, gap):
    """Panel merkez konumlarını hesaplar. Panel i: [s+i*pitch, s+i*pitch+thickness]."""
    span = amax - amin
    pitch = thickness + gap
    if pitch <= 0:
        raise ValueError("Panel kalınlığı sıfırdan büyük olmalı.")
    if span < thickness:
        return [amin + span / 2.0], pitch
    n = int(math.floor((span - thickness) / pitch + 1e-9)) + 1
    n = max(1, n)
    if n > MAX_PANELS:
        raise ValueError(
            f"{n} panel oluşuyor — çok fazla. Panel kalınlığını artırın, "
            f"aralık ekleyin veya ölçeği küçültün (üst sınır {MAX_PANELS})."
        )
    used = (n - 1) * pitch + thickness
    start = amin + (span - used) / 2.0
    return [start + i * pitch + thickness / 2.0 for i in range(n)], pitch


def build_panels(tris, axis="z", thickness=18.0, gap=0.0, scale=1.0,
                 simplify_tol=0.15, hole_count=0, hole_dia=10.0, hole_margin=6.0):
    """Modeli dilimleyip panel kesitlerini üretir.

    Dönüş: {'panels': [...], 'pitch':, 'axis':, 'warnings': [...], 'info': {...}}
    Her panel: {'no', 'pos', 'loops', 'bbox', 'area_approx'}
    """
    axis = (axis or "z").lower()
    if axis not in _AXIS_IDX:
        axis = "z"
    ai = _AXIS_IDX[axis]
    pu, pv = _PROJ[axis]

    scale = float(scale or 1.0)
    if scale <= 0:
        scale = 1.0
    if scale != 1.0:
        tris = [tuple((v[0] * scale, v[1] * scale, v[2] * scale) for v in t) for t in tris]

    info = mesh_info(tris)
    amin, amax = info["min"][ai], info["max"][ai]
    positions, pitch = plan_positions(amin, amax, thickness, gap)

    # Düzlemler tam köşeye denk gelmesin diye mikro kaydırma
    eps = max((amax - amin), 1.0) * 1e-9
    planes = [p + eps for p in positions]

    # Üçgenleri eksen boyunca min değerine göre sırala → düzlem başına
    # sadece o düzlemi kesen üçgenlere bakılır.
    buckets = [[] for _ in planes]
    np_ = len(planes)
    for t in tris:
        a0 = t[0][ai]; a1 = t[1][ai]; a2 = t[2][ai]
        lo = a0 if a0 < a1 else a1
        if a2 < lo: lo = a2
        hi = a0 if a0 > a1 else a1
        if a2 > hi: hi = a2
        i0 = bisect_left(planes, lo)
        i1 = bisect_right(planes, hi)
        for pi in range(i0, i1):
            buckets[pi].append(t)

    tol = max((amax - amin), 1.0) * 1e-7
    warnings = []
    panels = []
    total_open = 0

    for pi, plane in enumerate(planes):
        segs = []
        for t in buckets[pi]:
            s = _tri_plane_segment(t, ai, plane, pu, pv)
            if s:
                segs.append(s)
        loops, open_n = _chain_loops(segs, tol)
        total_open += open_n

        clean = []
        for lp in loops:
            lp = _simplify(lp, simplify_tol)
            if len(lp) >= 3 and _polygon_area(lp) > 1e-6:
                clean.append(lp)
        if not clean:
            continue

        xs = [p[0] for lp in clean for p in lp]
        ys = [p[1] for lp in clean for p in lp]
        panels.append({
            "no": len(panels) + 1,
            "pos": positions[pi],
            "loops": clean,
            "bbox": (min(xs), min(ys), max(xs), max(ys)),
        })

    if not panels:
        raise ValueError(
            "Modelden hiç kesit çıkarılamadı. Dilimleme eksenini değiştirmeyi "
            "veya modelin kapalı (watertight) olduğundan emin olmayı deneyin."
        )

    if total_open:
        warnings.append(
            f"{total_open} adet açık kontur bulundu — model tam kapalı (watertight) değil. "
            "Kesim öncesi DXF'i kontrol edin."
        )

    skipped = len(positions) - len(panels)
    if skipped > 0:
        warnings.append(f"{skipped} dilim boş çıktığı için atlandı.")

    holes = []
    if hole_count > 0:
        holes, hw = find_assembly_holes(panels, hole_count, hole_dia, hole_margin)
        if hw:
            warnings.append(hw)
        if holes:
            r = hole_dia / 2.0
            for p in panels:
                p["holes"] = [(hx, hy, r) for hx, hy in holes]

    return {
        "panels": panels,
        "positions": positions,
        "pitch": pitch,
        "axis": axis,
        "thickness": thickness,
        "gap": gap,
        "scale": scale,
        "holes": holes,
        "hole_dia": hole_dia,
        "info": info,
        "warnings": warnings,
    }


def _polygon_area(pts):
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) * 0.5


# ══════════════════════════════════════════════════════════════════════════
#  3) Montaj (mil) deliği bulma — tüm panellerde ortak dolu bölge
# ══════════════════════════════════════════════════════════════════════════

def _inside_grid(loops, x0, y0, cell, nx, ny):
    """Panel malzemesinin içinde kalan grid hücrelerini scanline ile işaretler."""
    g = bytearray(nx * ny)
    for j in range(ny):
        y = y0 + (j + 0.5) * cell
        xs = []
        for lp in loops:
            n = len(lp)
            for i in range(n):
                xa, ya = lp[i]
                xb, yb = lp[(i + 1) % n]
                if (ya > y) != (yb > y):
                    xs.append(xa + (y - ya) / (yb - ya) * (xb - xa))
        if len(xs) < 2:
            continue
        xs.sort()
        row = j * nx
        for k in range(0, len(xs) - 1, 2):
            i0 = int(math.ceil((xs[k] - x0) / cell - 0.5))
            i1 = int(math.floor((xs[k + 1] - x0) / cell - 0.5))
            if i0 < 0: i0 = 0
            if i1 > nx - 1: i1 = nx - 1
            for i in range(i0, i1 + 1):
                g[row + i] = 1
    return g


def find_assembly_holes(panels, count, dia, margin=6.0):
    """Bütün panellerde ortak olan dolu bölgede montaj mili delikleri konumlandırır."""
    if count <= 0 or not panels:
        return [], ""

    # Tüm panellerin ortak sınır kutusu
    x0 = max(p["bbox"][0] for p in panels)
    y0 = max(p["bbox"][1] for p in panels)
    x1 = min(p["bbox"][2] for p in panels)
    y1 = min(p["bbox"][3] for p in panels)
    need = dia / 2.0 + margin
    if x1 - x0 < 2 * need or y1 - y0 < 2 * need:
        return [], "Paneller için ortak montaj deliği bölgesi bulunamadı — delik eklenmedi."

    w, h = x1 - x0, y1 - y0
    cell = max(min(w, h) / 60.0, 0.5)
    nx = max(4, int(w / cell))
    ny = max(4, int(h / cell))
    if nx * ny > 90_000:
        cell = math.sqrt(w * h / 90_000.0)
        nx = max(4, int(w / cell))
        ny = max(4, int(h / cell))

    acc = None
    for p in panels:
        g = _inside_grid(p["loops"], x0, y0, cell, nx, ny)
        if acc is None:
            acc = g
        else:
            for i in range(nx * ny):
                if acc[i] and not g[i]:
                    acc[i] = 0
        if not any(acc):
            return [], "Paneller için ortak montaj deliği bölgesi bulunamadı — delik eklenmedi."

    # Gerekli yarıçap kadar aşındır (erosion)
    k = int(math.ceil(need / cell))
    cand = []
    k2 = k * k
    for j in range(ny):
        for i in range(nx):
            if not acc[j * nx + i]:
                continue
            ok = True
            for dj in range(-k, k + 1):
                jj = j + dj
                if jj < 0 or jj >= ny:
                    ok = False
                    break
                base = jj * nx
                for di in range(-k, k + 1):
                    if di * di + dj * dj > k2:
                        continue
                    ii = i + di
                    if ii < 0 or ii >= nx or not acc[base + ii]:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                cand.append((x0 + (i + 0.5) * cell, y0 + (j + 0.5) * cell))

    if not cand:
        return [], (f"Ø{dia:g} mm montaj deliği için tüm panellerde ortak yeterli alan yok — "
                    "delik eklenmedi. Delik çapını veya kenar payını küçültmeyi deneyin.")

    # 1. delik: aday kümesinin ağırlık merkezine en yakın nokta
    cx = sum(p[0] for p in cand) / len(cand)
    cy = sum(p[1] for p in cand) / len(cand)
    picked = [min(cand, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)]
    # Sonraki delikler: mevcutlardan en uzak nokta (farthest point sampling)
    while len(picked) < count:
        best, bestd = None, -1.0
        for p in cand:
            d = min((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 for q in picked)
            if d > bestd:
                bestd, best = d, p
        if best is None or bestd < (dia * dia):
            break
        picked.append(best)

    warn = ""
    if len(picked) < count:
        warn = (f"{count} delik istendi, ortak alanda yalnızca {len(picked)} tanesi "
                "birbirinden yeterince uzağa yerleştirilebildi.")
    return picked, warn


# ══════════════════════════════════════════════════════════════════════════
#  4) Yerleşim (nesting)
# ══════════════════════════════════════════════════════════════════════════

def nest(panels, sheet_w=2100.0, sheet_h=2800.0, part_gap=15.0, margin=15.0):
    """Panelleri plakalara raf (shelf) yöntemiyle yerleştirir.

    Dönüş: [{'sheet':0,'no':1,'dx':..,'dy':..,'w':..,'h':..}, ...]
    """
    place = []
    sheet = 0
    cur_x = margin
    cur_y = margin
    row_h = 0.0
    oversize = []

    for p in panels:
        bx0, by0, bx1, by1 = p["bbox"]
        w = bx1 - bx0
        h = by1 - by0

        if w > sheet_w - 2 * margin or h > sheet_h - 2 * margin:
            oversize.append(p["no"])

        if cur_x + w > sheet_w - margin and cur_x > margin:
            cur_x = margin
            cur_y += row_h + part_gap
            row_h = 0.0
        if cur_y + h > sheet_h - margin and (cur_y > margin or row_h > 0):
            sheet += 1
            cur_x = margin
            cur_y = margin
            row_h = 0.0

        place.append({
            "sheet": sheet, "no": p["no"],
            "dx": cur_x - bx0, "dy": cur_y - by0,
            "w": w, "h": h,
            "x": cur_x, "y": cur_y,
        })
        cur_x += w + part_gap
        if h > row_h:
            row_h = h

    return place, sheet + 1, oversize


# ══════════════════════════════════════════════════════════════════════════
#  5) DXF çıktısı
# ══════════════════════════════════════════════════════════════════════════

L_OUT = "KESIM_DIS"
L_IN = "KESIM_IC"
L_HOLE = "DELIK"
L_TEXT = "YAZI"
L_SHEET = "PLAKA"


def _point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _classify_loops(loops):
    """Her konturun iç mi dış mı olduğunu belirler (even-odd yuvalama)."""
    out = []
    for i, lp in enumerate(loops):
        px, py = lp[0]
        depth = 0
        for k, other in enumerate(loops):
            if k == i:
                continue
            if _point_in_poly(px, py, other):
                depth += 1
        out.append((lp, depth % 2 == 1))  # True → iç kontur (delik)
    return out


def _new_doc():
    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4  # milimetre
    for name, color in ((L_OUT, 1), (L_IN, 3), (L_HOLE, 5), (L_TEXT, 2), (L_SHEET, 8)):
        if name not in doc.layers:
            doc.layers.add(name, color=color)
    return doc


def _add_text(msp, s, x, y, height, layer):
    t = msp.add_text(s, height=height, dxfattribs={"layer": layer})
    try:
        from ezdxf.enums import TextEntityAlignment
        t.set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER)
    except Exception:
        try:
            t.dxf.insert = (x, y)
        except Exception:
            pass
    return t


def _draw_panel(msp, panel, dx, dy, label=None, label_h=12.0):
    for lp, is_hole in _classify_loops(panel["loops"]):
        pts = [(x + dx, y + dy) for x, y in lp]
        msp.add_lwpolyline(pts, close=True,
                           dxfattribs={"layer": L_IN if is_hole else L_OUT})
    for hx, hy, r in panel.get("holes", ()):
        msp.add_circle((hx + dx, hy + dy), r, dxfattribs={"layer": L_HOLE})
    if label:
        bx0, by0, bx1, by1 = panel["bbox"]
        _add_text(msp, label, (bx0 + bx1) / 2 + dx, (by0 + by1) / 2 + dy, label_h, L_TEXT)


def export_dxf(result, sheet_w=2100.0, sheet_h=2800.0, part_gap=15.0,
               label=True, draw_sheets=True, job_name=""):
    """Tüm panelleri plakalara yerleştirip tek bir DXF üretir."""
    panels = result["panels"]
    places, sheet_count, oversize = nest(panels, sheet_w, sheet_h, part_gap)
    by_no = {p["no"]: p for p in panels}

    doc = _new_doc()
    msp = doc.modelspace()
    gutter = 250.0
    label_h = max(8.0, min(sheet_w, sheet_h) / 120.0)

    if draw_sheets:
        for s in range(sheet_count):
            ox = s * (sheet_w + gutter)
            msp.add_lwpolyline(
                [(ox, 0), (ox + sheet_w, 0), (ox + sheet_w, sheet_h), (ox, sheet_h)],
                close=True, dxfattribs={"layer": L_SHEET})
            _add_text(msp, f"PLAKA {s + 1}/{sheet_count}  {sheet_w:g}x{sheet_h:g}",
                      ox + sheet_w / 2, sheet_h + label_h * 2, label_h * 1.6, L_TEXT)

    for pl in places:
        ox = pl["sheet"] * (sheet_w + gutter)
        p = by_no[pl["no"]]
        _draw_panel(msp, p, pl["dx"] + ox, pl["dy"],
                    label=f"{pl['no']:02d}" if label else None, label_h=label_h)

    buf = io.StringIO()
    doc.write(buf)
    return buf.getvalue().encode("utf-8"), sheet_count, oversize


def export_zip(result, label=True, job_name="panel"):
    """Her panel için ayrı DXF içeren ZIP üretir."""
    panels = result["panels"]
    safe = "".join(c for c in (job_name or "panel") if c.isalnum() or c in "-_") or "panel"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in panels:
            doc = _new_doc()
            msp = doc.modelspace()
            bx0, by0, _, _ = p["bbox"]
            label_h = max(6.0, (p["bbox"][2] - bx0) / 12.0)
            _draw_panel(msp, p, -bx0, -by0,
                        label=f"{p['no']:02d}" if label else None, label_h=label_h)
            s = io.StringIO()
            doc.write(s)
            z.writestr(f"{safe}_{p['no']:03d}.dxf", s.getvalue())
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════
#  6) SVG önizleme
# ══════════════════════════════════════════════════════════════════════════

def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def export_svg(result, cols=6, cell=190, pad=10):
    """Panel kesitlerini ızgara halinde gösteren SVG önizleme üretir."""
    panels = result["panels"]
    n = len(panels)
    cols = max(1, min(cols, n))
    rows = int(math.ceil(n / cols))
    W = cols * cell
    H = rows * cell

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="100%" style="max-width:{W}px;height:auto;">'
    ]

    # Paneller birbiriyle kıyaslanabilsin diye tek ortak ölçek kullanılır
    gw = max((p["bbox"][2] - p["bbox"][0]) for p in panels)
    gh = max((p["bbox"][3] - p["bbox"][1]) for p in panels)
    s = min((cell - 2 * pad) / max(gw, 1e-6), (cell - 2 * pad - 12) / max(gh, 1e-6))

    for i, p in enumerate(panels):
        cx = (i % cols) * cell
        cy = (i // cols) * cell
        bx0, by0, bx1, by1 = p["bbox"]
        w = max(bx1 - bx0, 1e-6)
        h = max(by1 - by0, 1e-6)
        ox = cx + (cell - w * s) / 2
        oy = cy + (cell - 12 - h * s) / 2

        # SVG'de Y aşağı doğru → kesiti dikey çevir
        def tx(x, y):
            return (ox + (x - bx0) * s, oy + (by1 - y) * s)

        d = []
        for lp in p["loops"]:
            x, y = tx(*lp[0])
            d.append(f"M{x:.1f} {y:.1f}")
            for pt in lp[1:]:
                x, y = tx(*pt)
                d.append(f"L{x:.1f} {y:.1f}")
            d.append("Z")
        parts.append(
            f'<path d="{" ".join(d)}" fill="#c8a165" fill-rule="evenodd" '
            f'stroke="#6b4f2a" stroke-width="1" stroke-linejoin="round"/>'
        )
        for hx, hy, r in p.get("holes", ()):
            x, y = tx(hx, hy)
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{max(r * s, 1.2):.1f}" '
                         f'fill="#1b1b1b" opacity="0.75"/>')
        parts.append(
            f'<text x="{cx + cell / 2:.0f}" y="{cy + cell - 4:.0f}" text-anchor="middle" '
            f'font-family="system-ui,sans-serif" font-size="11" fill="#8b949e">'
            f'{p["no"]:02d}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def summary(result, sheet_count=None):
    """Sonuç özeti (şablonda gösterim için)."""
    panels = result["panels"]
    axis = result["axis"]
    info = result["info"]
    ai = _AXIS_IDX[axis]
    span = info["size"][ai]
    pu, pv = _PROJ[axis]
    xs0 = min(p["bbox"][0] for p in panels)
    ys0 = min(p["bbox"][1] for p in panels)
    xs1 = max(p["bbox"][2] for p in panels)
    ys1 = max(p["bbox"][3] for p in panels)
    total_len = sum(_loop_len(lp) for p in panels for lp in p["loops"])
    return {
        "panel_count": len(panels),
        "axis": axis,
        "thickness": result["thickness"],
        "gap": result["gap"],
        "pitch": result["pitch"],
        "stack_len": (len(panels) - 1) * result["pitch"] + result["thickness"],
        "model_span": span,
        "profile_w": xs1 - xs0,
        "profile_h": ys1 - ys0,
        "cut_len_m": total_len / 1000.0,
        "hole_count": len(result.get("holes") or []),
        "hole_dia": result.get("hole_dia", 0),
        "sheet_count": sheet_count,
        "warnings": result.get("warnings", []),
    }


def _loop_len(pts):
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += math.hypot(x2 - x1, y2 - y1)
    return s


# ══════════════════════════════════════════════════════════════════════════
#  7) Sonucu diske yazma / okuma (indirmede yeniden dilimlememek için)
# ══════════════════════════════════════════════════════════════════════════

def dump_result(result) -> bytes:
    """Dilimleme sonucunu sıkıştırılmış JSON olarak paketler."""
    import gzip, json
    r3 = lambda v: round(float(v), 3)
    data = {
        "axis": result["axis"],
        "thickness": result["thickness"],
        "gap": result["gap"],
        "scale": result["scale"],
        "pitch": result["pitch"],
        "hole_dia": result.get("hole_dia", 0),
        "holes": [[r3(x), r3(y)] for x, y in (result.get("holes") or [])],
        "info": {k: (list(v) if isinstance(v, tuple) else v)
                 for k, v in result["info"].items()},
        "warnings": result.get("warnings", []),
        "panels": [{
            "no": p["no"],
            "pos": r3(p["pos"]),
            "bbox": [r3(v) for v in p["bbox"]],
            "loops": [[[r3(x), r3(y)] for x, y in lp] for lp in p["loops"]],
            "holes": [[r3(x), r3(y), r3(r)] for x, y, r in p.get("holes", ())],
        } for p in result["panels"]],
    }
    return gzip.compress(json.dumps(data, separators=(",", ":")).encode("utf-8"), 6)


def load_result(blob: bytes):
    """dump_result çıktısını geri yükler."""
    import gzip, json
    d = json.loads(gzip.decompress(blob).decode("utf-8"))
    for p in d["panels"]:
        p["bbox"] = tuple(p["bbox"])
        p["loops"] = [[tuple(pt) for pt in lp] for lp in p["loops"]]
        p["holes"] = [tuple(h) for h in p.get("holes", [])]
    d["holes"] = [tuple(h) for h in d.get("holes", [])]
    d["info"]["size"] = tuple(d["info"]["size"])
    d["info"]["min"] = tuple(d["info"]["min"])
    d["info"]["max"] = tuple(d["info"]["max"])
    return d
