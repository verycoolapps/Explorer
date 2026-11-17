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

"""Modal operator: explorer.explore game loop."""

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty

from ..core import engine as engine_mod


class EXPLORER_OT_Explore(Operator):
    """Start EXPLORER first-person exploration"""

    bl_idname = "explorer.explore"
    bl_label = "Start Exploration"
    bl_options = {"REGISTER", "GRAB_CURSOR", "BLOCKING"}

    _timer = None
    _draw_handle = None

    def invoke(self, context, event):
        eng = engine_mod.ENGINE
        if eng.active:
            self.report({"WARNING"}, "EXPLORER is already running")
            return {"CANCELLED"}
        err = eng.start(context)
        if err:
            self.report({"ERROR"}, err)
            return {"CANCELLED"}
        eng.operator = self
        self._timer = eng._timer
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        eng = engine_mod.ENGINE
        if eng.request_stop or not eng.active:
            eng.finish(context)
            return {"FINISHED"}
        eng.handle_event(event)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        return self.invoke(context, None)


class EXPLORER_OT_Stop(Operator):
    """Stop EXPLORER exploration"""

    bl_idname = "explorer.stop"
    bl_label = "Stop Explorer"

    def execute(self, context):
        engine_mod.ENGINE.request_stop = True
        return {"FINISHED"}
