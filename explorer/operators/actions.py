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

"""Sidebar + utility operators for EXPLORER."""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty

from ..core import engine as engine_mod
from ..tests import make_test_scene


def _engine_or_report(self):
    eng = engine_mod.ENGINE
    if not eng.active:
        self.report({"WARNING"}, "EXPLORER is not running")
        return None
    return eng


class EXPLORER_OT_ResetPosition(Operator):
    bl_idname = "explorer.reset_position"
    bl_label = "Reset Position"

    def execute(self, context):
        eng = _engine_or_report(self)
        if eng:
            eng.respawn()
        return {"FINISHED"}


class EXPLORER_OT_Pause(Operator):
    bl_idname = "explorer.pause"
    bl_label = "Pause/Resume Exploration"

    def execute(self, context):
        eng = _engine_or_report(self)
        if eng:
            eng.toggle_pause()
        return {"FINISHED"}

class EXPLORER_OT_RebuildCollision(Operator):
    bl_idname = "explorer.rebuild_collision"
    bl_label = "Refresh Collision World"

    def execute(self, context):
        eng = _engine_or_report(self)
        if eng:
            eng.collision.rebuild(context.scene)
            eng.toast("Collision world rebuilt", 2.0)
        return {"FINISHED"}


class EXPLORER_OT_ApplyCollision(Operator):
    bl_idname = "explorer.apply_collision"
    bl_label = "Apply Default Collision"

    def execute(self, context):
        s = context.scene.explorer
        value = s.default_collision.lower()
        count = 0
        for obj in context.selected_objects:
            if obj.name.startswith("EXPLORER_"):
                continue
            obj["explorer_collision"] = value
            count += 1
        self.report({"INFO"}, "Set explorer_collision='%s' on %d object(s)" % (value, count))
        return {"FINISHED"}


class EXPLORER_OT_MarkDoor(Operator):
    bl_idname = "explorer.mark_door"
    bl_label = "Mark as Door"

    def execute(self, context):
        count = 0
        for obj in context.selected_objects:
            obj["explorer_door"] = True
            if "explorer_door_axis" not in obj:
                obj["explorer_door_axis"] = "Z"
            if "explorer_door_angle" not in obj:
                obj["explorer_door_angle"] = 100.0
            count += 1
        self.report({"INFO"}, "Marked %d object(s) as doors" % count)
        return {"FINISHED"}


class EXPLORER_OT_MarkTeleport(Operator):
    bl_idname = "explorer.mark_teleport"
    bl_label = "Mark as Teleport"

    def execute(self, context):
        count = 0
        for obj in context.selected_objects:
            if obj.get("explorer_teleport"):
                obj["explorer_teleport"] = ""
            else:
                obj["explorer_teleport"] = obj.name
            count += 1
        self.report({"INFO"}, "Toggled teleport mark on %d object(s)" % count)
        return {"FINISHED"}


class EXPLORER_OT_SetInfo(Operator):
    bl_idname = "explorer.set_info"
    bl_label = "Set Explorer Info"
    bl_options = {"REGISTER", "UNDO"}

    info_text: StringProperty(name="Info", description="Text shown when player inspects this object", default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        count = 0
        for obj in context.selected_objects:
            obj["explorer_info"] = self.info_text
            count += 1
        self.report({"INFO"}, "Set explorer_info on %d object(s)" % count)
        return {"FINISHED"}


class EXPLORER_OT_ClearMarks(Operator):
    bl_idname = "explorer.clear_marks"
    bl_label = "Clear Explorer Marks"

    def execute(self, context):
        keys = ("explorer_collision", "explorer_door", "explorer_door_axis", "explorer_door_angle",
                "explorer_teleport", "explorer_teleport_label", "explorer_info",
                "explorer_floor", "explorer_room")
        count = 0
        for obj in context.scene.objects:
            for k in keys:
                if k in obj:
                    del obj[k]
                    count += 1
        self.report({"INFO"}, "Cleared %d mark(s)" % count)
        return {"FINISHED"}


class EXPLORER_OT_TestScene(Operator):
    bl_idname = "explorer.test_scene"
    bl_label = "Create Test House"

    def execute(self, context):
        try:
            make_test_scene.build_test_house(context)
            self.report({"INFO"}, "Test house created")
        except Exception as e:
            self.report({"ERROR"}, "Failed to build test house: %s" % e)
            return {"CANCELLED"}
        return {"FINISHED"}

class EXPLORER_OT_AutoSpawn(Operator):
    bl_idname = "explorer.auto_spawn"
    bl_label = "Auto-Place Spawn"

    def execute(self, context):
        scene = context.scene
        collision = engine_mod.ENGINE.collision
        collision.rebuild(scene)
        collision.active = list(collision.entries)
        extra = [scene.cursor.location.copy()] if getattr(scene, "cursor", None) else None
        feet, source = engine_mod.auto_spawn_scan(
            collision, scene.explorer, extra_points=extra)
        if feet is None:
            self.report({"ERROR"}, "Auto spawn failed: %s" % source)
            return {"CANCELLED"}
        obj = bpy.data.objects.get("EXPLORER_SPAWN")
        if obj is None:
            obj = bpy.data.objects.new("EXPLORER_SPAWN", None)
            obj.empty_display_type = "SPHERE"
            obj.empty_display_size = 0.3
            obj.color = (0.2, 0.9, 0.3, 1.0)
            scene.collection.objects.link(obj)
        obj.location = feet
        obj.rotation_euler = (0.0, 0.0, 0.0)
        self.report({"INFO"}, "EXPLORER_SPAWN placed at (%.2f, %.2f, %.2f) — %s"
                    % (feet.x, feet.y, feet.z, source))
        return {"FINISHED"}
