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

"""EXPLORER settings PropertyGroup."""

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)


class ExplorerSettings(bpy.types.PropertyGroup):
    # ---- movement
    walk_speed: FloatProperty(name="Walk Speed", default=3.0, min=0.5, max=20.0)
    run_speed: FloatProperty(name="Run Speed", default=5.5, min=0.5, max=30.0)
    crouch_speed: FloatProperty(name="Crouch Speed", default=1.5, min=0.2, max=10.0)
    crouch_height: FloatProperty(name="Crouch Height", default=1.0, min=0.4, max=2.0)
    jump_height: FloatProperty(name="Jump Height", default=0.6, min=0.0, max=5.0)
    player_height: FloatProperty(name="Player Height", default=1.75, min=0.5, max=4.0)
    player_radius: FloatProperty(name="Player Radius", default=0.30, min=0.05, max=1.0)
    eye_height: FloatProperty(name="Eye Height", default=1.60, min=0.1, max=4.0)
    mouse_sensitivity: FloatProperty(name="Mouse Sensitivity", default=0.0022, min=0.0005, max=0.02)
    gravity: FloatProperty(name="Gravity", default=9.81, min=0.0, max=50.0)
    step_height: FloatProperty(name="Step Height", default=0.35, min=0.0, max=1.5)
    interact_distance: FloatProperty(name="Interact Distance", default=3.0, min=0.5, max=20.0)

    # ---- world
    world_bounds: FloatProperty(name="World Bounds (0=off)", default=0.0, min=0.0, max=1000.0)
    fall_z: FloatProperty(name="Fall Respawn Z", default=-200.0, min=-10000.0, max=0.0)

    # ---- toggles
    enable_jump: BoolProperty(name="Jump", default=True)
    enable_sprint: BoolProperty(name="Sprint", default=True)
    enable_crouch: BoolProperty(name="Crouch", default=True)
    enable_gravity: BoolProperty(name="Gravity", default=True)
    enable_collision: BoolProperty(name="Collision", default=True)

    # ---- look / camera
    invert_y: BoolProperty(name="Invert Y", default=False)
    camera_mode: EnumProperty(
        name="Camera Mode",
        items=[("FP", "First Person", "First person"), ("TP", "Third Person", "Third person")],
        default="FP",
    )
    view_mode: EnumProperty(
        name="Viewport Shading",
        items=[
            ("CURRENT", "Current", "Keep current shading"),
            ("SOLID", "Solid", "Solid shading"),
            ("MATERIAL", "Material Preview", "Material preview"),
            ("RENDERED", "Rendered", "Rendered shading"),
        ],
        default="CURRENT",
    )
    quality: EnumProperty(
        name="Quality",
        items=[
            ("LOW", "Low", "2 ray heights, no flashlight shadow"),
            ("MEDIUM", "Medium", "3 ray heights, shadow"),
            ("HIGH", "High", "5 ray heights, shadow"),
        ],
        default="MEDIUM",
    )
    default_collision: EnumProperty(
        name="Default Collision",
        items=[
            ("SOLID", "Solid", "Blocks all movement"),
            ("WALKABLE", "Walkable", "Ground only"),
            ("NONE", "None", "Ignored"),
        ],
        default="SOLID",
    )
    auto_refresh: BoolProperty(name="Auto Refresh Collision", default=True)
    auto_spawn: BoolProperty(name="Auto Spawn (grid-scan fallback)", default=True)


CLASSES = (ExplorerSettings,)
