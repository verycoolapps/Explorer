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

"""EXPLORER sidebar panel (N-panel, category 'EXPLORER')."""

import bpy
from bpy.types import Panel

from ..core import engine as engine_mod


class EXPLORER_PT_Main(Panel):
    bl_label = "EXPLORER"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "EXPLORER"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        s = scene.explorer
        eng = engine_mod.ENGINE

        # ---- start/stop
        row = layout.row()
        if eng.active:
            row.operator("explorer.stop", text="Stop Exploration", icon="PAUSE")
            row.operator("explorer.reset_position", text="", icon="LOOP_BACK")
            pause_text = "Resume Exploration" if eng.manual_pause else "Pause Exploration"
            row.operator("explorer.pause", text=pause_text, icon="TIME")
        else:
            row.operator("explorer.explore", text="Start Exploration", icon="PLAY")

        # ---- status
        if eng.active and eng.player_state is not None:
            box = layout.box()
            p = eng.player_state.pos
            box.label(text="Pos: %.1f, %.1f, %.1f" % (p.x, p.y, p.z))
            box.label(text="FPS: %.0f" % eng.fps)
            loc = eng.location_cache
            parts = [x for x in (loc.get("area"), loc.get("floor"), loc.get("room")) if x]
            if parts:
                box.label(text="Loc: " + " / ".join(parts))

        layout.separator()

        # ---- movement
        box = layout.box()
        box.label(text="Movement", icon="ARMATURE_DATA")
        col = box.column(align=True)
        col.prop(s, "walk_speed")
        col.prop(s, "run_speed")
        col.prop(s, "crouch_speed")
        col.prop(s, "jump_height")
        col.prop(s, "player_height")
        col.prop(s, "player_radius")
        col.prop(s, "eye_height")
        col.prop(s, "mouse_sensitivity")
        col.prop(s, "gravity")
        col.prop(s, "step_height")
        row = box.row(align=True)
        row.prop(s, "enable_jump", toggle=True)
        row.prop(s, "enable_sprint", toggle=True)
        row.prop(s, "enable_crouch", toggle=True)
        row.prop(s, "enable_gravity", toggle=True)
        box.prop(s, "invert_y")

        # ---- collision
        box = layout.box()
        box.label(text="Collision", icon="MESH_UVSPHERE")
        box.prop(s, "enable_collision")
        box.prop(s, "default_collision")
        box.prop(s, "auto_refresh")
        row = box.row(align=True)
        row.operator("explorer.apply_collision", text="Apply to Selected", icon="CHECKMARK")
        row.operator("explorer.rebuild_collision", text="Refresh", icon="FILE_REFRESH")

        # ---- camera
        box = layout.box()
        box.label(text="Camera", icon="CAMERA_DATA")
        box.prop(s, "camera_mode", expand=True)
        box.prop(s, "view_mode")
        box.prop(s, "quality")
        box.prop(s, "interact_distance")

        # ---- world
        box = layout.box()
        box.label(text="World", icon="WORLD")
        box.prop(s, "world_bounds")
        box.prop(s, "fall_z")
        box.prop(s, "auto_spawn")

        layout.separator()

        # ---- object marking
        box = layout.box()
        box.label(text="Object Marking", icon="OBJECT_DATA")
        row = box.row(align=True)
        row.operator("explorer.mark_door", text="Door", icon="PROP_ON")
        row.operator("explorer.mark_teleport", text="Teleport", icon="PROP_CON")
        row.operator("explorer.set_info", text="Info", icon="TEXT")
        box.operator("explorer.clear_marks", text="Clear Explorer Marks", icon="X")

        # ---- tools
        box = layout.box()
        box.label(text="Tools", icon="TOOL_SETTINGS")
        box.operator("explorer.test_scene", text="Create Test House", icon="HOME")
        box.operator("explorer.auto_spawn", text="Auto-Place Spawn", icon="MOD_MESHDEFORM")
        if eng.active:
            box.operator("explorer.reset_position", text="Teleport to Spawn", icon="LOOP_BACK")

        layout.separator()

        # ---- about (collapsed)
        about = layout.box()
        about.label(text="ABOUT", icon="INFO")
        col = about.column(align=True)
        col.label(text="EXPLORER v1.0.0")
        col.label(text="© 2026 VeryCoolApps — PT. Agra Karya Digital")
        col.label(text="All Rights Reserved")
        col.label(text="WhatsApp +62 815-1925-0845")
        col.label(text="Telegram t.me/VeryCoolApps")
