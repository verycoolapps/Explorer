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

"""Build a deterministic two-story test house for EXPLORER."""

import bpy
from mathutils import Vector

PREFIX = "TESTHOUSE_"


def _cube(name, loc, scale, collection=None):
    """Create a cube, apply scale, name it, optionally link to collection."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if collection is not None:
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        collection.objects.link(obj)
    return obj


def _empty(name, loc, collection=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.3
    obj.location = loc
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def _delete_prior():
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX) or obj.name == "EXPLORER_SPAWN":
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception:
                pass


def build_test_house(context):
    """Build a ~10x8m two-story house with stairs, door, furniture, teleports."""
    scene = context.scene
    _delete_prior()

    coll = bpy.data.collections.new(PREFIX + "House")
    scene.collection.children.link(coll)

    WALL_T = 0.15
    H1 = 3.0   # ground floor height
    H2 = 2.8   # second floor height
    W, D = 10.0, 8.0

    # ---------- ground slab (house floor)
    _cube(PREFIX + "GroundSlab", (0, 0, -0.1), (W + 1, D + 1, 0.2), coll)

    # ---------- exterior ground plane (large, walkable)
    ground = _cube(PREFIX + "ExteriorGround", (0, 0, -0.15), (60, 60, 0.1), coll)
    ground["explorer_collision"] = "walkable"
    # back wall
    _cube(PREFIX + "WallBack", (0, D / 2 - WALL_T / 2, H1 / 2), (W, WALL_T, H1), coll)
    # left wall
    _cube(PREFIX + "WallLeft", (-W / 2 + WALL_T / 2, 0, H1 / 2), (WALL_T, D, H1), coll)
    # right wall
    _cube(PREFIX + "WallRight", (W / 2 - WALL_T / 2, 0, H1 / 2), (WALL_T, D, H1), coll)
    # front wall with doorway gap (door at x=0, width 1.2)
    door_w = 1.2
    seg_w = (W - door_w) / 2
    _cube(PREFIX + "WallFrontL", (-(door_w / 2 + seg_w / 2), -D / 2 + WALL_T / 2, H1 / 2), (seg_w, WALL_T, H1), coll)
    _cube(PREFIX + "WallFrontR", (door_w / 2 + seg_w / 2, -D / 2 + WALL_T / 2, H1 / 2), (seg_w, WALL_T, H1), coll)
    # lintel above door
    _cube(PREFIX + "WallFrontTop", (0, -D / 2 + WALL_T / 2, H1 - 0.4), (door_w, WALL_T, 0.8), coll)

    # ---------- interior partition (vertical wall splitting ground floor)
    _cube(PREFIX + "Partition", (-2.0, 0, H1 / 2), (WALL_T, D - 0.4, H1), coll)

    # ---------- stairs to second floor (along right wall)
    # 20 steps, 0.15m riser, 0.4m tread -> gentle climbable staircase
    step_count = 20
    step_w = 1.0
    step_d = 0.4
    stair_run = step_count * step_d          # 8.0m run
    stair_x = W / 2 - step_w / 2 - 0.3
    stair_y0 = -stair_run / 2               # centered, starts at y=-4
    for i in range(step_count):
        top_z = (i + 1) * (H1 / step_count)  # 0.15, 0.30, ... 3.0
        y = stair_y0 + i * step_d + step_d / 2
        zc = top_z - 0.075                    # box center (0.15 thick)
        _cube(PREFIX + "Step%02d" % i, (stair_x, y, zc), (step_w, step_d, 0.15), coll)

    # ---------- second floor slab
    _cube(PREFIX + "Floor2", (0, 0, H1 + 0.1), (W, D, 0.2), coll)

    # ---------- second floor walls ----------
    _cube(PREFIX + "Wall2Back", (0, D / 2 - WALL_T / 2, H1 + H2 / 2 + 0.1), (W, WALL_T, H2), coll)
    _cube(PREFIX + "Wall2Left", (-W / 2 + WALL_T / 2, 0, H1 + H2 / 2 + 0.1), (WALL_T, D, H2), coll)
    _cube(PREFIX + "Wall2Right", (W / 2 - WALL_T / 2, 0, H1 + H2 / 2 + 0.1), (WALL_T, D, H2), coll)
    _cube(PREFIX + "Wall2Front", (0, -D / 2 + WALL_T / 2, H1 + H2 / 2 + 0.1), (W, WALL_T, H2), coll)

    # ---------- roof slab
    _cube(PREFIX + "Roof", (0, 0, H1 + H2 + 0.2), (W + 0.4, D + 0.4, 0.2), coll)

    # ---------- door (thin box in doorway) ----------
    door = _cube(PREFIX + "Door", (0, -D / 2 + WALL_T / 2, 1.05), (door_w - 0.05, 0.08, 2.1), coll)
    door["explorer_door"] = True
    door["explorer_door_axis"] = "Z"
    door["explorer_door_angle"] = 100.0

    # ---------- furniture ----------
    table = _cube(PREFIX + "Table", (-3.0, -2.0, 0.4), (1.6, 0.9, 0.8), coll)
    table["explorer_info"] = "A wooden table. It creaks when you walk past."
    _cube(PREFIX + "Chair1", (-3.0, -2.6, 0.25), (0.45, 0.45, 0.5), coll)
    _cube(PREFIX + "Chair2", (-3.0, -1.4, 0.25), (0.45, 0.45, 0.5), coll)
    _cube(PREFIX + "Shelf", (3.5, 2.5, 1.0), (1.2, 0.4, 2.0), coll)
    bed = _cube(PREFIX + "Bed", (3.0, 0.5, H1 + 0.45), (2.0, 1.2, 0.5), coll)
    bed["explorer_info"] = "A cozy bed on the second floor."
    _cube(PREFIX + "Desk2", (-3.5, 2.5, H1 + 0.4), (1.4, 0.7, 0.8), coll)

    # ---------- spawn empty outside front ----------
    spawn = _empty("EXPLORER_SPAWN", (0, -D / 2 - 1.5, 0.1), coll)
    spawn.rotation_euler.z = 0.0  # facing -Y into the house? forward is -Y when yaw=0

    # ---------- teleport targets ----------
    tp1 = _empty(PREFIX + "TP_Entrance", (0, -D / 2 - 1.0, 0.1), coll)
    tp1["explorer_teleport"] = "Entrance"
    tp1["explorer_teleport_label"] = "Entrance"

    tp2 = _empty(PREFIX + "TP_Rooftop", (0, 0, H1 + H2 + 0.4), coll)
    tp2["explorer_teleport"] = "Rooftop"
    tp2["explorer_teleport_label"] = "Rooftop"

    # mark floor names for location display
    coll["explorer_floor"] = "Test House"
    coll["explorer_room"] = "Main"

    return {"objects": len(scene.objects), "collection": coll}
