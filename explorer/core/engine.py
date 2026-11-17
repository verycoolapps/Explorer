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

"""EXPLORER engine: modal operator + singleton state + game loop."""

import math
import time

import bpy
from mathutils import Vector, Quaternion

from .collision import CollisionWorld
from .player import PlayerState, PlayerPhysics
from .camera_rig import CameraRig
from ..navigation import location as nav_location
from ..navigation import teleport as nav_teleport
from ..interaction import interact as interact_mod
from ..ui import hud


def auto_spawn_scan(collision, settings, extra_points=None, grid=8):
    """Grid-scan the scene for a safe spawn point. Returns (feet, source) or (None, reason).

    Samples an NxN grid over the XY bounds of collision entries (biased toward
    the scene center), plus any extra candidate points (e.g. the 3D cursor).
    For each candidate, probes downward for walkable ground and validates the
    player capsule. Returns the first safe point found; prefers lower Z and
    points closer to the bounds center.
    """
    phys = PlayerPhysics(settings, collision)
    phys._apply_quality()

    # bounds from collision entries (fallback: scene objects)
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    max_z = 0.0
    min_z = float("inf")
    have = False
    for entry in collision.entries:
        c = entry["center"]
        r = entry["radius"]
        have = True
        min_x = min(min_x, c.x - r)
        max_x = max(max_x, c.x + r)
        min_y = min(min_y, c.y - r)
        max_y = max(max_y, c.y + r)
        min_z = min(min_z, c.z - r)
        max_z = max(max_z, c.z + r)
    if not have:
        return None, "no collision geometry in scene"

    cx, cy = (min_x + max_x) * 0.5, (min_y + max_y) * 0.5
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)

    # candidate order: extra points first, then grid biased toward center
    cands = []
    if extra_points:
        for p in extra_points:
            if p is not None:
                cands.append((Vector(p), "cursor"))
    pts = []
    n = grid
    for iy in range(n):
        for ix in range(n):
            fx = (ix + 0.5) / n
            fy = (iy + 0.5) / n
            x = min_x + fx * span_x
            y = min_y + fy * span_y
            # bias: sample order by distance from center (inner cells first)
            d = abs(fx - 0.5) + abs(fy - 0.5)
            pts.append((d, Vector((x, y, 0.0))))
    pts.sort(key=lambda t: t[0])
    for _, p in pts:
        cands.append((p, "grid"))

    best = None
    best_key = None
    for cand, source in cands:
        # probe from above the scene bounds downward; reach the lowest bound
        probe = Vector((cand.x, cand.y, max_z + 2.0))
        reach = (max_z + 2.0) - min_z + 2.0
        hit = collision.raycast(probe, Vector((0, 0, -1)), reach,
                                kinds={"solid", "walkable"})
        if hit is None:
            continue
        feet = Vector((cand.x, cand.y, hit["loc"].z + 0.03))
        if hit["normal"].z < 0.4:
            continue  # not a floor
        if not phys.capsule_free(feet, settings.player_height):
            continue
        # prefer lowest ground, then closest to center
        key = (feet.z, (feet.x - cx) ** 2 + (feet.y - cy) ** 2)
        if best_key is None or key < best_key:
            best_key = key
            best = (feet, "auto:%s" % source)
        if source == "cursor":
            # a safe cursor point is good enough; keep scanning only if none yet
            pass
    if best is not None:
        return best
    return None, "no safe point found in %dx%d grid over bounds (%.1f,%.1f)-(%.1f,%.1f)" % (
        n, n, min_x, min_y, max_x, max_y)


class ExplorerEngine:
    """Runtime state for one exploration session."""

    def __init__(self):
        self.active = False
        self.request_stop = False
        self.operator = None
        self.context = None
        self.window = None
        self.region = None
        self.space = None
        self.area = None

        # backups
        self.backup_camera = None
        self.backup_perspective = None
        self.backup_shading = None

        # modules
        self.collision = CollisionWorld()
        self.settings = None
        self.scene = None
        self.player_state = None
        self.physics = None
        self.rig = None

        # input
        self.look_dx = 0.0
        self.look_dy = 0.0
        self.last_mouse = (0, 0)
        self.mouse_warped = False

        # hud state
        self.fps = 0.0
        self.time = 0.0
        self.location_cache = {}
        self.toast_msg = ""
        self.toast_until = 0.0
        self.info_popup = None
        self.focus = None
        self.menu_open = False
        self.menu_items = []
        self.menu_index = 0
        self.menu_stack = []
        self.manual_pause = False

        # gameplay extras
        self.door_backup = {}
        self.saved_positions = []
        self.spawn_pos = None
        self.spawn_yaw = 0.0
        self._fps_acc = 0.0
        self._fps_frames = 0
        self._last_tick = 0.0
        self._draw_handle = None
        self._timer = None

    @property
    def paused(self):
        return self.menu_open or self.manual_pause


    # ------------------------------------------------------------ math helpers
    def forward_vec(self):
        if self.player_state is None:
            return Vector((0, 0, -1))
        yaw = self.player_state.yaw
        pitch = self.player_state.pitch
        cp = math.cos(pitch)
        return Vector((-math.sin(yaw) * cp, -math.cos(yaw) * cp, math.sin(pitch)))

    def right_vec(self):
        yaw = self.player_state.yaw if self.player_state else 0.0
        return Vector((-math.cos(yaw), math.sin(yaw), 0.0))

    def look_quat(self):
        fwd = self.forward_vec()
        if fwd.length < 1e-8:
            return Quaternion()
        return fwd.to_track_quat("-Z", "Y")

    # --------------------------------------------------------------- toast/info
    def toast(self, msg, dur=3.0):
        self.toast_msg = msg
        self.toast_until = self.time + dur

    def save_position(self, label="Saved"):
        p = self.player_state.pos.copy()
        self.saved_positions.append(
            {"label": label, "pos": (p.x, p.y, p.z), "yaw": self.player_state.yaw}
        )
        self.toast("Position saved", 1.5)

    def respawn(self):
        if self.spawn_pos is not None:
            self.player_state.pos = self.spawn_pos.copy()
            self.player_state.vel = Vector((0, 0, 0))
            self.player_state.yaw = self.spawn_yaw
            self.player_state.pitch = 0.0
            self.player_state.grounded = True
            self.toast("Respawned", 1.5)

    # ------------------------------------------------------------- menu system
    def build_menu(self):
        s = self.settings
        tp_label = "Camera: %s" % ("First Person" if s.camera_mode == "FP" else "Third Person")
        flash_label = "Flashlight: ON" if getattr(self, "flashlight_on", True) else "Flashlight: OFF"
        items = [
            {"label": "Resume" if not self.manual_pause else "Resume (unpause)", "action": "resume"},
            {"label": tp_label, "action": "toggle_camera"},
            {"label": flash_label, "action": "toggle_flash"},
            {"label": "Teleport", "action": "submenu_teleport"},
            {"label": "Save Current Position", "action": "save_position"},
            {"label": "Respawn at Start", "action": "respawn"},
            {"label": "Exit Explorer", "action": "exit"},
            {"label": "Clear Saved", "action": "clear_saved"},
        ]
        return items

    def open_menu(self):
        self.menu_stack = [self.build_menu()]
        self.menu_items = self.menu_stack[0]
        self.menu_open = True
        self.menu_index = 0


    def close_menu(self):
        self.menu_open = False
        self.menu_items = []
        self.menu_stack = []
        self.menu_index = 0

    def toggle_pause(self):
        """Manual pause toggle (P key / panel button)."""
        self.manual_pause = not self.manual_pause
        if self.manual_pause and self.player_state is not None:
            # freeze: drop held keys and kill horizontal momentum
            self.player_state.keys.clear()
            self.player_state.vel.x = 0.0
            self.player_state.vel.y = 0.0
        self.toast("Paused" if self.manual_pause else "Resumed", 1.2)

    def apply_look(self, dt):
        s = self.settings
        dx = self.look_dx
        dy = self.look_dy
        self.look_dx = 0.0
        self.look_dy = 0.0
        if s.invert_y:
            dy = -dy
        # look_dx/dy are accumulated pixel deltas; convert via sensitivity
        self.player_state.yaw += dx * s.mouse_sensitivity
        self.player_state.pitch += dy * s.mouse_sensitivity
        self.player_state.pitch = max(-1.55, min(1.55, self.player_state.pitch))

    def menu_up(self):
        items = self.menu_items
        if not items:
            return
        self.menu_index = (self.menu_index - 1) % len(items)

    def menu_down(self):
        items = self.menu_items
        if not items:
            return
        self.menu_index = (self.menu_index + 1) % len(items)

    def menu_confirm(self):
        items = self.menu_items
        if not items:
            return
        item = items[self.menu_index]
        action = item.get("action")
        if action == "resume":
            self.close_menu()
        elif action == "toggle_camera":
            s = self.settings
            s.camera_mode = "TP" if s.camera_mode == "FP" else "FP"
            self.menu_stack[-1] = self.build_menu()
            self.menu_index = min(self.menu_index, len(self.menu_items) - 1)
        elif action == "toggle_flash":
            self.flashlight_on = not getattr(self, "flashlight_on", True)
            self._apply_flashlight()
            self.menu_stack[-1] = self.build_menu()
            self.menu_index = min(self.menu_index, len(self.menu_items) - 1)
        elif action == "submenu_teleport":
            targets = nav_teleport.collect_targets(self)
            sub = [{"label": "< Back", "action": "back"}]
            for t in targets:
                sub.append({"label": t["label"], "action": "teleport", "target": t})
            self.menu_stack.append(sub)
            self.menu_items = sub
            self.menu_index = 0
        elif action == "back":
            if len(self.menu_stack) > 1:
                self.menu_stack.pop()
                self.menu_items = self.menu_stack[-1]
                self.menu_index = 0
            else:
                self.close_menu()
        elif action == "teleport":
            t = item["target"]
            nav_teleport.try_teleport(self, t["pos"], yaw=t.get("yaw"))
            self.close_menu()
        elif action == "save_position":
            self.save_position("Saved %d" % (len(self.saved_positions) + 1))
        elif action == "respawn":
            self.respawn()
        elif action == "exit":
            self.request_stop = True
        elif action == "clear_saved":
            self.saved_positions = []
            self.toast("Saved positions cleared", 1.5)

    def menu_cancel(self):
        if len(self.menu_stack) > 1:
            self.menu_stack.pop()
            self.menu_items = self.menu_stack[-1]
            self.menu_index = 0
        else:
            self.close_menu()

    def _apply_flashlight(self):
        if self.rig and self.rig.flash is not None:
            self.rig.flash.hide_render = not getattr(self, "flashlight_on", True)
            self.rig.flash.hide_set(not getattr(self, "flashlight_on", True))

    # ------------------------------------------------------------- start/stop
    def start(self, context):
        """Called by modal operator invoke. Returns error string or None."""
        # find VIEW_3D area + WINDOW region
        screen = getattr(context, "screen", None)
        if screen is None:
            return "EXPLORER: No screen available. Open a 3D Viewport first."
        area = None
        region = None
        for a in screen.areas:
            if a.type == "VIEW_3D":
                for r in a.regions:
                    if r.type == "WINDOW":
                        area, region = a, r
                        break
                if area:
                    break
        if area is None or region is None:
            return "EXPLORER: No 3D Viewport found. Open a VIEW_3D area first."

        space = area.spaces.active
        if space is None or getattr(space, "region_3d", None) is None:
            return "EXPLORER: 3D Viewport is not ready. Click into the viewport and try again."

        self.context = context
        self.window = context.window
        self.region = region
        self.area = area
        self.space = space
        self.scene = context.scene
        self.settings = self.scene.explorer

        # backups
        self.backup_camera = self.scene.camera
        self.backup_perspective = space.region_3d.view_perspective
        self.backup_shading = space.shading.type

        # apply shading mode
        vm = self.settings.view_mode
        if vm == "SOLID":
            self.space.shading.type = "SOLID"
        elif vm == "MATERIAL":
            self.space.shading.type = "MATERIAL"
        elif vm == "RENDERED":
            self.space.shading.type = "RENDERED"

        # set camera view
        self.space.region_3d.view_perspective = "CAMERA"

        # cursor
        try:
            self.window.cursor_modal_set("NONE")
        except Exception:
            pass

        # spawn
        spawn_obj = bpy.data.objects.get("EXPLORER_SPAWN")
        if spawn_obj is not None:
            dg = bpy.context.evaluated_depsgraph_get()
            spawn_pos = spawn_obj.evaluated_get(dg).matrix_world.translation.copy()
            spawn_yaw = -spawn_obj.matrix_world.to_euler().z
        else:
            spawn_pos = self.scene.cursor.location.copy() if self.scene.cursor else Vector((0, 0, 1))
            spawn_yaw = 0.0

        # build collision first (needed for spawn validation)
        self.collision.rebuild(self.scene)
        self.collision.update_focus(spawn_pos, 8.0)

        self.physics = PlayerPhysics(self.settings, self.collision, toast=self.toast)
        self.physics._apply_quality()
        self.player_state = PlayerState(self.settings)

        # resolve spawn: EXPLORER_SPAWN/cursor first, then optional auto grid-scan
        resolved = None
        spawn_source = ""
        try:
            resolved = self._resolve_spawn(spawn_pos)
            if resolved is not None:
                spawn_source = "EXPLORER_SPAWN" if spawn_obj is not None else "3D cursor"
        except Exception as e:
            print("EXPLORER spawn resolve error: %s" % e)
        if resolved is None and getattr(self.settings, "auto_spawn", True):
            extra = [self.scene.cursor.location.copy()] if getattr(self.scene, "cursor", None) else None
            # scan needs ALL entries, not just the focus-filtered active set
            saved_active = self.collision.active
            self.collision.active = list(self.collision.entries)
            try:
                resolved, spawn_source = auto_spawn_scan(
                    self.collision, self.settings, extra_points=extra)
            finally:
                self.collision.active = saved_active
        if resolved is None:
            self.finish(context)
            detail = ""
            if spawn_source:
                detail = " Auto-scan also failed: %s." % spawn_source
            return ("EXPLORER: Could not find a safe spawn position.%s "
                    "Place an 'EXPLORER_SPAWN' object on walkable ground, "
                    "move the 3D cursor, or enable Auto Spawn." % detail)

        feet = resolved
        if spawn_source.startswith("auto"):
            self.toast("Auto spawn: grid scan", 3.0)

        self.player_state.pos = feet
        self.player_state.yaw = spawn_yaw
        self.player_state.pitch = 0.0
        self.spawn_pos = feet.copy()
        self.spawn_yaw = spawn_yaw

        # camera rig
        self.rig = CameraRig(self)
        self.rig.create(self.scene, self.settings)
        self.flashlight_on = True

        # link temp camera to scene for view_perspective='CAMERA'
        self.scene.camera = self.rig.cam

        # HUD draw handler
        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            hud.draw_callback, (self, region), "WINDOW", "POST_PIXEL"
        )

        # timer
        self._timer = bpy.app.timers.register(self._timer_tick, first_interval=1.0 / 60.0)

        self.active = True
        self.request_stop = False
        self.time = time.time()
        self._last_tick = self.time
        self.location_cache = {}
        self.menu_items = self.build_menu()
        self.menu_open = False
        self.menu_stack = []
        self.door_backup = {}
        self.saved_positions = []
        self.focus = None
        self.info_popup = None
        self.toast("EXPLORER started — WASD move, mouse look, E interact, Tab menu", 4.0)
        return None

    def _resolve_spawn(self, spawn_pos):
        """Find a safe feet position near spawn_pos.

        Tries direct spawn resolution first, then a nudge sweep around the
        point with small lifts (prefers nearby low ground over roofs), then
        larger vertical lifts as a last resort. Covers spawns placed inside
        walls or other geometry where vertical-only repair cannot work.
        """
        phys = self.physics
        feet = phys.spawn_point(spawn_pos)
        if feet is not None:
            return feet
        for radius in (0.6, 1.2, 2.0, 3.0):
            for k in range(8):
                ang = k * (math.pi / 4.0)
                for lift in (0.0, 0.5, 1.0):
                    cand = spawn_pos + Vector(
                        (math.cos(ang) * radius, math.sin(ang) * radius, lift)
                    )
                    feet = phys.spawn_point(cand)
                    if feet is not None:
                        return feet
        for lift in (0.5, 1.0, 1.5, 2.0, 3.0):
            feet = phys.spawn_point(spawn_pos + Vector((0, 0, lift)))
            if feet is not None:
                return feet
        return None

    def _timer_tick(self):
        "Called by bpy.app.timers; returns interval or None to stop."""
        if not self.active or self.request_stop:
            return None
        try:
            self.tick(self.context)
        except Exception as e:
            self.toast("EXPLORER error: %s" % e, 3.0)
        return 1.0 / 60.0

    # --------------------------------------------------------------- event loop
    def handle_event(self, event):
        """Called from modal operator. Returns True if event consumed."""
        et = event.type
        # timer events handled by operator separately? Actually modal gets TIMER too.
        if et == "TIMER":
            self.tick(self.context)
            return True

        if et == "MOUSEMOVE":
            cx = self.window.width // 2
            cy = self.window.height // 2
            # event.mouse_x/y are window coords; region offset not needed for delta
            dx = event.mouse_x - self.last_mouse[0]
            dy = event.mouse_y - self.last_mouse[1]
            # accumulate raw pixel deltas; sensitivity applied in apply_look
            self.look_dx += dx
            self.look_dy += dy
            self.last_mouse = (event.mouse_x, event.mouse_y)
            return True

        if et in ("WHEELUPMOUSE", "MOUSEWHEELUP"):
            if self.settings.camera_mode == "TP":
                self.rig.wheel_zoom(-1.0)
            return True
        if et in ("WHEELDOWNMOUSE", "MOUSEWHEELDOWN"):
            if self.settings.camera_mode == "TP":
                self.rig.wheel_zoom(1.0)
            return True

        # Keyboard events in modal operators arrive with event.type == key name
        # (e.g. 'W', 'ESC', 'LEFT_SHIFT'); event.key is usually empty. Accept
        # both 'KEYBOARD' (key stored in .key) and bare key-name types.
        key = ""
        if et == "KEYBOARD":
            key = getattr(event, "key", "") or getattr(event, "ascii", "") or ""
        elif et and (len(et) == 1 or et in (
            "ESC", "TAB", "SPACE", "RET", "NUMPAD_ENTER",
            "UP", "DOWN", "LEFT", "RIGHT",
            "LEFT_SHIFT", "RIGHT_SHIFT", "LEFT_CTRL", "RIGHT_CTRL",
            "LEFT_ALT", "RIGHT_ALT",
        )):
            key = et
        if key:
            key = key.upper() if len(key) == 1 else key
            # claim the event so Blender doesn't cancel the modal operator (ESC)
            # or trigger default keymap actions while exploring
            try:
                event.prevent_default()
            except Exception:
                pass
            val = getattr(event, "value", "PRESS") or "PRESS"
            # modifiers for run/crouch come as key events too
            if key in ("LEFT_SHIFT", "RIGHT_SHIFT"):
                self._modifier("SHIFT", val == "PRESS")
                return True
            if key in ("LEFT_CTRL", "RIGHT_CTRL"):
                if val == "PRESS" and self.settings.enable_crouch:
                    self.player_state.crouching = not self.player_state.crouching
                return True
            if key in ("W", "A", "S", "D", "UP", "DOWN", "LEFT", "RIGHT", "SPACE", "E", "C", "F", "TAB", "ESC", "RET", "NUMPAD_ENTER", "P"):
                self._key_event(key, val)
                return True
            # generic single-char keys (IJKL etc.) as movement fallback
            if len(key) == 1:
                self._key_event(key, val)
                return True
            return True

        return True  # consume everything while exploring

    def _modifier(self, name, down):
        keys = self.player_state.keys
        if down:
            keys.add(name)
        else:
            keys.discard(name)

    def _key_event(self, key, value):
        """value: 'PRESS', 'RELEASE', 'CLICK'"""
        down = value in ("PRESS", "CLICK")
        state = self.player_state
        movement_keys = {"W", "A", "S", "D", "UP", "DOWN", "LEFT", "RIGHT", "SPACE"}

        # menu navigation takes priority when menu is open
        if self.menu_open and key in ("UP", "DOWN", "W", "S") and value == "PRESS":
            if key in ("UP", "W"):
                self.menu_up()
            else:
                self.menu_down()
            return

        if key in movement_keys and not (self.menu_open and key in ("W", "S", "UP", "DOWN")):
            if down:
                state.keys.add(key)
            else:
                state.keys.discard(key)
            return

        if key == "SHIFT":
            if down:
                state.keys.add("SHIFT")
            else:
                state.keys.discard("SHIFT")
            return

        if key == "LEFT_CTRL" or key == "RIGHT_CTRL":
            # toggle crouch on press edge (Ctrl is a modifier; use press edge)
            if value == "PRESS":
                state.crouching = not state.crouching
            return

        if value != "PRESS" and value != "CLICK":
            return

        if key == "E":
            interact_mod.try_interact(self)
        elif key == "C":
            s = self.settings
            s.camera_mode = "TP" if s.camera_mode == "FP" else "FP"
            self.toast("Camera: %s" % ("Third Person" if s.camera_mode == "TP" else "First Person"), 1.5)
        elif key == "F":
            self.flashlight_on = not getattr(self, "flashlight_on", True)
            self._apply_flashlight()
            self.toast("Flashlight %s" % ("ON" if self.flashlight_on else "OFF"), 1.2)
        elif key == "P":
            self.toggle_pause()
        elif key == "TAB":
            if self.menu_open:
                self.menu_cancel()
            else:
                self.open_menu()
        elif key == "ESC":
            if self.menu_open:
                self.menu_cancel()
            else:
                self.request_stop = True
        elif key in ("RET", "NUMPAD_ENTER"):
            if self.menu_open:
                self.menu_confirm()

    # ------------------------------------------------------------------ tick
    def tick(self, context):
        if not self.active:
            return
        now = time.time()
        dt = min(0.1, now - self._last_tick) if self._last_tick else 1.0 / 60.0
        self._last_tick = now
        self.time = now

        # fps
        self._fps_frames += 1
        self._fps_acc += dt
        if self._fps_acc >= 0.5:
            self.fps = self._fps_frames / self._fps_acc
            self._fps_frames = 0
            self._fps_acc = 0.0

        # auto-refresh collision
        if self.collision.maybe_auto_refresh(self.scene, self.settings, now):
            self.toast("Collision refreshed", 2.0)

        # apply look (frozen while paused)
        if not self.paused:
            self.apply_look(dt)

        # warp cursor to center (self-correcting)
        cx = self.window.width // 2
        cy = self.window.height // 2
        try:
            self.window.cursor_warp(cx, cy)
            self.last_mouse = (cx, cy)
            self.mouse_warped = True
        except Exception:
            pass

        # physics (frozen while paused)
        if not self.paused:
            self.physics.update(dt, self.player_state)

        # fall respawn
        if self.player_state.pos.z < self.settings.fall_z:
            self.respawn()

        # camera rig (frozen while paused)
        if not self.paused:
            self.rig.update(context, dt)

        # interaction focus
        interact_mod.update_focus(self)

        # location cache (throttled to ~2 Hz)
        if not hasattr(self, "_loc_next") or now >= self._loc_next:
            self.location_cache = nav_location.resolve(self, self.player_state.pos)
            self._loc_next = now + 0.5

        # collision focus update
        self.collision.update_focus(self.player_state.pos, 8.0)

        # clear expired info popup
        if self.info_popup and now > self.info_popup["until"]:
            self.info_popup = None

    # ---------------------------------------------------------------- finish
    def finish(self, context):
        """Restore everything. Idempotent."""
        needs_restore = (
            self.active
            or self._draw_handle is not None
            or self.rig is not None
            or self.backup_perspective is not None
            or self.backup_shading is not None
        )
        if not needs_restore:
            return
        # stop timer
        try:
            if self._timer is not None:
                bpy.app.timers.unregister(self._timer_tick)
        except Exception:
            pass
        self._timer = None

        try:
            if self._draw_handle is not None:
                try:
                    bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, "WINDOW")
                except Exception:
                    pass
                self._draw_handle = None
        except Exception:
            pass

        # delete temp objects
        if self.rig is not None:
            self.rig.remove_temp(self.scene)
            self.rig = None

        # restore camera / perspective / shading
        if self.scene is not None:
            if self.backup_camera is not None:
                self.scene.camera = self.backup_camera
            if self.space is not None:
                if self.backup_perspective is not None:
                    self.space.region_3d.view_perspective = self.backup_perspective
                if self.backup_shading is not None:
                    try:
                        self.space.shading.type = self.backup_shading
                    except Exception:
                        pass

        # restore door rotations
        try:
            interact_mod.restore_doors(self)
        except Exception:
            pass

        # clear collision
        self.collision.clear()

        # cursor
        try:
            if self.window is not None:
                self.window.cursor_modal_set("DEFAULT")
        except Exception:
            pass

        self.active = False
        self.request_stop = False
        self.operator = None
        self.context = None
        self.player_state = None
        self.physics = None
        self.focus = None
        self.menu_open = False
        self.menu_items = []
        self.menu_stack = []
        self.menu_index = 0
        self.manual_pause = False
        self.info_popup = None
        self.toast_msg = ""
        self.door_backup = {}
        self.saved_positions = []
        self.backup_camera = None
        self.backup_perspective = None
        self.backup_shading = None

    def emergency_cleanup(self):
        """Best-effort cleanup on file load / unexpected state."""
        try:
            if self.active or self.rig is not None or self._draw_handle is not None:
                self.finish(getattr(self, "context", None) or bpy.context)
        except Exception:
            pass
        # remove orphan temp objects
        try:
            for obj in list(bpy.data.objects):
                if obj.name.startswith("EXPLORER_") and obj.name not in ("EXPLORER_SPAWN",):
                    try:
                        bpy.data.objects.remove(obj, do_unlink=True)
                    except Exception:
                        pass
        except Exception:
            pass


ENGINE = ExplorerEngine()
