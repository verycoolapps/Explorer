# =============================================================================
# © 2026 VeryCoolApps — PT. Agra Karya Digital
# ALL RIGHTS RESERVED — PROPRIETARY & CONFIDENTIAL
# =============================================================================
# Product   : EXPLORER — Blender Interactive World Exploration Engine
# Version   : 1.0.0
# Author    : VeryCoolApps / PT. Agra Karya Digital
# Contact   : WA +62 815-1925-0845 | Telegram: t.me/VeryCoolApps
# Website   : https://t.me/VeryCoolApps
# =============================================================================
# LICENSE NOTICE:
# This file is the exclusive intellectual property of VeryCoolApps
# (PT. Agra Karya Digital). Reproduction, distribution, modification,
# reverse engineering, or any unauthorized use — in whole or in part —
# is strictly prohibited without prior written consent. Violations are
# subject to civil and criminal prosecution under Indonesian Law No.
# 28/2014 on Copyright and applicable international IP treaties.
#
# PROHIBITED: Copy · Redistribution · Modify · Decompile · Sublicense
# FOR LICENSING: wa.me/6281519250845
# =============================================================================

"""HUD draw callback: title, status, location, crosshair, prompts, menu."""

import blf
import gpu
from gpu_extras.batch import batch_for_shader


def draw_callback(engine, region):
    """SpaceView3D draw_handler_add callback args=(engine, region)."""
    try:
        _draw(engine, region)
    except Exception:
        pass


def _draw(engine, region):
    s = engine.settings
    state = engine.player_state
    width = region.width
    height = region.height

    # ---------- menu (drawn instead of HUD)
    if engine.menu_open:
        _fill_rect(0, 0, width, height, (0.01, 0.01, 0.02, 0.55))
        _draw_menu(engine, width, height)
        return

    # ---------- top-left title + status
    blf.size(0, 18)
    blf.position(0, height - 24, 14)
    blf.draw(0, "EXPLORER")
    blf.size(0, 12)
    y = height - 42
    mode = "FP" if s.camera_mode == "FP" else "TP"
    if engine.manual_pause:
        mode += " | PAUSED"
    flags = []
    if state.crouching:
        flags.append("CROUCH")
    if "SHIFT" in state.keys:
        flags.append("RUN")
    blf.position(0, y, 14)
    blf.draw(0, "%s | %.0f fps %s" % (mode, engine.fps, " ".join(flags)))
    y -= 16
    # location line
    loc = engine.location_cache
    parts = [p for p in (loc.get("area"), loc.get("floor"), loc.get("room")) if p]
    blf.position(0, y, 14)
    blf.draw(0, " / ".join(parts) if parts else "Unknown")
    y -= 16
    p = state.pos
    blf.position(0, y, 14)
    blf.draw(0, "XYZ  %.2f  %.2f  %.2f" % (p.x, p.y, p.z))

    # ---------- center crosshair
    cx, cy = width // 2, height // 2
    blf.size(0, 16)
    blf.position(0, cy - 6, cx - 4)
    blf.draw(0, "+")

    # ---------- interact prompt
    if engine.focus is not None and not engine.info_popup:
        obj = engine.focus["obj"]
        label = "Open" if obj.get("explorer_door") else "Inspect"
        text = "[%s] %s — %s" % ("E", label, obj.name)
        blf.size(0, 13)
        tw = blf.dimensions(0, text)[0]
        blf.position(0, 60, (width - tw) // 2)
        blf.draw(0, text)

    # ---------- info popup
    if engine.info_popup and engine.time < engine.info_popup["until"]:
        _draw_info_popup(engine, width, height)

    # ---------- toast
    if engine.toast_msg and engine.time < engine.toast_until:
        text = engine.toast_msg
        blf.size(0, 14)
        tw = blf.dimensions(0, text)[0]
        blf.position(0, height - 70, (width - tw) // 2)
        blf.draw(0, text)

    # ---------- watermark (bottom-right, subtle)
    credit = "© 2026 VeryCoolApps · PT. Agra Karya Digital"
    blf.size(0, 10)
    tw = blf.dimensions(0, credit)[0]
    blf.position(0, 8, width - tw - 10)
    blf.draw(0, credit)


def _draw_info_popup(engine, width, height):
    info = engine.info_popup
    lines = [
        info["name"],
        "%s  %s" % (info["type"], info["dimensions"] or ""),
        "Materials: %s" % info["materials"],
        "",
        info["info"],
    ]
    blf.size(0, 12)
    line_h = 16
    box_h = line_h * len(lines) + 16
    box_w = max(blf.dimensions(0, l)[0] for l in lines) + 24
    x = (width - box_w) / 2
    y = height - 140 - box_h
    _fill_rect(x, y, box_w, box_h, (0.05, 0.05, 0.07, 0.85))
    ty = y + box_h - 20
    for line in lines:
        blf.position(0, ty, x + 12)
        blf.draw(0, line)
        ty -= line_h


def _draw_menu(engine, width, height):
    items = engine.menu_items
    if not items:
        return
    sel = engine.menu_index
    box_w = 340
    box_h = 60 + len(items) * 22
    x = (width - box_w) / 2
    y = height * 0.5 - box_h / 2
    _fill_rect(x, y, box_w, box_h, (0.04, 0.05, 0.08, 0.92))

    blf.size(0, 16)
    blf.position(0, y + box_h - 28, x + 16)
    blf.draw(0, "EXPLORER")

    blf.size(0, 13)
    iy = y + box_h - 52
    for i, item in enumerate(items):
        prefix = "> " if i == sel else "   "
        text = prefix + item["label"]
        if i == sel:
            blf.position(0, iy, x + 16)
        else:
            blf.position(0, iy, x + 20)
        blf.draw(0, text)
        iy -= 22

    blf.size(0, 11)
    blf.position(0, y + 10, x + 16)
    blf.draw(0, "W/S navigate · Enter select · Esc/Tab back · P pause · Esc exit")


def _fill_rect(x, y, w, h, color):
    """Draw a filled rect in region pixel coords via gpu (POST_PIXEL)."""
    try:
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        shader.bind()
        gpu.state.blend_set("ALPHA")
        # viewport size for NDC conversion
        vw, vh = gpu.state.viewport_get()[2], gpu.state.viewport_get()[3]
        if vw <= 0 or vh <= 0:
            gpu.state.blend_set("NONE")
            return
        x0 = x / vw * 2 - 1
        x1 = (x + w) / vw * 2 - 1
        # gpu NDC y is up; blf y is up too in POST_PIXEL? blf origin bottom-left.
        y0 = y / vh * 2 - 1
        y1 = (y + h) / vh * 2 - 1
        verts = [
            (x0, y0, 0), (x1, y0, 0), (x1, y1, 0),
            (x0, y0, 0), (x1, y1, 0), (x0, y1, 0),
        ]
        batch = batch_for_shader(shader, "TRIS", {"pos": verts})
        shader.uniform_float("color", color)
        batch.draw(shader)
        gpu.state.blend_set("NONE")
    except Exception:
        pass
