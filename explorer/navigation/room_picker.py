# =============================================================================
# © 2026 VeryCoolApps — PT. Agra Karya Digital
# ALL RIGHTS RESERVED — PROPRIETARY & CONFIDENTIAL
# =============================================================================
# EXPLORER Room Picker — Navigate between rooms/spaces in your scene
# =============================================================================

"""Room detection and navigation for multi-room scenes.

Automatically detects rooms from Blender collections and provides
navigation UI to jump between them or spawn in specific rooms.

Naming conventions:
  - Collections: "Room.Name" (e.g., "Room.Kitchen")
  - Or capitalized: "Kitchen", "Bedroom"
  - Or objects: "room_name"
"""

from mathutils import Vector
from typing import Dict, List, Optional, Tuple
import bpy


class Room:
    """Represents a single room in the scene."""

    def __init__(self, name: str, objects: List[bpy.types.Object], collection=None):
        self.name = name
        self.objects = objects
        self.collection = collection
        self._bounds = None
        self._center = None

    @property
    def bounds(self) -> Tuple[Vector, Vector]:
        """Get room bounds (min, max)."""
        if self._bounds is None:
            if not self.objects:
                self._bounds = (Vector((0, 0, 0)), Vector((0, 0, 0)))
            else:
                min_coords = [float("inf")] * 3
                max_coords = [float("-inf")] * 3

                for obj in self.objects:
                    if obj.type in ("MESH", "CURVE", "SURFACE"):
                        if hasattr(obj.data, "vertices"):
                            for vertex in obj.data.vertices:
                                world_pos = obj.matrix_world @ vertex.co
                                for i in range(3):
                                    min_coords[i] = min(min_coords[i], world_pos[i])
                                    max_coords[i] = max(max_coords[i], world_pos[i])

                self._bounds = (Vector(min_coords), Vector(max_coords))

        return self._bounds

    @property
    def center(self) -> Vector:
        """Get room center point."""
        if self._center is None:
            min_b, max_b = self.bounds
            self._center = (min_b + max_b) / 2
        return self._center

    @property
    def size(self) -> Vector:
        """Get room dimensions."""
        min_b, max_b = self.bounds
        return max_b - min_b

    def spawn_point(self, offset_height: float = 0.5) -> Vector:
        """Get safe spawn point in room (at center, raised by offset)."""
        center = self.center
        return Vector((center.x, center.y, center.z + offset_height))


class RoomDetector:
    """Detects and manages rooms in scene."""

    def __init__(self, scene: bpy.types.Scene):
        self.scene = scene
        self.rooms: Dict[str, Room] = {}
        self.detect_rooms()

    def detect_rooms(self):
        """Detect rooms from scene collections - super smart detection."""
        self.rooms.clear()

        # Scan all collections recursively - DETECT EVERYTHING
        self._scan_collections_smart(self.scene.collection)

        # Fallback: Also check objects with "room_" prefix at root level
        for obj in self.scene.collection.objects:
            if obj.name.startswith("room_"):
                room_name = obj.name[5:]
                if room_name not in self.rooms:
                    self.rooms[room_name] = Room(room_name, [obj])

    def _scan_collections_smart(self, parent_collection: bpy.types.Collection):
        """Recursively scan ALL collections - super smart detection."""
        for collection in parent_collection.children:
            # Skip only hidden/system collections (starting with .)
            if collection.name.startswith("."):
                continue

            # Get all objects in this collection (recursive)
            objects = self._get_collection_objects(collection)

            # ADD EVERY COLLECTION - regardless of content
            # Method 1: Priority - collections with "Room." prefix
            if collection.name.startswith("Room."):
                room_name = collection.name[5:]
            else:
                # Method 2: Any other collection name (use as-is)
                room_name = collection.name

            # Add room even if empty - it's still a valid space
            self.rooms[room_name] = Room(room_name, objects if objects else [], collection)

            # Recurse into subcollections (nested rooms too)
            self._scan_collections_smart(collection)

    def _add_room_from_collection(
        self, room_name: str, collection: bpy.types.Collection
    ):
        """Create room from collection."""
        objects = self._get_collection_objects(collection)
        if objects:
            self.rooms[room_name] = Room(room_name, objects, collection)

    def _get_collection_objects(
        self, collection: bpy.types.Collection, recursive: bool = True
    ) -> List[bpy.types.Object]:
        """Get all objects in collection."""
        objects = list(collection.objects)
        if recursive:
            for sub in collection.children:
                objects.extend(self._get_collection_objects(sub))
        return objects

    def get_room_names(self) -> List[str]:
        """Get sorted room names."""
        return sorted(self.rooms.keys())

    def get_room(self, name: str) -> Optional[Room]:
        """Get room by name."""
        return self.rooms.get(name)

    def get_all_rooms(self) -> List[Room]:
        """Get all rooms."""
        return [self.rooms[name] for name in self.get_room_names()]


def detect_rooms(scene: bpy.types.Scene) -> RoomDetector:
    """Detect rooms in scene."""
    return RoomDetector(scene)


def teleport_to_room(
    player_obj: bpy.types.Object, room: Room, z_offset: float = 0.5
):
    """Teleport player to room center."""
    spawn_point = room.spawn_point(z_offset)
    player_obj.location = spawn_point
