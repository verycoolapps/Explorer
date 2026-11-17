# =============================================================================
# © 2026 VeryCoolApps — PT. Agra Karya Digital
# ALL RIGHTS RESERVED — PROPRIETARY & CONFIDENTIAL
# =============================================================================
# EXPLORER Room Picker Operators
# =============================================================================

"""Operators for room selection and navigation."""

import bpy
from bpy.types import Operator
from ..navigation import room_picker
from ..core import engine as engine_mod


class EXPLORER_OT_TeleportToRoom(Operator):
    """Teleport player to selected room."""

    bl_idname = "explorer.teleport_to_room"
    bl_label = "Teleport to Room"
    bl_options = {"REGISTER", "UNDO"}

    room_name: bpy.props.StringProperty(name="Room Name", default="")

    def execute(self, context):
        scene = context.scene
        eng = engine_mod.ENGINE

        if not eng.active:
            self.report({"ERROR"}, "Start exploration first")
            return {"CANCELLED"}

        if not eng.player or not eng.player.entity:
            self.report({"ERROR"}, "Player not initialized")
            return {"CANCELLED"}

        detector = room_picker.detect_rooms(scene)
        room = detector.get_room(self.room_name)

        if not room:
            self.report({"ERROR"}, f"Room '{self.room_name}' not found")
            return {"CANCELLED"}

        room_picker.teleport_to_room(eng.player.entity, room, z_offset=0.5)
        self.report({"INFO"}, f"Teleported to {self.room_name}")
        return {"FINISHED"}


class EXPLORER_OT_SelectRoom(Operator):
    """Select room to spawn in."""

    bl_idname = "explorer.select_room"
    bl_label = "Select Room"
    bl_options = {"REGISTER", "UNDO"}

    room_name: bpy.props.StringProperty(name="Room Name", default="")

    def execute(self, context):
        scene = context.scene

        detector = room_picker.detect_rooms(scene)
        room = detector.get_room(self.room_name)

        if not room:
            self.report({"ERROR"}, f"Room '{self.room_name}' not found")
            return {"CANCELLED"}

        # Store selected room in scene properties
        scene.explorer.selected_room = self.room_name
        self.report({"INFO"}, f"Selected room: {self.room_name}")
        return {"FINISHED"}


class EXPLORER_OT_ShowRooms(Operator):
    """Show list of available rooms."""

    bl_idname = "explorer.show_rooms"
    bl_label = "Refresh Rooms"

    def execute(self, context):
        scene = context.scene
        detector = room_picker.detect_rooms(scene)
        rooms = detector.get_room_names()

        if not rooms:
            self.report({"WARNING"}, "No rooms detected")
        else:
            self.report({"INFO"}, f"Found {len(rooms)} rooms: {', '.join(rooms)}")

        return {"FINISHED"}
