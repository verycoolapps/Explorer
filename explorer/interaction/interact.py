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

"""Interaction: focus raycast, door toggle, info popup."""

import math

from mathutils import Vector, Quaternion

TEMP_PREFIX = "EXPLORER_"


def update_focus(engine):
    """Each tick: raycast from camera forward for interactive objects."""
    engine.focus = None
    if engine.menu_open or engine.info_popup:
        return
    origin = engine.physics.state.eye_pos(engine.settings)
    direction = engine.forward_vec()
    dist = engine.settings.interact_distance
    # cast a few rays with slight spread to be forgiving
    for spread in (0.0, 0.06, -0.06):
        d = direction.copy()
        if spread:
            d.rotate(Quaternion(Vector((0, 0, 1)), spread))
        hit = engine.collision.raycast(origin, d, dist, kinds={"solid", "walkable"})
        if hit is None:
            continue
        obj = hit["obj"]
        if obj.name.startswith(TEMP_PREFIX):
            continue
        if _is_interactive(obj):
            engine.focus = {"obj": obj, "hit": hit}
            return
    return


def _is_interactive(obj):
    return bool(obj.get("explorer_info") or obj.get("explorer_door") or obj.get("explorer_interact"))


def try_interact(engine):
    """E key handler: door toggle or info popup."""
    focus = engine.focus
    if focus is None:
        return
    obj = focus["obj"]
    if obj.get("explorer_door"):
        toggle_door(engine, obj)
    else:
        show_info(engine, obj)


def toggle_door(engine, obj):
    """Rotate door around its local axis; rebuild collision after."""
    door_backup = engine.door_backup
    if obj.name not in door_backup:
        door_backup[obj.name] = {
            "rotation_mode": obj.rotation_mode,
            "rotation_euler": obj.rotation_euler.copy(),
            "rotation_quaternion": obj.rotation_quaternion.copy(),
        }
        obj.rotation_mode = "QUATERNION"

    axis_name = str(obj.get("explorer_door_axis", "Z")).upper()
    axis_map = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}
    axis_local = axis_map.get(axis_name, Vector((0, 0, 1)))
    angle_deg = float(obj.get("explorer_door_angle", 100.0))

    # determine current open state by checking a custom prop
    is_open = bool(obj.get("_explorer_door_open"))
    target_angle = math.radians(angle_deg) if not is_open else 0.0

    backup = door_backup[obj.name]
    base_quat = backup["rotation_quaternion"]
    delta = Quaternion(axis_local, target_angle)
    obj.rotation_quaternion = base_quat @ delta
    obj["_explorer_door_open"] = not is_open

    engine.collision.rebuild_one(obj)
    engine.toast(("Opened" if not is_open else "Closed") + " — " + obj.name, 1.8)


def restore_doors(engine):
    for name, backup in engine.door_backup.items():
        obj = engine.scene.objects.get(name)
        if obj is None:
            continue
        try:
            obj.rotation_mode = backup["rotation_mode"]
            obj.rotation_euler = backup["rotation_euler"]
            obj.rotation_quaternion = backup["rotation_quaternion"]
            obj["_explorer_door_open"] = False
        except Exception:
            pass
    engine.door_backup = {}


def show_info(engine, obj):
    dims = ""
    if obj.type == "MESH" and obj.data is not None:
        bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        size = Vector((max(v.x for v in bb) - min(v.x for v in bb),
                       max(v.y for v in bb) - min(v.y for v in bb),
                       max(v.z for v in bb) - min(v.z for v in bb)))
        dims = "%.1f × %.1f × %.1f m" % (size.x, size.y, size.z)
    mats = ", ".join(m.name for m in getattr(obj.data, "materials", []) if m) or "—"
    engine.info_popup = {
        "name": obj.name,
        "type": obj.type,
        "dimensions": dims,
        "materials": mats,
        "info": obj.get("explorer_info") or "—",
        "until": engine.time + 6.0,
    }
