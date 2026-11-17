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

"""EXPLORER — first-person world exploration inside Blender.

Walk through any scene with WASD + mouse look, collision, gravity,
jumping, doors, teleport and a HUD. Start from the 3D Viewport
sidebar (N-panel, category "EXPLORER").
"""

import bpy

bl_info = {
    "name": "EXPLORER",
    "author": "VeryCoolApps (PT. Agra Karya Digital)",
    "author_email": "wa.me/6281519250845",
    "version": (1, 0, 1),
    "blender": (4, 0, 0),
    "location": "3D Viewport > Sidebar (N) > EXPLORER",
    "description": "First-person exploration engine: walk, jump, collide, doors, teleport",
    "category": "3D View",
}


@bpy.app.handlers.persistent
def _load_pre_cleanup(*args):
    from .core import engine

    engine.ENGINE.emergency_cleanup()


def _import_leaves():
    # Leaf imports only; ui.panel may reference core.engine lazily.
    from .settings import props  # noqa: F401
    from .operators import actions  # noqa: F401
    from .operators import modal  # noqa: F401
    from .operators import room_picker_ops  # noqa: F401
    from .ui import hud  # noqa: F401
    from .ui import panel  # noqa: F401
    from .core import collision, player, camera_rig, engine  # noqa: F401
    from .navigation import location, teleport, room_picker  # noqa: F401
    from .interaction import interact  # noqa: F401
    from .tests import make_test_scene  # noqa: F401


_CLASSES = None


def _classes():
    global _CLASSES
    if _CLASSES is None:
        _import_leaves()
        from .settings import props
        from .operators import actions, modal, room_picker_ops
        from .ui import panel

        _CLASSES = (
            props.ExplorerSettings,
            panel.EXPLORER_PT_Main,
            modal.EXPLORER_OT_Explore,
            modal.EXPLORER_OT_Stop,
            actions.EXPLORER_OT_Pause,
            actions.EXPLORER_OT_ResetPosition,
            actions.EXPLORER_OT_RebuildCollision,
            actions.EXPLORER_OT_ApplyCollision,
            actions.EXPLORER_OT_MarkDoor,
            actions.EXPLORER_OT_MarkTeleport,
            actions.EXPLORER_OT_SetInfo,
            actions.EXPLORER_OT_TestScene,
            actions.EXPLORER_OT_AutoSpawn,
            room_picker_ops.EXPLORER_OT_SelectRoom,
            room_picker_ops.EXPLORER_OT_TeleportToRoom,
            room_picker_ops.EXPLORER_OT_ShowRooms,
        )
    return _CLASSES


def register():
    for cls in _classes():
        bpy.utils.register_class(cls)
    from .settings import props

    bpy.types.Scene.explorer = bpy.props.PointerProperty(type=props.ExplorerSettings)
    if _load_pre_cleanup not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(_load_pre_cleanup)


def unregister():
    global _CLASSES
    if _load_pre_cleanup in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(_load_pre_cleanup)
    try:
        del bpy.types.Scene.explorer
    except Exception:
        pass
    if _CLASSES:
        for cls in reversed(_CLASSES):
            try:
                bpy.utils.unregister_class(cls)
            except Exception:
                pass
        _CLASSES = None
