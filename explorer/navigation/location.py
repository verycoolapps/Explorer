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

"""Location resolver: area / floor / room from props and collections."""

import re

from mathutils import Vector

TEMP_PREFIX = "EXPLORER_"
_FLOOR_RE = re.compile(r"(floor|level|lvl|storey|etage|piso|deck)", re.IGNORECASE)
_GENERIC = {"collection", "collection 1", "collection 2", "master collection", "scene collection"}


def _prop_walk(obj):
    """Walk object -> parents -> collections; return first explorer_floor/explorer_room."""
    floor = obj.get("explorer_floor") if obj else None
    room = obj.get("explorer_room") if obj else None
    if floor or room:
        return floor, room
    node = obj
    while node is not None:
        for coll in getattr(node, "users_collection", []):
            f = coll.get("explorer_floor")
            r = coll.get("explorer_room")
            if f or r:
                return f, r
        node = getattr(node, "parent", None)
    return None, None


def _floor_from_name(name):
    if not name:
        return None
    return name if _FLOOR_RE.search(name) else None


def resolve(engine, pos):
    """Return dict {area, floor, room} for world position."""
    hit = engine.collision.raycast(pos + Vector((0, 0, 0.1)), Vector((0, 0, -1)), 3.5, kinds={"solid", "walkable"})
    obj = hit["obj"] if hit else None
    area = floor = room = None
    if obj is not None:
        f, r = _prop_walk(obj)
        floor = f
        room = r or obj.name
        # area: first non-generic collection name else object name
        colls = list(obj.users_collection)
        for coll in colls:
            if coll.name.lower() not in _GENERIC:
                area = coll.name
                break
        if area is None:
            area = obj.name
        if floor is None:
            for coll in colls:
                floor = _floor_from_name(coll.name)
                if floor:
                    break
    if floor is None:
        floor = _floor_from_name(obj.name) if obj else None
    if floor is None:
        floor = _floor_from_name(area) or _floor_from_name(room)
    return {"area": area, "floor": floor, "room": room}
