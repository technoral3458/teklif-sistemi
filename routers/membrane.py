import urllib.request
import xml.etree.ElementTree as ET
import base64
import json
import math as _math
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse, Response

import db.factory as fdb
import auth
from tmpl import templates


import re as _re

# ── NC Code Generator ─────────────────────────────────────────────────────────

_VAR_NORM = [('lpx', 'LPX'), ('lpy', 'LPY'), ('lpz', 'LPZ')]

def _normalize_expr(expr: str) -> str:
    """Normalize LPX/LPY/LPZ variable names to uppercase regardless of input case."""
    for lower, upper in _VAR_NORM:
        expr = _re.sub(r'(?i)\b' + lower + r'\b', upper, expr)
    return expr

def _eval_expr(expr, variables):
    """Safely evaluate a parametric expression using the given variables."""
    expr = _normalize_expr(str(expr).strip())
    env = {k: float(v) for k, v in variables.items()}
    env.update({k: getattr(_math, k) for k in dir(_math) if not k.startswith("_")})
    env["__builtins__"] = None
    return float(eval(expr, env))


def _generate_nc(model, paths, variables, x_off=0.0, y_off=0.0, prog_no=1):
    """Generate Fanuc-compatible G-code from a cap model and plate variables."""
    ev = lambda expr: _eval_expr(expr, variables)
    lines = []
    name_upper = model["name"].upper().replace("(", "").replace(")", "")
    var_comment = " ".join(f"{k}={v}" for k, v in sorted(variables.items()))
    safe_z = float(model.get("safe_z") or 5.0)
    feed_xy = int(model.get("feed_xy") or 3000)
    feed_z = int(model.get("feed_z") or 1000)
    spindle = int(model.get("spindle_speed") or 18000)
    default_tool = int(model.get("tool_no") or 1)
    off_comment = f" OFS X{x_off:.1f} Y{y_off:.1f}" if (x_off or y_off) else ""

    lines += [
        "%",
        f"O{prog_no:04d} ({name_upper}{off_comment})",
        f"({var_comment})",
        f"(GENERATED {datetime.now().strftime('%Y-%m-%d %H:%M')})",
        "G17 G21 G40 G49 G80 G90",
        f"T{default_tool} M6",
        f"S{spindle} M3",
        f"G0 G90 Z{safe_z:.3f}",
    ]
    cur_tool = default_tool

    for p in paths:
        label = (p.get("label") or "").strip()
        ptype = p.get("path_type", "LINE")
        path_tool = int(p.get("tool_no") or 0) or default_tool
        if path_tool != cur_tool:
            lines += [f"G0 Z{safe_z:.3f}", "M5",
                      f"T{path_tool} M6", f"S{spindle} M3",
                      f"G0 G90 Z{safe_z:.3f}"]
            cur_tool = path_tool
        if label:
            lines.append(f"({label})")

        try:
            x1 = ev(p["x1"]) + x_off; y1 = ev(p["y1"]) + y_off
            x2 = ev(p["x2"]) + x_off; y2 = ev(p["y2"]) + y_off
            z2 = ev(p["z2"])
            feed = int(ev(p["feed_override"])) if str(p.get("feed_override", "")).strip() else feed_xy

            if ptype == "LINE":
                lines += [
                    f"G0 Z{safe_z:.3f}",
                    f"G0 X{x1:.3f} Y{y1:.3f}",
                    f"G1 Z{z2:.3f} F{feed_z}",
                    f"G1 X{x2:.3f} Y{y2:.3f} F{feed}",
                ]

            elif ptype in ("ARC_CW", "ARC_CCW"):
                cx = ev(p.get("ix") or "0") + x_off
                cy = ev(p.get("jy") or "0") + y_off
                I = round(cx - x1, 3); J = round(cy - y1, 3)
                cmd = "G2" if ptype == "ARC_CW" else "G3"
                lines += [
                    f"G0 Z{safe_z:.3f}",
                    f"G0 X{x1:.3f} Y{y1:.3f}",
                    f"G1 Z{z2:.3f} F{feed_z}",
                    f"{cmd} X{x2:.3f} Y{y2:.3f} I{I:.3f} J{J:.3f} F{feed}",
                ]

            elif ptype == "POCKET":
                tool_dia = float(p.get("tool_dia") or 8.0)
                step_over = float(p.get("step_over") or 0.5)
                step = max(0.1, tool_dia * step_over)
                r = tool_dia / 2.0
                lx = min(x1, x2) + r; rx = max(x1, x2) - r
                by = min(y1, y2) + r; ty = max(y1, y2) - r
                lines.append(f"G0 Z{safe_z:.3f}")
                direction = 1; y = by
                while y <= ty + 0.001:
                    sx, ex = (lx, rx) if direction == 1 else (rx, lx)
                    lines += [f"G0 X{sx:.3f} Y{y:.3f}",
                              f"G1 Z{z2:.3f} F{feed_z}",
                              f"G1 X{ex:.3f} F{feed}",
                              f"G0 Z{safe_z:.3f}"]
                    y = round(y + step, 4); direction *= -1
                lines += [f"G0 X{lx:.3f} Y{by:.3f}", f"G1 Z{z2:.3f} F{feed_z}",
                          f"G1 X{rx:.3f} F{feed}", f"G1 Y{ty:.3f}",
                          f"G1 X{lx:.3f}", f"G1 Y{by:.3f}", f"G0 Z{safe_z:.3f}"]

        except Exception as exc:
            lines.append(f"(ERROR IN PATH '{label or ptype}': {exc})")

    lines += [f"G0 Z{safe_z:.3f}", "M5", "G28 G91 Z0.", "M30", "%"]
    return "\n".join(lines)


# ── Ops/Moves NC generator ────────────────────────────────────────────────────

_CORNER_LABELS = {'BL':'Sol-Alt','TL':'Sol-Ust','BR':'Sag-Alt','TR':'Sag-Ust'}


def _circumcenter(x1, y1, x2, y2, x3, y3):
    """Return (cx, cy) of circumcircle passing through 3 points."""
    ax, ay = x2 - x1, y2 - y1
    bx, by = x3 - x1, y3 - y1
    D = 2.0 * (ax * by - ay * bx)
    if abs(D) < 1e-10:
        raise ValueError("Collinear points – cannot form arc")
    ux = (by * (ax*ax + ay*ay) - ay * (bx*bx + by*by)) / D
    uy = (ax * (bx*bx + by*by) - bx * (ax*ax + ay*ay)) / D
    return x1 + ux, y1 + uy


def _apply_corner(x, y, ref, W, H):
    if ref == 'TL':   return x, H - y
    elif ref == 'BR': return W - x, y
    elif ref == 'TR': return W - x, H - y
    return x, y  # BL default


def _sort_ops_inner_first(ops):
    """Inner cuts (pockets/holes) before outer profile cuts."""
    return sorted(ops, key=lambda o: (0 if o.get('op_type', 'inner') == 'inner' else 1, o.get('seq', 0)))


def _split_op_at_last_start(op):
    """Split a single op's moves at the last START move.
    Returns (inner_op, outer_op) dicts. outer_op is None if < 2 STARTs."""
    moves = op.get('moves', [])
    start_idxs = [i for i, m in enumerate(moves) if m.get('move_type') == 'start']
    if len(start_idxs) < 2:
        return op, None
    last = start_idxs[-1]
    inner_op = dict(op, moves=moves[:last])
    outer_op = dict(op, moves=moves[last:])
    return inner_op, outer_op


def _generate_nc_ops(model, ops, variables, x_off=0.0, y_off=0.0, prog_no=1):
    ev = lambda expr: _eval_expr(expr, variables)
    W = float(variables.get('LPX', 0)); H = float(variables.get('LPY', 0))
    name_upper = model["name"].upper().replace("(", "").replace(")", "")
    var_comment = " ".join(f"{k}={v}" for k, v in sorted(variables.items()))
    safe_z = float(model.get("safe_z") or 5.0)
    feed_xy = int(model.get("feed_xy") or 3000)
    feed_z = int(model.get("feed_z") or 1000)
    spindle = int(model.get("spindle_speed") or 18000)
    off_comment = f" OFS X{x_off:.1f} Y{y_off:.1f}" if (x_off or y_off) else ""

    lines = [
        "%", f"O{prog_no:04d} ({name_upper}{off_comment})",
        f"({var_comment})",
        f"(GENERATED {datetime.now().strftime('%Y-%m-%d %H:%M')})",
        "G17 G21 G40 G49 G80 G90",
    ]
    if not ops:
        lines += ["(NO OPERATIONS)", "M30", "%"]
        return "\n".join(lines)

    cur_tool = None
    for op in ops:
        ref = op.get('ref_corner') or 'BL'
        op_tool = int(op.get('tool_no') or 1)
        try:    op_depth = ev(op.get('depth') or '-LPZ')
        except: op_depth = -5.0
        feed_str = str(op.get('feed') or '').strip()
        try:    op_feed = int(ev(feed_str)) if feed_str else feed_xy
        except: op_feed = feed_xy

        if cur_tool is None:
            lines += [f"T{op_tool} M6", f"S{spindle} M3", f"G0 G90 Z{safe_z:.3f}"]
        elif op_tool != cur_tool:
            lines += [f"G0 Z{safe_z:.3f}", "M5",
                      f"T{op_tool} M6", f"S{spindle} M3", f"G0 G90 Z{safe_z:.3f}"]
        cur_tool = op_tool

        # Tool radius compensation
        comp = (op.get('comp_mode') or 'none').upper()
        offset_side = op.get('offset_side') or 'center'
        tool_dia = 0.0
        if comp in ('G41', 'G42'):
            tid = op.get('tool_id')
            t = fdb.get_tool(tid) if tid else None
            tool_dia = float(t['diameter']) if t else 0.0

        op_name = (op.get('name') or '').strip() or f"OP{op.get('seq',0)}"
        comp_label = f" {comp} R={tool_dia:.1f}mm" if comp != 'NONE' else ""
        lines.append(f"({op_name} T{op_tool} F{op_feed} Z{op_depth:.3f} REF:{_CORNER_LABELS.get(ref,ref)}{comp_label})")

        cur_x = cur_y = 0.0; plunged = False; comp_active = False
        for mv in op.get('moves', []):
            mt = mv.get('move_type', 'line')
            try:
                mx = ev(mv.get('x') or '0'); my = ev(mv.get('y') or '0')
                ax, ay = _apply_corner(mx, my, ref, W, H)
                ax += x_off; ay += y_off
                if mt == 'start':
                    if plunged:
                        if comp_active: lines.append("G40"); comp_active = False
                        lines.append(f"G0 Z{safe_z:.3f}")
                    lines += [f"G0 X{ax:.3f} Y{ay:.3f}", f"G1 Z{op_depth:.3f} F{feed_z}"]
                    cur_x = ax; cur_y = ay; plunged = True
                elif mt == 'line' and plunged:
                    if comp in ('G41', 'G42') and not comp_active:
                        lines.append(f"{comp} D{op_tool:02d}")
                        comp_active = True
                    lines.append(f"G1 X{ax:.3f} Y{ay:.3f} F{op_feed}")
                    cur_x = ax; cur_y = ay
                elif mt in ('arc_cw','arc_ccw') and plunged:
                    if comp in ('G41', 'G42') and not comp_active:
                        lines.append(f"{comp} D{op_tool:02d}")
                        comp_active = True
                    mcx = ev(mv.get('cx') or '0'); mcy = ev(mv.get('cy') or '0')
                    acx, acy = _apply_corner(mcx, mcy, ref, W, H)
                    acx += x_off; acy += y_off
                    I = round(acx - cur_x, 3); J = round(acy - cur_y, 3)
                    cmd = 'G2' if mt == 'arc_cw' else 'G3'
                    lines.append(f"{cmd} X{ax:.3f} Y{ay:.3f} I{I:.3f} J{J:.3f} F{op_feed}")
                    cur_x = ax; cur_y = ay
                elif mt == 'arc_3p' and plunged:
                    if comp in ('G41', 'G42') and not comp_active:
                        lines.append(f"{comp} D{op_tool:02d}")
                        comp_active = True
                    # cx,cy store the through/mid point
                    mid_x = ev(mv.get('cx') or '0'); mid_y = ev(mv.get('cy') or '0')
                    amid_x, amid_y = _apply_corner(mid_x, mid_y, ref, W, H)
                    amid_x += x_off; amid_y += y_off
                    ccx, ccy = _circumcenter(cur_x, cur_y, amid_x, amid_y, ax, ay)
                    # cross product sign → CCW (G3) if positive, CW (G2) if negative
                    cross = (amid_x - cur_x) * (ay - cur_y) - (amid_y - cur_y) * (ax - cur_x)
                    I = round(ccx - cur_x, 3); J = round(ccy - cur_y, 3)
                    cmd = 'G3' if cross > 0 else 'G2'
                    lines.append(f"{cmd} X{ax:.3f} Y{ay:.3f} I{I:.3f} J{J:.3f} F{op_feed}")
                    cur_x = ax; cur_y = ay
                elif mt in ('arc_cw_r', 'arc_ccw_r') and plunged:
                    if comp in ('G41', 'G42') and not comp_active:
                        lines.append(f"{comp} D{op_tool:02d}")
                        comp_active = True
                    r_val = ev(mv.get('r') or '0')
                    cmd = 'G2' if mt == 'arc_cw_r' else 'G3'
                    lines.append(f"{cmd} X{ax:.3f} Y{ay:.3f} R{r_val:.3f} F{op_feed}")
                    cur_x = ax; cur_y = ay
            except Exception as exc:
                lines.append(f"(ERROR: {exc})")
        if plunged:
            if comp_active: lines.append("G40")
            lines.append(f"G0 Z{safe_z:.3f}")

    lines += ["M5", "G28 G91 Z0.", "M30", "%"]
    return "\n".join(lines)


def _eval_ops(model, ops, variables, x_off=0.0, y_off=0.0):
    ev = lambda expr: _eval_expr(expr, variables)
    W = float(variables.get('LPX', 0)); H = float(variables.get('LPY', 0))
    safe_z = float(model.get('safe_z') or 5.0)
    result = []
    for op in ops:
        ref = op.get('ref_corner') or 'BL'
        try:    depth = ev(op.get('depth') or '-LPZ')
        except: depth = -5.0
        cur_x = cur_y = 0.0; plunged = False
        for mv in op.get('moves', []):
            mt = mv.get('move_type', 'line')
            try:
                mx = ev(mv.get('x') or '0'); my = ev(mv.get('y') or '0')
                ax, ay = _apply_corner(mx, my, ref, W, H)
                ax += x_off; ay += y_off
                if mt == 'start':
                    # zero-length entry: simulation shows rapid to this point
                    result.append({'type':'LINE','x1':ax,'y1':ay,'x2':ax,'y2':ay,'z2':depth,'label':'START'})
                    cur_x = ax; cur_y = ay; plunged = True
                elif mt == 'line' and plunged:
                    result.append({'type':'LINE','x1':cur_x,'y1':cur_y,'x2':ax,'y2':ay,'z2':depth})
                    cur_x = ax; cur_y = ay
                elif mt in ('arc_cw','arc_ccw') and plunged:
                    mcx = ev(mv.get('cx') or '0'); mcy = ev(mv.get('cy') or '0')
                    acx, acy = _apply_corner(mcx, mcy, ref, W, H)
                    acx += x_off; acy += y_off
                    result.append({'type':'ARC_CW' if mt=='arc_cw' else 'ARC_CCW',
                                   'x1':cur_x,'y1':cur_y,'x2':ax,'y2':ay,
                                   'cx':acx,'cy':acy,'z2':depth})
                    cur_x = ax; cur_y = ay
                elif mt == 'arc_3p' and plunged:
                    mid_x = ev(mv.get('cx') or '0'); mid_y = ev(mv.get('cy') or '0')
                    amid_x, amid_y = _apply_corner(mid_x, mid_y, ref, W, H)
                    amid_x += x_off; amid_y += y_off
                    ccx, ccy = _circumcenter(cur_x, cur_y, amid_x, amid_y, ax, ay)
                    cross = (amid_x - cur_x) * (ay - cur_y) - (amid_y - cur_y) * (ax - cur_x)
                    atype = 'ARC_CCW' if cross > 0 else 'ARC_CW'
                    result.append({'type': atype, 'x1':cur_x,'y1':cur_y,'x2':ax,'y2':ay,
                                   'cx':ccx,'cy':ccy,'z2':depth})
                    cur_x = ax; cur_y = ay
                elif mt in ('arc_cw_r', 'arc_ccw_r') and plunged:
                    r_val = ev(mv.get('r') or '0')
                    atype = 'ARC_CW' if mt == 'arc_cw_r' else 'ARC_CCW'
                    result.append({'type': atype, 'x1':cur_x,'y1':cur_y,'x2':ax,'y2':ay,
                                   'r': r_val, 'z2':depth})
                    cur_x = ax; cur_y = ay
            except Exception as exc:
                result.append({'type':'ERROR','label':str(exc),'x1':x_off,'y1':y_off,'x2':x_off,'y2':y_off,'z2':0})
    return {'paths': result, 'safe_z': safe_z}


# ── Nesting algorithm (shelf / strip packing with rotation) ───────────────────

_NEST_COLORS = ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6',
                '#06b6d4','#ec4899','#84cc16','#f97316','#14b8a6']

def _nest(items, sheet_w, sheet_h, margin=5.0, allow_rotate=True):
    """
    Pack cap rectangles onto sheets using MaxRects (BSSF) algorithm.
    items: list of {cap_w, cap_h, qty, model_name, model_id}
    Returns (placements, sheet_count, util_pct)
    Each placement: {x, y, w, h, label, color, sheet, rotated, group, model_id, cap_w, cap_h}
    """
    pieces = []
    for i, item in enumerate(items):
        w, h = float(item['cap_w']), float(item['cap_h'])
        name = (item.get('model_name') or '').strip()
        label = f"{name}\n{int(w)}×{int(h)}" if name else f"{int(w)}×{int(h)}"
        for _ in range(max(1, int(item.get('qty', 1)))):
            pieces.append({'ow': w, 'oh': h, 'label': label,
                          'color': _NEST_COLORS[i % len(_NEST_COLORS)],
                          'group': i, 'model_id': item.get('model_id'),
                          'cap_w': w, 'cap_h': h})

    # MaxRects BSSF core — run once for a given piece ordering
    def _maxrects_run(ordered_pieces):
        sf: list[list[tuple]] = []  # free rect lists per sheet

        def _new():
            sf.append([(margin, margin, sheet_w - 2*margin, sheet_h - 2*margin)])
            return len(sf) - 1

        def _find(si, pw, ph):
            ew, eh = pw + margin, ph + margin
            best_score, best_pos = float('inf'), None
            for (rx, ry, rw, rh) in sf[si]:
                if ew <= rw and eh <= rh:
                    score = min(rw - ew, rh - eh)
                    if score < best_score:
                        best_score, best_pos = score, (rx, ry)
            return best_pos

        def _update(si, px, py, pw, ph):
            ew, eh = pw + margin, ph + margin
            nr = []
            for (rx, ry, rw, rh) in sf[si]:
                if not (px < rx+rw and px+ew > rx and py < ry+rh and py+eh > ry):
                    nr.append((rx, ry, rw, rh)); continue
                if px > rx:            nr.append((rx, ry, px-rx, rh))
                if px+ew < rx+rw:     nr.append((px+ew, ry, rx+rw-px-ew, rh))
                if py > ry:            nr.append((rx, ry, rw, py-ry))
                if py+eh < ry+rh:     nr.append((rx, py+eh, rw, ry+rh-py-eh))
            # Prune non-maximal
            n, result = len(nr), []
            for i in range(n):
                ax, ay, aw, ah = nr[i]
                if not any(j != i and nr[j][0]<=ax and nr[j][1]<=ay
                           and nr[j][0]+nr[j][2]>=ax+aw and nr[j][1]+nr[j][3]>=ay+ah
                           for j in range(n)):
                    result.append(nr[i])
            sf[si] = result

        result_pl = []
        for pc in ordered_pieces:
            orientations = [(pc['ow'], pc['oh'], False)]
            if allow_rotate and abs(pc['ow'] - pc['oh']) > 0.5:
                orientations.append((pc['oh'], pc['ow'], True))
            placed = False
            for w, h, rot in orientations:
                for si in range(len(sf)):
                    pos = _find(si, w, h)
                    if pos:
                        _update(si, pos[0], pos[1], w, h)
                        result_pl.append({'x': round(pos[0],2), 'y': round(pos[1],2),
                                         'w': w, 'h': h, 'label': pc['label'],
                                         'color': pc['color'], 'sheet': si,
                                         'rotated': rot, 'group': pc['group'],
                                         'model_id': pc['model_id'],
                                         'cap_w': pc['cap_w'], 'cap_h': pc['cap_h']})
                        placed = True; break
                if placed: break
            if not placed:
                si = _new()
                for w, h, rot in orientations:
                    pos = _find(si, w, h)
                    if pos:
                        _update(si, pos[0], pos[1], w, h)
                        result_pl.append({'x': round(pos[0],2), 'y': round(pos[1],2),
                                         'w': w, 'h': h, 'label': pc['label'],
                                         'color': pc['color'], 'sheet': si,
                                         'rotated': rot, 'group': pc['group'],
                                         'model_id': pc['model_id'],
                                         'cap_w': pc['cap_w'], 'cap_h': pc['cap_h']})
                        placed = True; break
                if not placed:
                    result_pl.append({'x': margin, 'y': margin,
                                     'w': pc['ow'], 'h': pc['oh'], 'label': pc['label'],
                                     'color': pc['color'], 'sheet': si, 'rotated': False,
                                     'group': pc['group'], 'model_id': pc['model_id'],
                                     'cap_w': pc['cap_w'], 'cap_h': pc['cap_h']})
        ns = max(1, len(sf))
        used = sum(p['w'] * p['h'] for p in result_pl)
        util = round(used / (sheet_w * sheet_h * ns) * 100, 1) if ns else 0
        return result_pl, ns, util

    # Try multiple sort orders, keep the best (fewest sheets, then highest util)
    sort_keys = [
        lambda p: -(p['ow'] * p['oh']),                          # area desc
        lambda p: -(p['ow'] + p['oh']) * 2,                      # perimeter desc
        lambda p: -max(p['ow'], p['oh']),                         # longest side desc
        lambda p: (-min(p['ow'], p['oh']), -max(p['ow'], p['oh'])),  # shortest side desc
        lambda p: (-(p['ow'] * p['oh']), p['group']),             # area desc, grouped
    ]

    best_pl, best_ns, best_util = None, float('inf'), 0
    for sk in sort_keys:
        pl, ns, util = _maxrects_run(sorted(pieces, key=sk))
        if ns < best_ns or (ns == best_ns and util > best_util):
            best_pl, best_ns, best_util = pl, ns, util

    return best_pl, best_ns, best_util


def _eval_paths(model, paths, variables, x_off=0.0, y_off=0.0):
    """Return evaluated path coordinates for frontend simulation."""
    ev = lambda expr: _eval_expr(expr, variables)
    safe_z = float(model.get("safe_z") or 5.0)
    result = []
    for p in paths:
        try:
            ep = {
                "label": p.get("label") or "",
                "type": p.get("path_type", "LINE"),
                "x1": round(ev(p["x1"]) + x_off, 4),
                "y1": round(ev(p["y1"]) + y_off, 4),
                "x2": round(ev(p["x2"]) + x_off, 4),
                "y2": round(ev(p["y2"]) + y_off, 4),
                "z2": round(ev(p["z2"]), 4),
            }
            if ep["type"] in ("ARC_CW", "ARC_CCW"):
                ep["cx"] = round(ev(p.get("ix") or "0") + x_off, 4)
                ep["cy"] = round(ev(p.get("jy") or "0") + y_off, 4)
            if ep["type"] == "POCKET":
                ep["tool_dia"] = float(p.get("tool_dia") or 8.0)
                ep["step_over"] = float(p.get("step_over") or 0.5)
            result.append(ep)
        except Exception as exc:
            result.append({"type": "ERROR", "label": str(exc),
                           "x1": x_off, "y1": y_off, "x2": x_off, "y2": y_off, "z2": 0})
    return {"paths": result, "safe_z": safe_z}

router = APIRouter(prefix="/membrane")


def _fetch_live_rates():
    try:
        url = "https://www.tcmb.gov.tr/kurlar/today.xml"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
        root = ET.fromstring(data)
        result = {}
        for cur_el in root.findall("Currency"):
            code = cur_el.get("CurrencyCode") or cur_el.get("Kod", "")
            if code not in ("USD", "EUR", "GBP"):
                continue
            unit_el = cur_el.find("Unit")
            unit = int(unit_el.text) if unit_el is not None and unit_el.text else 1
            selling_el = cur_el.find("ForexSelling")
            if selling_el is not None and selling_el.text:
                rate = float(selling_el.text.replace(",", ".")) / unit
                result[code] = round(rate, 4)
        return result, None
    except Exception as e:
        return None, str(e)


def _calc_price_try(price, currency, rates):
    if currency == "TRY":
        return float(price)
    r = rates.get(currency, {}).get("rate", 1) or 1
    return float(price) * float(r)


def _material_cost_per_m2(mat, rates):
    price_try = _calc_price_try(mat["price"], mat["currency"], rates)
    if mat["unit"] == "plaka":
        w = float(mat["sheet_width"] or 0)
        h = float(mat["sheet_height"] or 0)
        area = (w / 100) * (h / 100)
        price_per_m2 = price_try / area if area > 0 else 0
    elif mat["unit"] == "m2":
        price_per_m2 = price_try
    else:
        price_per_m2 = price_try * float(mat["usage_per_m2"] or 0)
    return price_per_m2


def _enrich_doors(doors, total_cost_per_m2):
    for door in doors:
        area = (float(door["width_mm"]) / 1000) * (float(door["height_mm"]) / 1000)
        door["area_m2"] = round(area, 4)
        door["unit_cost"] = round(total_cost_per_m2 * area, 2)
        door["total_cost"] = round(door["unit_cost"] * int(door["quantity"]), 2)
    return doors


def _base_ctx(user, materials, rates):
    for mat in materials:
        mat["cost_per_m2_try"] = _material_cost_per_m2(mat, rates)
    total_cost_per_m2 = sum(m["cost_per_m2_try"] for m in materials)
    return materials, rates, round(total_cost_per_m2, 2)


# ── Main page: materials + rates + lists overview ─────────────────────────────

@router.get("")
async def membrane_page(request: Request):
    user = auth.require_user(request)
    materials = fdb.get_membrane_materials()
    rates = fdb.get_membrane_rates()
    materials, rates, total_cost_per_m2 = _base_ctx(user, materials, rates)

    lists = fdb.get_membrane_lists()
    for lst in lists:
        doors = fdb.get_membrane_doors_by_list(lst["id"])
        lst["total_cost"] = round(sum(
            total_cost_per_m2 * (float(d["width_mm"])/1000) * (float(d["height_mm"])/1000) * int(d["quantity"])
            for d in doors
        ), 2)

    return templates.TemplateResponse(request, "membrane_cost.html", {
        "user": user, "materials": materials, "rates": rates,
        "total_cost_per_m2": total_cost_per_m2, "lists": lists,
        "active_page": "membrane",
    })


# ── Rates ─────────────────────────────────────────────────────────────────────

@router.post("/rates/fetch")
async def fetch_rates(request: Request):
    user = auth.require_user(request)
    result, err = _fetch_live_rates()
    if result:
        for cur, rate in result.items():
            fdb.set_membrane_rate(cur, rate)
        msg, msg_type = f"Merkez Bankası kurları güncellendi ({', '.join(f'{c}: {r:.4f} ₺' for c,r in result.items())})", "success"
    else:
        msg, msg_type = f"Merkez Bankası'na bağlanılamadı: {err}. Kurları elle giriniz.", "danger"
    materials = fdb.get_membrane_materials()
    rates = fdb.get_membrane_rates()
    materials, rates, total_cost_per_m2 = _base_ctx(user, materials, rates)
    lists = fdb.get_membrane_lists()
    for lst in lists:
        doors = fdb.get_membrane_doors_by_list(lst["id"])
        lst["total_cost"] = round(sum(
            total_cost_per_m2 * (float(d["width_mm"])/1000) * (float(d["height_mm"])/1000) * int(d["quantity"])
            for d in doors
        ), 2)
    return templates.TemplateResponse(request, "membrane_cost.html", {
        "user": user, "materials": materials, "rates": rates,
        "total_cost_per_m2": total_cost_per_m2, "lists": lists,
        "active_page": "membrane", "msg": msg, "msg_type": msg_type,
    })


@router.post("/rates/save")
async def save_rates(request: Request,
                     usd: float = Form(0), eur: float = Form(0), gbp: float = Form(0)):
    auth.require_user(request)
    if usd > 0: fdb.set_membrane_rate("USD", usd)
    if eur > 0: fdb.set_membrane_rate("EUR", eur)
    if gbp > 0: fdb.set_membrane_rate("GBP", gbp)
    return RedirectResponse("/membrane", 303)


# ── Materials ─────────────────────────────────────────────────────────────────

@router.post("/material/save")
async def save_material(request: Request,
                        id: int = Form(0), name: str = Form(...),
                        material_type: str = Form("other"), price: float = Form(0),
                        currency: str = Form("TRY"), unit: str = Form("m2"),
                        sheet_width: float = Form(0), sheet_height: float = Form(0),
                        usage_per_m2: float = Form(1), notes: str = Form("")):
    auth.require_user(request)
    fdb.save_membrane_material(
        id=id or None, name=name, material_type=material_type,
        price=price, currency=currency, unit=unit,
        sheet_width=sheet_width, sheet_height=sheet_height,
        usage_per_m2=usage_per_m2, notes=notes,
    )
    return RedirectResponse("/membrane", 303)


@router.post("/material/delete")
async def delete_material(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_membrane_material(id)
    return RedirectResponse("/membrane", 303)


# ── Lists ─────────────────────────────────────────────────────────────────────

@router.post("/list/save")
async def save_list(request: Request, id: int = Form(0),
                    name: str = Form(...), notes: str = Form("")):
    auth.require_user(request)
    lid = fdb.save_membrane_list(id=id or None, name=name, notes=notes)
    return RedirectResponse(f"/membrane/list/{lid}", 303)


@router.post("/list/delete")
async def delete_list(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_membrane_list(id)
    return RedirectResponse("/membrane", 303)


# ── List Detail ───────────────────────────────────────────────────────────────

@router.get("/list/{lid}")
async def list_detail(request: Request, lid: int):
    user = auth.require_user(request)
    lst = fdb.get_membrane_list(lid)
    if not lst:
        return RedirectResponse("/membrane", 303)
    materials = fdb.get_membrane_materials()
    rates = fdb.get_membrane_rates()
    materials, rates, total_cost_per_m2 = _base_ctx(user, materials, rates)
    doors = _enrich_doors(fdb.get_membrane_doors_by_list(lid), total_cost_per_m2)
    grand_total = sum(d["total_cost"] for d in doors)
    grand_area = sum(d["area_m2"] * d["quantity"] for d in doors)
    return templates.TemplateResponse(request, "membrane_list.html", {
        "user": user, "lst": lst, "doors": doors, "materials": materials,
        "rates": rates, "total_cost_per_m2": total_cost_per_m2,
        "grand_total": round(grand_total, 2), "grand_area": round(grand_area, 4),
        "active_page": "membrane",
    })


@router.get("/list/{lid}/print")
async def print_list(request: Request, lid: int):
    user = auth.require_user(request)
    lst = fdb.get_membrane_list(lid)
    if not lst:
        return RedirectResponse("/membrane", 303)
    materials = fdb.get_membrane_materials()
    rates = fdb.get_membrane_rates()
    materials, rates, total_cost_per_m2 = _base_ctx(user, materials, rates)
    doors = _enrich_doors(fdb.get_membrane_doors_by_list(lid), total_cost_per_m2)
    grand_total = sum(d["total_cost"] for d in doors)
    grand_area = sum(d["area_m2"] * d["quantity"] for d in doors)
    company = fdb.get_company()
    return templates.TemplateResponse(request, "membrane_print.html", {
        "user": user, "lst": lst, "doors": doors, "company": company,
        "total_cost_per_m2": total_cost_per_m2,
        "grand_total": round(grand_total, 2), "grand_area": round(grand_area, 4),
    })


@router.post("/list/{lid}/door/save")
async def save_door(request: Request, lid: int,
                    id: int = Form(0), project_name: str = Form(""),
                    door_name: str = Form(""), width_mm: float = Form(...),
                    height_mm: float = Form(...), quantity: int = Form(1)):
    auth.require_user(request)
    fdb.save_membrane_door(
        id=id or None, project_name=project_name, door_name=door_name,
        width_mm=width_mm, height_mm=height_mm, quantity=quantity, list_id=lid,
    )
    return RedirectResponse(f"/membrane/list/{lid}", 303)


@router.post("/list/{lid}/door/delete")
async def delete_door(request: Request, lid: int, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_membrane_door(id)
    return RedirectResponse(f"/membrane/list/{lid}", 303)


@router.post("/list/{lid}/door/clear")
async def clear_doors(request: Request, lid: int):
    auth.require_user(request)
    for door in fdb.get_membrane_doors_by_list(lid):
        fdb.del_membrane_door(door["id"])
    return RedirectResponse(f"/membrane/list/{lid}", 303)


@router.post("/list/{lid}/door/scan")
async def scan_image(request: Request, lid: int, image: UploadFile = File(...)):
    auth.require_user(request)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return JSONResponse({"error": "ANTHROPIC_API_KEY ayarlanmamış. Sunucuda bu ortam değişkenini tanımlayın."}, status_code=500)

    content = await image.read()
    b64 = base64.standard_b64encode(content).decode()
    mime = image.content_type or "image/jpeg"

    prompt = """Bu görselde Türk mobilya/mutfak sektörüne ait el yazısıyla yazılmış membran kapak ölçü listesi var.
Tüm satırları tek tek oku ve kapak ölçülerini JSON array olarak çıkar.

OKUMA KURALLARI (çok önemli):
1. FORMAT: Genellikle "Boy x En = Adet" ya da "En x Boy = Adet" sırasında yazılır.
   Sütun başlıklarına bak (Boy/En/Adet gibi) — yoksa bağlamdan anla.
2. AYRAÇLAR: "x", "X", "×" ölçü ayracı; "=" ya da "-" ise adeti gösterir.
   Örn: "85X38=8" → boy=85, en=38, adet=8
3. ÖLÇÜ BİRİMİ TESPİTİ:
   - 2 haneli sayılar (10-99): büyük ihtimalle cm → mm'ye çevir (×10)
   - 3 haneli sayılar (100-999): büyük ihtimalle mm → direkt kullan
   - Şüpheliyse: tipik kapak en 150-1200mm, boy 150-2500mm aralığında olur
4. KESME / TAKSIM İŞARETİ: "/" rakamın parçası olabilir.
   Örn: "29/2" → 292, "11'5" veya "11.5" → 115, "14X59/7" → en=14cm=140mm, boy=597mm
5. ÜZERİ ÇİZİLİ SATIRLARI ATLA — iptal edilmiştir.
6. RENK/MODEL NOTU: Sayfanın kenarında renk kodu veya model adı varsa
   (örn: "STN Mercan", "Beyaz", "VR-805") tüm kapaklar için color alanına yaz.
7. AÇIKLAMALAR: "Tay lazım", "baca", "topuz" gibi notlar door_name'e yaz, ölçü olarak alma.

ÇIKTI — yalnızca geçerli JSON array döndür, başka hiçbir şey yazma:
[
  {"width_mm": 380, "height_mm": 850, "quantity": 8, "door_name": "", "color": "STN Mercan"},
  {"width_mm": 650, "height_mm": 250, "quantity": 1, "door_name": "", "color": "STN Mercan"}
]"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        raw = response.content[0].text.strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            return JSONResponse({"error": f"Model ölçü listesi bulamadı. Ham yanıt: {raw[:400]}"}, status_code=422)
        doors = json.loads(raw[start:end])
        saved = []
        for d in doors:
            w = float(d.get("width_mm") or 0)
            h = float(d.get("height_mm") or 0)
            if w <= 0 or h <= 0:
                continue
            name = str(d.get("door_name") or "")
            color = str(d.get("color") or "")
            full_name = f"{name} - {color}".strip(" -") if (name or color) else ""
            fdb.save_membrane_door(
                project_name="", door_name=full_name,
                width_mm=w, height_mm=h,
                quantity=max(1, int(d.get("quantity") or 1)),
                list_id=lid,
            )
            saved.append({"width_mm": w, "height_mm": h,
                          "quantity": int(d.get("quantity") or 1),
                          "door_name": full_name, "color": color})
        return JSONResponse({"saved": saved, "count": len(saved)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Keep old routes for backward compatibility
@router.post("/door/save")
async def save_door_old(request: Request, id: int = Form(0),
                        project_name: str = Form(""), door_name: str = Form(""),
                        width_mm: float = Form(...), height_mm: float = Form(...),
                        quantity: int = Form(1)):
    auth.require_user(request)
    fdb.save_membrane_door(
        id=id or None, project_name=project_name, door_name=door_name,
        width_mm=width_mm, height_mm=height_mm, quantity=quantity,
    )
    return RedirectResponse("/membrane", 303)


@router.post("/door/delete")
async def delete_door_old(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_membrane_door(id)
    return RedirectResponse("/membrane", 303)


# ── Parametric Cap Models ─────────────────────────────────────────────────────

def _parse_dxf_file(data: bytes):
    """Parse DXF bytes → contours with moves + bounding box."""
    try:
        import ezdxf
        import io as _bio
    except ImportError:
        return {"error": "ezdxf kütüphanesi yüklü değil (pip install ezdxf)."}

    try:
        doc = ezdxf.read(_bio.BytesIO(data))
    except Exception as e:
        return {"error": f"DXF okuma hatası: {e}"}

    msp = doc.modelspace()
    layer_segs = {}

    def _add(layer, seg):
        layer_segs.setdefault(layer, []).append(seg)

    def _proc_line(layer, e):
        s, en = e.dxf.start, e.dxf.end
        _add(layer, {'type': 'line',
                     'x1': float(s.x), 'y1': float(s.y),
                     'x2': float(en.x), 'y2': float(en.y)})

    def _proc_arc(layer, e):
        cx, cy = float(e.dxf.center.x), float(e.dxf.center.y)
        r = float(e.dxf.radius)
        sa = _math.radians(float(e.dxf.start_angle))
        ea = _math.radians(float(e.dxf.end_angle))
        _add(layer, {'type': 'arc_ccw',
                     'x1': cx + r * _math.cos(sa), 'y1': cy + r * _math.sin(sa),
                     'x2': cx + r * _math.cos(ea), 'y2': cy + r * _math.sin(ea),
                     'cx': cx, 'cy': cy})

    def _proc_circle(layer, e):
        cx, cy = float(e.dxf.center.x), float(e.dxf.center.y)
        _add(layer, {'type': 'circle', 'cx': cx, 'cy': cy, 'r': float(e.dxf.radius)})

    for entity in msp:
        try:
            layer = entity.dxf.layer if entity.dxf.hasattr('layer') else '0'
            t = entity.dxftype()
            if t == 'LINE':
                _proc_line(layer, entity)
            elif t == 'ARC':
                _proc_arc(layer, entity)
            elif t == 'CIRCLE':
                _proc_circle(layer, entity)
            elif t in ('LWPOLYLINE', 'POLYLINE'):
                for sub in entity.virtual_entities():
                    st = sub.dxftype()
                    if st == 'LINE': _proc_line(layer, sub)
                    elif st == 'ARC': _proc_arc(layer, sub)
            elif t == 'SPLINE':
                pts = list(entity.flattening(0.5))
                for i in range(len(pts) - 1):
                    _add(layer, {'type': 'line',
                                 'x1': float(pts[i].x), 'y1': float(pts[i].y),
                                 'x2': float(pts[i + 1].x), 'y2': float(pts[i + 1].y)})
        except Exception:
            pass

    if not any(layer_segs.values()):
        return {"error": "DXF dosyasında çizilebilir varlık bulunamadı."}

    TOL = 0.05
    contours = []

    for layer, segs in layer_segs.items():
        circles = [s for s in segs if s['type'] == 'circle']
        edges = [s for s in segs if s['type'] != 'circle']

        for c in circles:
            cx, cy, r = c['cx'], c['cy'], c['r']
            pts = [(cx + r * _math.cos(_math.radians(a)), cy + r * _math.sin(_math.radians(a)))
                   for a in range(0, 361, 10)]
            moves = [
                {'move_type': 'start', 'x': str(round(cx + r, 3)), 'y': str(round(cy, 3))},
                {'move_type': 'arc_ccw', 'x': str(round(cx - r, 3)), 'y': str(round(cy, 3)),
                 'cx': str(round(cx, 3)), 'cy': str(round(cy, 3))},
                {'move_type': 'arc_ccw', 'x': str(round(cx + r, 3)), 'y': str(round(cy, 3)),
                 'cx': str(round(cx, 3)), 'cy': str(round(cy, 3))},
            ]
            contours.append({'layer': layer, 'moves': moves, 'preview_pts': pts, 'closed': True})

        remaining = list(edges)
        while remaining:
            chain = [remaining.pop(0)]
            grew = True
            while grew:
                grew = False
                tx, ty = chain[-1]['x2'], chain[-1]['y2']
                for i, seg in enumerate(remaining):
                    if abs(seg['x1'] - tx) < TOL and abs(seg['y1'] - ty) < TOL:
                        chain.append(remaining.pop(i)); grew = True; break
                    elif abs(seg['x2'] - tx) < TOL and abs(seg['y2'] - ty) < TOL:
                        rs = dict(seg, x1=seg['x2'], y1=seg['y2'], x2=seg['x1'], y2=seg['y1'])
                        if rs['type'] == 'arc_ccw': rs['type'] = 'arc_cw'
                        elif rs['type'] == 'arc_cw': rs['type'] = 'arc_ccw'
                        chain.append(rs); remaining.pop(i); grew = True; break

            hx, hy = chain[0]['x1'], chain[0]['y1']
            closed = abs(chain[-1]['x2'] - hx) < TOL and abs(chain[-1]['y2'] - hy) < TOL
            if len(chain) < 2 and not closed:
                continue

            moves = [{'move_type': 'start', 'x': str(round(hx, 3)), 'y': str(round(hy, 3))}]
            pts = [(hx, hy)]
            for seg in chain:
                mv = {'move_type': seg['type'],
                      'x': str(round(seg['x2'], 3)), 'y': str(round(seg['y2'], 3))}
                if seg['type'] in ('arc_cw', 'arc_ccw'):
                    mv['cx'] = str(round(seg['cx'], 3)); mv['cy'] = str(round(seg['cy'], 3))
                moves.append(mv)
                pts.append((seg['x2'], seg['y2']))
            contours.append({'layer': layer, 'moves': moves, 'preview_pts': pts, 'closed': closed})

    if not contours:
        return {"error": "Kontur zincirlenemedi."}

    all_x = [p[0] for c in contours for p in c['preview_pts']]
    all_y = [p[1] for c in contours for p in c['preview_pts']]
    min_x, min_y = min(all_x), min(all_y)
    max_x, max_y = max(all_x), max(all_y)
    W = round(max_x - min_x, 2)
    H = round(max_y - min_y, 2)

    for c in contours:
        c['preview_pts'] = [(round(x - min_x, 2), round(y - min_y, 2)) for x, y in c['preview_pts']]
        for m in c['moves']:
            if 'x' in m: m['x'] = str(round(float(m['x']) - min_x, 3))
            if 'y' in m: m['y'] = str(round(float(m['y']) - min_y, 3))
            if 'cx' in m: m['cx'] = str(round(float(m['cx']) - min_x, 3))
            if 'cy' in m: m['cy'] = str(round(float(m['cy']) - min_y, 3))
        xs = [p[0] for p in c['preview_pts']]
        ys = [p[1] for p in c['preview_pts']]
        c['bbox'] = {'x': min(xs), 'y': min(ys), 'w': max(xs) - min(xs), 'h': max(ys) - min(ys)}

    inner_kw = ['ic', 'inner', 'pocket', 'hole', 'cep', 'kanal', 'delik']
    outer_kw = ['dc', 'dis', 'outer', 'profil', 'kontur', 'profile', 'contour', 'frame']
    areas = [(c['bbox']['w'] * c['bbox']['h'], i) for i, c in enumerate(contours)]
    max_area_idx = max(areas, key=lambda a: a[0])[1] if areas else -1

    layers = sorted(set(c['layer'] for c in contours))
    for i, c in enumerate(contours):
        ll = c['layer'].lower()
        if any(k in ll for k in inner_kw):
            c['op_type'] = 'inner'
        elif any(k in ll for k in outer_kw):
            c['op_type'] = 'outer'
        elif i == max_area_idx:
            c['op_type'] = 'outer'
        else:
            c['op_type'] = 'inner'
        c['id'] = i
        c['name'] = (f"{c['layer']} {i + 1}" if c['layer'] != '0' else f"Op {i + 1}")

    return {'contours': contours, 'width': W, 'height': H, 'layers': layers}

@router.get("/caps")
async def caps_list(request: Request):
    user = auth.require_user(request)
    models = fdb.get_cap_models()
    return templates.TemplateResponse(request, "membrane_caps.html", {
        "user": user, "models": models, "active_page": "membrane",
        "edit_model": None, "paths": [],
        "msg": request.query_params.get("msg", ""),
        "msg_type": request.query_params.get("msg_type", "info"),
    })


@router.get("/caps/{mid}")
async def caps_edit(request: Request, mid: int):
    user = auth.require_user(request)
    model = fdb.get_cap_model(mid)
    if not model:
        return RedirectResponse("/membrane/caps", 303)
    paths = fdb.get_cap_paths(mid)
    models = fdb.get_cap_models()
    return templates.TemplateResponse(request, "membrane_caps.html", {
        "user": user, "models": models, "edit_model": model, "paths": paths,
        "active_page": "membrane",
        "msg": request.query_params.get("msg", ""),
        "msg_type": request.query_params.get("msg_type", "info"),
    })


@router.post("/caps/save")
async def caps_save(request: Request,
                    id: int = Form(0),
                    name: str = Form(...),
                    description: str = Form(""),
                    tool_no: int = Form(1),
                    spindle_speed: int = Form(18000),
                    feed_xy: int = Form(3000),
                    feed_z: int = Form(1000),
                    safe_z: float = Form(5.0),
                    constants_json: str = Form("{}")):
    auth.require_user(request)
    try:
        json.loads(constants_json or "{}")
    except Exception:
        constants_json = "{}"
    mid = fdb.save_cap_model(
        id=id or 0, name=name, description=description,
        tool_no=tool_no, spindle_speed=spindle_speed,
        feed_xy=feed_xy, feed_z=feed_z, safe_z=safe_z,
        constants_json=constants_json,
    )
    return RedirectResponse(f"/membrane/caps/{mid}?msg=Model+kaydedildi&msg_type=success", 303)


@router.post("/caps/delete")
async def caps_delete(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_cap_model(id)
    return RedirectResponse("/membrane/caps?msg=Model+silindi&msg_type=success", 303)


@router.get("/caps/tools")
async def tools_list_api(request: Request):
    auth.require_user(request)
    return JSONResponse(fdb.get_tools())

@router.post("/caps/tools/save")
async def tool_save(request: Request,
                    id: int = Form(0), name: str = Form(""),
                    tool_no: int = Form(1), diameter: float = Form(6.0),
                    length: float = Form(0), feed_xy: int = Form(3000),
                    feed_z: int = Form(1000), notes: str = Form("")):
    auth.require_user(request)
    tid = fdb.save_tool(id=id or 0, name=name, tool_no=tool_no,
                        diameter=diameter, length=length,
                        feed_xy=feed_xy, feed_z=feed_z, notes=notes)
    return JSONResponse({"id": tid, "ok": True, "tools": fdb.get_tools()})

@router.post("/caps/tools/delete")
async def tool_delete(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_tool(id)
    return JSONResponse({"ok": True})


@router.post("/caps/dxf_preview")
async def caps_dxf_preview(request: Request, file: UploadFile = File(...)):
    auth.require_user(request)
    data = await file.read()
    return JSONResponse(_parse_dxf_file(data))


@router.post("/caps/dxf_create")
async def caps_dxf_create(request: Request):
    auth.require_user(request)
    body = await request.json()
    mid = fdb.save_cap_model(
        id=0,
        name=body.get('name', 'DXF Model'),
        description=body.get('description', ''),
        tool_no=int(body.get('tool_no', 1)),
        spindle_speed=int(body.get('spindle_speed', 18000)),
        feed_xy=int(body.get('feed_xy', 3000)),
        feed_z=int(body.get('feed_z', 1000)),
        safe_z=float(body.get('safe_z', 5)),
        constants_json=body.get('constants_json', '{}'),
    )
    for op_data in body.get('ops', []):
        op_id = fdb.save_cap_op(
            id=0, model_id=mid,
            name=op_data.get('name', 'Op'),
            tool_no=int(op_data.get('tool_no', 1)),
            depth=str(op_data.get('depth', '-LPZ')),
            feed=str(op_data.get('feed', '')),
            ref_corner=op_data.get('ref_corner', 'BL'),
            seq=int(op_data.get('seq', 10)),
            op_type=op_data.get('op_type', 'inner'),
        )
        for seq_i, mv in enumerate(op_data.get('moves', []), 1):
            fdb.save_cap_move(
                id=0, op_id=op_id,
                move_type=mv.get('move_type', 'line'),
                x=str(mv.get('x', '0')),
                y=str(mv.get('y', '0')),
                cx=str(mv.get('cx', '')) if 'cx' in mv else '',
                cy=str(mv.get('cy', '')) if 'cy' in mv else '',
                seq=seq_i,
            )
    return JSONResponse({'ok': True, 'model_id': mid})


@router.post("/caps/{mid}/path/save")
async def cap_path_save(request: Request, mid: int,
                        id: int = Form(0),
                        seq: int = Form(0),
                        label: str = Form(""),
                        path_type: str = Form("LINE"),
                        x1: str = Form("0"), y1: str = Form("0"), z1: str = Form("0"),
                        x2: str = Form("LPX"), y2: str = Form("LPY"), z2: str = Form("-LPZ"),
                        ix: str = Form("0"), jy: str = Form("0"),
                        tool_dia: float = Form(8.0),
                        step_over: float = Form(0.5),
                        feed_override: str = Form(""),
                        tool_no: int = Form(0)):
    auth.require_user(request)
    fdb.save_cap_path(
        id=id or 0, model_id=mid, seq=seq, label=label, path_type=path_type,
        x1=x1, y1=y1, z1=z1, x2=x2, y2=y2, z2=z2,
        ix=ix, jy=jy, tool_dia=tool_dia, step_over=step_over, feed_override=feed_override,
        tool_no=tool_no,
    )
    return RedirectResponse(f"/membrane/caps/{mid}?msg=Yol+kaydedildi&msg_type=success", 303)


@router.post("/caps/{mid}/path/delete")
async def cap_path_delete(request: Request, mid: int, path_id: int = Form(...)):
    auth.require_user(request)
    fdb.del_cap_path(path_id)
    return RedirectResponse(f"/membrane/caps/{mid}?msg=Yol+silindi&msg_type=success", 303)


@router.post("/caps/{mid}/generate")
async def cap_generate(request: Request, mid: int,
                       W: float = Form(0), H: float = Form(0), T: float = Form(18.0),
                       extra_json: str = Form("{}")):
    auth.require_user(request)
    model = fdb.get_cap_model(mid)
    if not model:
        return JSONResponse({"error": "Model bulunamadı"}, status_code=404)
    paths = fdb.get_cap_paths(mid)
    variables = {"LPX": W, "LPY": H, "LPZ": T, "W": W, "H": H, "T": T}
    try:
        extra = json.loads(extra_json or "{}")
        variables.update({k: float(v) for k, v in extra.items()})
    except Exception:
        pass
    constants = model.get("constants") or {}
    variables.update({k: float(v) for k, v in constants.items()})
    ops = _sort_ops_inner_first(fdb.get_cap_ops(mid))
    if ops:
        nc = _generate_nc_ops(model, ops, variables)
        sim = _eval_ops(model, ops, variables)
    else:
        paths = fdb.get_cap_paths(mid)
        nc = _generate_nc(model, paths, variables)
        sim = _eval_paths(model, paths, variables)
    return JSONResponse({"nc": nc, "sim": sim, "LPX": W, "LPY": H, "LPZ": T})


@router.get("/caps/{mid}/download")
async def cap_download(request: Request, mid: int,
                       W: float = 0, H: float = 0, T: float = 18.0,
                       extra: str = "{}"):
    auth.require_user(request)
    model = fdb.get_cap_model(mid)
    if not model:
        return RedirectResponse("/membrane/caps", 303)
    variables = {"LPX": W, "LPY": H, "LPZ": T, "W": W, "H": H, "T": T}
    try:
        variables.update({k: float(v) for k, v in json.loads(extra).items()})
    except Exception:
        pass
    variables.update({k: float(v) for k, v in (model.get("constants") or {}).items()})
    ops = _sort_ops_inner_first(fdb.get_cap_ops(mid))
    if ops:
        nc = _generate_nc_ops(model, ops, variables)
    else:
        nc = _generate_nc(model, fdb.get_cap_paths(mid), variables)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in model["name"])
    filename = f"{safe_name}_W{int(W)}xH{int(H)}.nc"
    return Response(
        content=nc,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Cap Ops/Moves API ─────────────────────────────────────────────────────────

@router.get("/caps/{mid}/ops")
async def cap_ops_list(request: Request, mid: int):
    auth.require_user(request)
    return JSONResponse(fdb.get_cap_ops(mid))


@router.post("/caps/{mid}/op/save")
async def cap_op_save(request: Request, mid: int,
                      id: int = Form(0), name: str = Form(""),
                      tool_no: int = Form(1), tool_id: int = Form(0),
                      depth: str = Form("-LPZ"), feed: str = Form(""),
                      ref_corner: str = Form("BL"), seq: int = Form(0),
                      op_type: str = Form("inner"),
                      comp_mode: str = Form("none"),
                      offset_side: str = Form("center")):
    auth.require_user(request)
    op_id = fdb.save_cap_op(id=id or 0, model_id=mid, name=name,
                             tool_no=tool_no, tool_id=tool_id or None,
                             depth=depth, feed=feed, ref_corner=ref_corner,
                             seq=seq, op_type=op_type,
                             comp_mode=comp_mode, offset_side=offset_side)
    return JSONResponse({"id": op_id})


@router.post("/caps/op/{oid}/delete")
async def cap_op_delete(request: Request, oid: int):
    auth.require_user(request)
    fdb.del_cap_op(oid)
    return JSONResponse({"ok": True})


@router.post("/caps/op/{oid}/move/save")
async def cap_move_save(request: Request, oid: int,
                        id: int = Form(0), move_type: str = Form("line"),
                        x: str = Form("0"), y: str = Form("0"),
                        cx: str = Form("0"), cy: str = Form("0"),
                        r: str = Form("0"), seq: int = Form(0)):
    auth.require_user(request)
    mv_id = fdb.save_cap_move(id=id or 0, op_id=oid, move_type=move_type,
                               x=x, y=y, cx=cx, cy=cy, r=r, seq=seq)
    return JSONResponse({"id": mv_id})


@router.post("/caps/move/{mvid}/delete")
async def cap_move_delete(request: Request, mvid: int):
    auth.require_user(request)
    fdb.del_cap_move(mvid)
    return JSONResponse({"ok": True})


# ── Job List ──────────────────────────────────────────────────────────────────

@router.get("/jobs")
async def jobs_list(request: Request):
    user = auth.require_user(request)
    jobs = fdb.get_cap_jobs()
    models = fdb.get_cap_models()
    return templates.TemplateResponse(request, "membrane_jobs.html", {
        "user": user, "jobs": jobs, "models": models,
        "edit_job": None, "items": [],
        "active_page": "membrane",
        "msg": request.query_params.get("msg", ""),
        "msg_type": request.query_params.get("msg_type", "info"),
    })


@router.get("/jobs/{jid}")
async def job_detail(request: Request, jid: int):
    user = auth.require_user(request)
    job = fdb.get_cap_job(jid)
    if not job:
        return RedirectResponse("/membrane/jobs", 303)
    items = fdb.get_cap_job_items(jid)
    models = fdb.get_cap_models()
    return templates.TemplateResponse(request, "membrane_jobs.html", {
        "user": user, "edit_job": job, "items": items,
        "models": models, "jobs": fdb.get_cap_jobs(),
        "active_page": "membrane",
        "msg": request.query_params.get("msg", ""),
        "msg_type": request.query_params.get("msg_type", "info"),
    })


@router.post("/jobs/save")
async def job_save(request: Request,
                   id: int = Form(0), name: str = Form(...),
                   notes: str = Form(""),
                   sheet_w: float = Form(2800), sheet_h: float = Form(1100),
                   margin: float = Form(5)):
    auth.require_user(request)
    jid = fdb.save_cap_job(id=id or 0, name=name, notes=notes,
                           sheet_w=sheet_w, sheet_h=sheet_h, margin=margin)
    return RedirectResponse(f"/membrane/jobs/{jid}?msg=İş+listesi+kaydedildi&msg_type=success", 303)


@router.post("/jobs/delete")
async def job_delete(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_cap_job(id)
    return RedirectResponse("/membrane/jobs?msg=Silindi&msg_type=success", 303)


@router.post("/jobs/{jid}/item/save")
async def job_item_save(request: Request, jid: int,
                        id: int = Form(0),
                        model_id: int = Form(0),
                        model_name: str = Form(""),
                        cap_w: float = Form(...),
                        cap_h: float = Form(...),
                        qty: int = Form(1),
                        notes: str = Form(""),
                        seq: int = Form(0)):
    auth.require_user(request)
    # Auto-fill model_name from model if not given
    if model_id and not model_name:
        m = fdb.get_cap_model(model_id)
        if m:
            model_name = m["name"]
    fdb.save_cap_job_item(
        id=id or 0, job_id=jid, model_id=model_id or None,
        model_name=model_name, cap_w=cap_w, cap_h=cap_h,
        qty=qty, notes=notes, seq=seq,
    )
    return RedirectResponse(f"/membrane/jobs/{jid}?msg=Kalem+eklendi&msg_type=success", 303)


@router.post("/jobs/{jid}/item/delete")
async def job_item_delete(request: Request, jid: int, item_id: int = Form(...)):
    auth.require_user(request)
    fdb.del_cap_job_item(item_id)
    return RedirectResponse(f"/membrane/jobs/{jid}?msg=Silindi&msg_type=success", 303)


@router.post("/jobs/{jid}/nest")
async def job_nest(request: Request, jid: int,
                   sheet_w: float = Form(2800), sheet_h: float = Form(1100),
                   margin: float = Form(5), allow_rotate: int = Form(1)):
    auth.require_user(request)
    items = fdb.get_cap_job_items(jid)
    if not items:
        return JSONResponse({"error": "İş listesinde kalem yok"}, status_code=400)
    placements, n_sheets, util = _nest(items, sheet_w, sheet_h, margin, allow_rotate=bool(allow_rotate))
    return JSONResponse({
        "placements": placements,
        "sheet_count": n_sheets,
        "util_pct": util,
        "sheet_w": sheet_w,
        "sheet_h": sheet_h,
        "total_pieces": len(placements),
    })


@router.post("/jobs/{jid}/nest_nc")
async def job_nest_nc(request: Request, jid: int,
                      sheet_w: float = Form(2800), sheet_h: float = Form(1100),
                      margin: float = Form(5), T: float = Form(18),
                      allow_rotate: int = Form(1)):
    """Generate NC code + simulation data for all nested pieces."""
    auth.require_user(request)
    job = fdb.get_cap_job(jid)
    if not job:
        return JSONResponse({"error": "İş listesi bulunamadı"}, status_code=404)
    items = fdb.get_cap_job_items(jid)
    if not items:
        return JSONResponse({"error": "İş listesinde kalem yok"}, status_code=400)

    placements, n_sheets, util = _nest(items, sheet_w, sheet_h, margin, allow_rotate=bool(allow_rotate))
    safe_z = 5.0
    prog_no = 1

    # Build per-placement context (model, ops, variables) once
    pl_ctx = []
    for pl in placements:
        mid = pl.get('model_id')
        if not mid:
            pl_ctx.append(None); continue
        model = fdb.get_cap_model(mid)
        if not model:
            pl_ctx.append(None); continue
        safe_z = float(model.get("safe_z") or 5.0)
        W, H = pl['cap_w'], pl['cap_h']
        variables = {"LPX": W, "LPY": H, "LPZ": T, "W": W, "H": H, "T": T}
        variables.update({k: float(v) for k, v in (model.get("constants") or {}).items()})
        if pl.get('rotated'):
            variables["LPX"], variables["LPY"] = H, W
            variables["W"],   variables["H"]   = H, W
        all_ops = fdb.get_cap_ops(mid)
        paths = [] if all_ops else fdb.get_cap_paths(mid)
        pl_ctx.append({"model": model, "ops": all_ops, "paths": paths,
                       "variables": variables, "pl": pl})

    # Two-pass NC: inner ops for all pieces first, then outer ops
    # (pieces stay attached to sheet during inner cuts, released last)
    nc_inner, nc_outer = [], []
    sim_inner_paths, sim_outer_paths = [], []

    for ctx in pl_ctx:
        if not ctx:
            continue
        model, all_ops, paths = ctx["model"], ctx["ops"], ctx["paths"]
        variables, pl = ctx["variables"], ctx["pl"]
        x_off, y_off = pl['x'], pl['y']

        if all_ops:
            explicit_outer = [o for o in all_ops if o.get('op_type') == 'outer']
            if explicit_outer:
                inner_ops = [o for o in all_ops if o.get('op_type') != 'outer']
                outer_ops = explicit_outer
            elif len(all_ops) >= 2:
                by_seq = sorted(all_ops, key=lambda o: o.get('seq', 0))
                inner_ops = by_seq[:-1]
                outer_ops = by_seq[-1:]
            else:
                # Single op: split at last START move for inner/outer separation
                inner_op_split, outer_op_split = _split_op_at_last_start(all_ops[0])
                if outer_op_split:
                    inner_ops = [inner_op_split]
                    outer_ops = [outer_op_split]
                else:
                    inner_ops = all_ops
                    outer_ops = []
            if inner_ops:
                nc_inner.append(_generate_nc_ops(model, sorted(inner_ops, key=lambda o: o.get('seq',0)),
                                                 variables, x_off=x_off, y_off=y_off, prog_no=prog_no))
                evp = _eval_ops(model, inner_ops, variables, x_off=x_off, y_off=y_off)
                for p in evp['paths']:
                    p['sheet'] = pl['sheet']; p['piece_color'] = pl['color']
                sim_inner_paths.extend(evp['paths'])
            if outer_ops:
                nc_outer.append(_generate_nc_ops(model, sorted(outer_ops, key=lambda o: o.get('seq',0)),
                                                 variables, x_off=x_off, y_off=y_off, prog_no=prog_no))
                evp = _eval_ops(model, outer_ops, variables, x_off=x_off, y_off=y_off)
                for p in evp['paths']:
                    p['sheet'] = pl['sheet']; p['piece_color'] = pl['color']
                sim_outer_paths.extend(evp['paths'])
        else:
            nc_inner.append(_generate_nc(model, paths, variables, x_off=x_off, y_off=y_off, prog_no=prog_no))
            evp = _eval_paths(model, paths, variables, x_off=x_off, y_off=y_off)
            for p in evp['paths']:
                p['sheet'] = pl['sheet']; p['piece_color'] = pl['color']
            sim_inner_paths.extend(evp['paths'])
        prog_no += 1

    sim_paths = sim_inner_paths + sim_outer_paths
    nc_parts = nc_inner + nc_outer

    return JSONResponse({
        "nc": "\n\n".join(nc_parts),
        "sim": {"paths": sim_paths, "safe_z": safe_z},
        "placements": placements,
        "sheet_count": n_sheets,
        "util_pct": util,
        "sheet_w": sheet_w,
        "sheet_h": sheet_h,
        "total_pieces": len(placements),
    })


@router.get("/jobs/{jid}/nc")
async def job_nc_download(request: Request, jid: int,
                          sheet_w: float = 2800, sheet_h: float = 1100,
                          margin: float = 5, T: float = 18,
                          allow_rotate: int = 1):
    """Download combined NC file — same 2-pass logic as nest_nc."""
    auth.require_user(request)
    job = fdb.get_cap_job(jid)
    if not job:
        return RedirectResponse("/membrane/jobs", 303)
    items = fdb.get_cap_job_items(jid)
    placements, n_sheets, _ = _nest(items, sheet_w, sheet_h, margin, allow_rotate=bool(allow_rotate))

    nc_inner, nc_outer = [], []
    prog_no = 1
    for pl in placements:
        mid = pl.get('model_id')
        if not mid: continue
        model = fdb.get_cap_model(mid)
        if not model: continue
        W, H = pl['cap_w'], pl['cap_h']
        variables = {"LPX": W, "LPY": H, "LPZ": T, "W": W, "H": H, "T": T}
        variables.update({k: float(v) for k, v in (model.get("constants") or {}).items()})
        if pl.get('rotated'):
            variables["LPX"], variables["LPY"] = H, W
            variables["W"],   variables["H"]   = H, W
        x_off, y_off = pl['x'], pl['y']
        all_ops = fdb.get_cap_ops(mid)
        if all_ops:
            explicit_outer = [o for o in all_ops if o.get('op_type') == 'outer']
            if explicit_outer:
                inner_ops = [o for o in all_ops if o.get('op_type') != 'outer']
                outer_ops = explicit_outer
            elif len(all_ops) >= 2:
                by_seq = sorted(all_ops, key=lambda o: o.get('seq', 0))
                inner_ops, outer_ops = by_seq[:-1], by_seq[-1:]
            else:
                inner_op_split, outer_op_split = _split_op_at_last_start(all_ops[0])
                if outer_op_split:
                    inner_ops = [inner_op_split]
                    outer_ops = [outer_op_split]
                else:
                    inner_ops, outer_ops = all_ops, []
            if inner_ops:
                nc_inner.append(_generate_nc_ops(model, sorted(inner_ops, key=lambda o: o.get('seq',0)),
                                                 variables, x_off=x_off, y_off=y_off, prog_no=prog_no))
            if outer_ops:
                nc_outer.append(_generate_nc_ops(model, sorted(outer_ops, key=lambda o: o.get('seq',0)),
                                                 variables, x_off=x_off, y_off=y_off, prog_no=prog_no))
        else:
            paths = fdb.get_cap_paths(mid)
            nc_inner.append(_generate_nc(model, paths, variables,
                                         x_off=x_off, y_off=y_off, prog_no=prog_no))
        prog_no += 1

    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in job["name"])
    content = "\n\n".join(nc_inner + nc_outer)
    return Response(
        content=content, media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{safe}_nested.nc"'},
    )
