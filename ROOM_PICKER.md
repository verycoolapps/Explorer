# EXPLORER Room Picker

**Navigate between rooms/spaces in your Blender scene during exploration.**

Automatically detects rooms from collections and provides quick teleportation between them while exploring.

---

## Features

- 🏠 **Automatic room detection** from Blender collections
- 📍 **Quick teleport** to any room during exploration  
- 🎥 **Smooth navigation** between spaces
- 🔍 **Room list** showing all available spaces
- ⚡ **In-exploration access** - teleport between rooms without stopping

---

## Setup

### Naming Conventions

EXPLORER Room Picker detects rooms using three methods:

**Method 1: Collections with "Room." prefix** (Recommended)
```
Scene Collection
├── Room.Kitchen
│   ├── floor
│   ├── walls
│   └── furniture
├── Room.Bedroom
│   ├── ...
└── Room.LivingRoom
    └── ...
```

**Method 2: Capitalized Collections**
```
Scene Collection
├── Kitchen
│   └── geometry
├── Bedroom
│   └── geometry
└── LivingRoom
    └── geometry
```

**Method 3: Objects with "room_" prefix**
```
Scene Collection
├── room_kitchen
├── room_bedroom
└── room_livingroom
```

---

## Usage

### 1. Start Exploration

- Open EXPLORER sidebar (N-panel, category "EXPLORER")
- Click **"Start Exploration"**

### 2. View Available Rooms

- Look at **"Room Navigation"** section
- Click **"Refresh Rooms"** to scan scene
- Shows list of detected rooms

### 3. Teleport Between Rooms

While exploring (not paused):
- Click **"→ RoomName"** button
- Player instantly teleports to room center
- Continue exploration in new room

### 4. Without Exploration

If you haven't started exploration yet:
- Room list shows available spaces (read-only)
- Start exploration first to navigate

---

## Room Detection Details

### Automatic Detection

Each room is scanned for:
- **Center point** - geometric center of all objects
- **Bounds** - min/max coordinates
- **Spawn point** - center + 0.5m height offset

### Spawn Behavior

When teleporting to a room:
- Player spawned at room center
- Height offset prevents clipping through floor
- Maintains player state (inventory, speed, etc)

---

## Technical Details

### Files Added

- `explorer/navigation/room_picker.py` - Room detection & teleport logic
- `explorer/operators/room_picker_ops.py` - Blender operators
- UI panel integration in `explorer/ui/panel.py`

### Integration

Room Picker is fully integrated into EXPLORER:
- Uses existing player entity
- Respects collision settings
- Maintains exploration state
- Synchronized with location HUD

---

## Workflow Example

**Scenario: 4-room game level exploration**

```
1. Scene has: Room.Hub, Room.East, Room.West, Room.Boss
2. Start Exploration
3. Spawn at Room.Hub
4. Explore around, check geometry
5. Click "→ Room.East" to teleport
6. Check East room, interact with objects
7. Click "→ Room.Boss" to visit boss arena
8. Use Teleport Points (normal gameplay) OR Room Navigation (jump)
9. Stop Exploration when done
```

---

## Notes

- Room picker **does not affect** normal teleport points/gameplay teleports
- Rooms must have **at least one object** to be detected  
- Empty collections are ignored
- Room names are **case-sensitive**
- Works with collision enabled/disabled

---

## See Also

- Main EXPLORER README - Feature overview & keyboard shortcuts
- KEYBOARD_SHORTCUTS.md - All keybindings
