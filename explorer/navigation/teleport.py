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

"""Teleport targets and execution."""

import bpy
from mathutils import Vector

TEMP_PREFIX = "EXPLORER_"


def collect_targets(engine):
    """Return list of dicts {label, pos, yaw} for teleport destinations."""
    targets = []
    # spawn
    spawn_obj = bpy.data.objects.get("EXPLORER_SPAWN")
    if spawn_obj is not None:
        targets.append(
            {
                "label": "Spawn",
                "pos": spawn_obj.matrix_world.translation.copy(),
                "yaw": -spawn_obj.matrix_world.to_euler().z,
            }
        )
    # objects marked explorer_teleport
    for obj in bpy.context.scene.objects:
        if obj.name.startswith(TEMP_PREFIX):
            continue
        val = obj.get("explorer_teleport")
        if val:
            label = obj.get("explorer_teleport_label") or (str(val) if isinstance(val, str) else obj.name)
            targets.append(
                {
                    "label": label,
                    "pos": obj.matrix_world.translation.copy(),
                    "yaw": engine.player_state.yaw,
                }
            )
    # saved positions on engine
    for i, sp in enumerate(getattr(engine, "saved_positions", [])):
        targets.append({"label": sp.get("label", "Saved %d" % (i + 1)), "pos": Vector(sp["pos"]), "yaw": sp.get("yaw", engine.player_state.yaw)})
    return targets


def try_teleport(engine, pos, yaw=None, reset_view=False):
    """Teleport player feet to pos (resolved to ground). Returns True on success."""
    s = engine.settings
    # find ground below pos + small lift
    probe = pos + Vector((0, 0, 1.2))
    hit = engine.collision.raycast(probe, Vector((0, 0, -1)), 4.5, kinds={"solid", "walkable"})
    if hit is not None:
        feet = Vector((pos.x, pos.y, hit["loc"].z + 0.03))
    else:
        feet = Vector((pos.x, pos.y, pos.z))
    # capsule check with lifts
    ok = None
    for lift in (0.0, 0.2, 0.5, 1.0):
        cand = feet + Vector((0, 0, lift))
        g = engine.collision.raycast(cand + Vector((0, 0, 0.05)), Vector((0, 0, -1)), 1.5, kinds={"solid", "walkable"})
        if g is not None:
            feet = Vector((cand.x, cand.y, cand.z - g["dist"] + 0.03))
            if engine.physics.capsule_free(feet, s.player_height):
                ok = feet
                break
        elif engine.physics.capsule_free(cand, s.player_height):
            ok = cand
            break
    if ok is None:
        engine.toast("Teleport blocked", 2.5)
        return False
    state = engine.player_state
    state.pos = ok
    state.vel = Vector((0, 0, 0))
    state.grounded = True
    if yaw is not None:
        state.yaw = yaw
    if reset_view:
        state.pitch = 0.0
    engine.collision.update_focus(ok, 6.0)
    engine.toast("Teleported", 1.5)
    return True
