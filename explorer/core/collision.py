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
# PROHIBITED: Copy · Redistribute · Modify · Decompile · Sublicense
# FOR LICENSING: wa.me/6281519250845
# =============================================================================

"""Collision world: per-object BVH broad+narrowphase raycasts."""

from mathutils import Vector
from mathutils.bvhtree import BVHTree

import bpy
from bpy.types import Scene

_TEMP_PREFIX = "EXPLORER_"


class CollisionWorld:
    def __init__(self):
        self.entries = []          # [{obj, bvh, center, radius, name, kinds:set}]
        self.active = []           # entries near the focus point
        self._fingerprint = None
        self._last_refresh_check = 0.0

    # ------------------------------------------------------------------ build
    def rebuild(self, scene: Scene):
        self.entries = []
        self._build_entry_list(scene)
        self._fingerprint = self._compute_fingerprint()

    def _build_entry_list(self, scene):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for obj in scene.objects:
            if obj.name.startswith(_TEMP_PREFIX):
                continue
            if obj.type != "MESH" or obj.hide_get():
                continue
            try:
                eval_obj = obj.evaluated_get(depsgraph)
                mesh = eval_obj.to_mesh()
                if mesh is None or len(mesh.vertices) == 0:
                    eval_obj.to_mesh_clear()
                    continue
                verts = [eval_obj.matrix_world @ v.co for v in mesh.vertices]
                polys = [p.vertices for p in mesh.polygons]
                bvh = BVHTree.FromPolygons(verts, polys)
                eval_obj.to_mesh_clear()
            except Exception:
                continue
            kinds = self._kinds_for(obj)
            if not kinds:
                continue
            center, radius = _bounding_sphere(verts)
            self.entries.append(
                {
                    "obj": obj,
                    "bvh": bvh,
                    "center": center,
                    "radius": radius,
                    "name": obj.name,
                    "kinds": kinds,
                }
            )
        self.active = list(self.entries)

    def rebuild_one(self, obj):
        """Rebuild the BVH entry for a single object (e.g. after a door toggles)."""
        for entry in self.entries:
            if entry["obj"] == obj:
                self.entries.remove(entry)
                break
        if obj.type == "MESH" and not obj.hide_get():
            try:
                depsgraph = bpy.context.evaluated_depsgraph_get()
                eval_obj = obj.evaluated_get(depsgraph)
                mesh = eval_obj.to_mesh()
                if mesh is not None and len(mesh.vertices):
                    verts = [eval_obj.matrix_world @ v.co for v in mesh.vertices]
                    polys = [p.vertices for p in mesh.polygons]
                    bvh = BVHTree.FromPolygons(verts, polys)
                    eval_obj.to_mesh_clear()
                    kinds = self._kinds_for(obj)
                    if kinds:
                        center, radius = _bounding_sphere(verts)
                        self.entries.append(
                            {
                                "obj": obj,
                                "bvh": bvh,
                                "center": center,
                                "radius": radius,
                                "name": obj.name,
                                "kinds": kinds,
                            }
                        )
            except Exception:
                pass

    @staticmethod
    def _kinds_for(obj) -> set:
        """Resolve collision category: 'solid', 'walkable' or 'none'."""
        node = obj
        value = None
        while node is not None:
            value = node.get("explorer_collision")
            if value is not None:
                break
            coll = getattr(node, "users_collection", None)
            if coll:
                for c in coll:
                    value = c.get("explorer_collision")
                    if value is not None:
                        break
            if value is not None:
                break
            node = getattr(node, "parent", None)
        if value is None:
            value = "solid"
        value = str(value).lower()
        if value in ("solid", "walkable", "none"):
            return {"solid"} if value == "solid" else ({"walkable"} if value == "walkable" else set())
        return {"solid"}

    # -------------------------------------------------------------- broadphase
    def update_focus(self, pos, radius=4.0):
        """Keep only entries whose bounding sphere intersects the neighborhood."""
        active = []
        for entry in self.entries:
            dist = (entry["center"] - pos).length
            if dist <= entry["radius"] + radius + 2.0:
                active.append(entry)
        self.active = active

    # --------------------------------------------------------------- raycasts
    def raycast(self, origin, direction, max_dist=1e6, kinds=None):
        """Nearest hit among active entries. kinds: subset of {'solid','walkable'}.

        Returns dict(loc, normal, obj, dist, entry) or None.
        """
        if kinds is None:
            kinds = {"solid"}
        origin = Vector(origin)
        direction = Vector(direction)
        if direction.length < 1e-8:
            return None
        direction.normalize()
        best = None
        best_dist = max_dist
        for entry in self.active:
            if not (entry["kinds"] & kinds):
                continue
            # sphere pre-cull: skip if ray passes outside bounding sphere
            oc = origin - entry["center"]
            r = entry["radius"] + 0.05
            proj = oc.dot(direction)
            perp_sq = oc.length_squared - proj * proj
            if perp_sq > r * r:
                continue  # ray misses the sphere entirely
            # sphere entirely behind the ray origin -> skip.
            # center sits at ray parameter t_c = -proj; sphere spans
            # [t_c - r, t_c + r], so fully behind iff proj > r.
            if proj > r:
                continue
            hit = entry["bvh"].ray_cast(origin, direction, best_dist)
            if hit[0] is not None:
                loc, normal, index, distance = hit
                if distance < best_dist:
                    best_dist = distance
                    best = {
                        "loc": loc,
                        "normal": normal,
                        "obj": entry["obj"],
                        "dist": distance,
                        "entry": entry,
                    }
        return best

    # ------------------------------------------------------------ auto-refresh
    def maybe_auto_refresh(self, scene, settings, now):
        if not getattr(settings, "auto_refresh", True):
            return False
        count = len(self.entries)
        # adaptive interval: more objects -> check less often
        interval = max(1.0, min(8.0, count / 400.0 + 1.5))
        if now - self._last_refresh_check < interval:
            return False
        self._last_refresh_check = now
        fp = self._compute_fingerprint()
        if fp != self._fingerprint:
            self.rebuild(scene)
            return True
        return False

    def _compute_fingerprint(self):
        import hashlib

        h = hashlib.sha1()
        count = 0
        for obj in bpy.context.scene.objects:
            if obj.name.startswith(_TEMP_PREFIX) or obj.type != "MESH" or obj.hide_get():
                continue
            count += 1
            h.update(obj.name.encode())
            loc = obj.matrix_world.translation
            h.update(("%.3f,%.3f,%.3f" % (loc.x, loc.y, loc.z)).encode())
            rot = obj.matrix_world.to_quaternion()
            h.update(("%.3f,%.3f,%.3f,%.3f" % (rot.w, rot.x, rot.y, rot.z)).encode())
        h.update(str(count).encode())
        return h.hexdigest()

    def clear(self):
        self.entries = []
        self.active = []
        self._fingerprint = None


def _bounding_sphere(verts):
    if not verts:
        return Vector((0, 0, 0)), 0.0
    minv = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts)))
    maxv = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts)))
    center = (minv + maxv) * 0.5
    radius = max((v - center).length for v in verts)
    return center, radius
