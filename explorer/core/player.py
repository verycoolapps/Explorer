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

"""First-person player physics: capsule, axis-separated movement, step-up."""

import math

from mathutils import Vector

HORIZONTAL_KINDS = {"solid"}
GROUND_KINDS = {"solid", "walkable"}


class PlayerState:
    def __init__(self, settings):
        self.pos = Vector((0.0, 0.0, 0.0))       # feet position
        self.vel = Vector((0.0, 0.0, 0.0))
        self.yaw = 0.0
        self.pitch = 0.0
        self.grounded = False
        self.crouching = False
        self.height_cur = settings.player_height
        self.keys = set()
        self._jump_was_down = False

    def eye_pos(self, settings):
        eye = min(settings.eye_height, self.height_cur - 0.05)
        return self.pos + Vector((0.0, 0.0, max(0.05, eye)))


class PlayerPhysics:
    def __init__(self, settings, collision, toast=None):
        self.settings = settings
        self.collision = collision
        self.toast = toast or (lambda msg, dur=3.0: None)
        self.bounds_warned = False
        self.ray_heights = [0.22, 0.55, 0.88]
        self._apply_quality()

    def _apply_quality(self):
        q = getattr(self.settings, "quality", "MEDIUM")
        counts = {"LOW": 2, "MEDIUM": 3, "HIGH": 5}
        n = counts.get(q, 3)
        base = [0.15, 0.32, 0.5, 0.68, 0.85, 0.95]
        self.ray_heights = base[:n] if n <= len(base) else base + [0.5] * (n - len(base))

    # ------------------------------------------------------------------ queries
    def forward_vec(self):
        yaw, pitch = self.state.yaw, self.state.pitch
        cp = math.cos(pitch)
        return Vector((-math.sin(yaw) * cp, -math.cos(yaw) * cp, math.sin(pitch)))

    def right_vec(self):
        yaw = self.state.yaw
        return Vector((-math.cos(yaw), math.sin(yaw), 0.0))

    # ---------------------------------------------------------------- capsule
    def capsule_free(self, feet, height=None):
        """True if a capsule of player radius fits at feet position."""
        s = self.settings
        height = height or self.state.height_cur
        r = s.player_radius
        center = feet + Vector((0.0, 0.0, height * 0.5))
        # check vertical column at several heights against 'solid' only
        for frac in (0.15, 0.4, 0.65, 0.9):
            p = feet + Vector((0.0, 0.0, height * frac))
            for axis in (Vector((r, 0, 0)), Vector((0, r, 0)), Vector((-r * 0.7, 0, 0)), Vector((0, -r * 0.7, 0))):
                hit = self.collision.raycast(p, axis, r * 1.05, kinds={"solid"})
                if hit is not None and hit["dist"] < r * 1.02:
                    return False
        return True

    def _ground_below(self, pos, max_dist):
        hit = self.collision.raycast(pos + Vector((0, 0, 0.05)), Vector((0, 0, -1)), max_dist, kinds=GROUND_KINDS)
        return hit

    # ------------------------------------------------------------------ update
    def update(self, dt, state: PlayerState):
        self.state = state
        s = self.settings
        pos = state.pos
        vel = state.vel

        # ---------------- desired horizontal velocity (yaw-relative WASD)
        wish = Vector((0.0, 0.0, 0.0))
        fwd = Vector((-math.sin(state.yaw), -math.cos(state.yaw), 0.0))
        right = Vector((-math.cos(state.yaw), math.sin(state.yaw), 0.0))
        if not s.enable_crouch and state.crouching:
            state.crouching = False
        keys = state.keys
        if "W" in keys or "UP" in keys:
            wish += fwd
        if "S" in keys or "DOWN" in keys:
            wish -= fwd
        if "D" in keys or "RIGHT" in keys:
            wish += right
        if "A" in keys or "LEFT" in keys:
            wish -= right
        if wish.length > 1e-6:
            wish.normalize()

        speed = s.walk_speed
        if s.enable_sprint and "SHIFT" in keys:
            speed = s.run_speed
        if s.enable_crouch and state.crouching:
            speed = s.crouch_speed
        target = wish * speed
        k = 1.0 - math.exp(-14.0 * dt)
        vel.x += (target.x - vel.x) * k
        vel.y += (target.y - vel.y) * k
        # no residual slide: kill leftover horizontal speed once input is released
        hspeed = math.hypot(vel.x, vel.y)
        if wish.length < 1e-6 and hspeed < 0.15:
            vel.x = 0.0
            vel.y = 0.0

        # ---------------- crouch height lerp + headroom check to stand
        if s.enable_crouch:
            if state.crouching and state.height_cur > s.crouch_height + 0.01:
                state.height_cur = max(s.crouch_height, state.height_cur - dt * 4.0)
            elif not state.crouching and state.height_cur < s.player_height - 0.01:
                new_h = min(s.player_height, state.height_cur + dt * 4.0)
                test_feet = pos + Vector((0, 0, 0.02))
                if self.capsule_free(test_feet, new_h):
                    state.height_cur = new_h

        # ---------------- jump
        jump_down = "SPACE" in keys
        if s.enable_jump and jump_down and not state._jump_was_down and state.grounded:
            vel.z = math.sqrt(2.0 * s.gravity * s.jump_height)
            state.grounded = False
        state._jump_was_down = jump_down

        # ---------------- gravity
        if s.enable_gravity:
            vel.z -= s.gravity * dt
            if vel.z < -40.0:
                vel.z = -40.0
        else:
            vel.z = 0.0

        # ---------------- horizontal axis-separated movement (may step up in z)
        new_x, new_y, step_z = self._move_horizontal(pos, vel, dt)

        # ---------------- vertical movement
        new_z, landed = self._move_vertical(Vector((new_x, new_y, step_z)), vel, dt, state)

        new_pos = Vector((new_x, new_y, new_z))

        # ---------------- world bounds
        if s.world_bounds > 0:
            b = s.world_bounds
            if abs(new_pos.x) > b or abs(new_pos.y) > b:
                new_pos.x = max(-b, min(b, new_pos.x))
                new_pos.y = max(-b, min(b, new_pos.y))
                if not self.bounds_warned:
                    self.bounds_warned = True
                    self.toast("World bounds reached", 2.0)

        state.pos = new_pos
        state.vel = vel
        state.grounded = landed or state.grounded and vel.z <= 0.05 and self._on_ground(new_pos)
        return state

    def _on_ground(self, pos):
        hit = self._ground_below(pos, 0.12)
        return hit is not None and hit["dist"] <= 0.12

    # ------------------------------------------------------- horizontal axis
    def _move_horizontal(self, pos, vel, dt):
        dx = vel.x * dt
        dy = vel.y * dt
        s = self.settings
        height = self.state.height_cur
        r = s.player_radius

        def blocked_axis(np):
            return not self.capsule_free(np, height)

        nx = pos.x + dx
        ny = pos.y + dy

        nz = pos.z
        if abs(dx) > 1e-9:
            cand = Vector((nx, pos.y, pos.z))
            if blocked_axis(cand):
                allowed = self._allowed_delta(pos, Vector((dx, 0, 0)), pos.z, height)
                cand = Vector((pos.x + allowed, pos.y, pos.z))
                if blocked_axis(cand):
                    stepped = self._try_step(pos, Vector((dx, 0, 0)), height)
                    if stepped is not None:
                        cand = stepped
                    else:
                        cand = Vector((pos.x, pos.y, pos.z))
            nx = cand.x
            ny = cand.y
            nz = cand.z

        if abs(dy) > 1e-9:
            cand = Vector((nx, pos.y + dy, nz))
            if blocked_axis(cand):
                allowed = self._allowed_delta(Vector((nx, pos.y, nz)), Vector((0, dy, 0)), nz, height)
                cand = Vector((nx, pos.y + allowed, nz))
                if blocked_axis(cand):
                    stepped = self._try_step(Vector((nx, pos.y, nz)), Vector((0, dy, 0)), height)
                    if stepped is not None:
                        cand = stepped
                    else:
                        cand = Vector((pos.x, pos.y, pos.z))
            nx = cand.x
            ny = cand.y
            nz = cand.z

        return nx, ny, nz

    def _allowed_delta(self, base, delta, z, height):
        """Max allowed component of delta before a 'solid' hit at ray heights."""
        r = self.settings.player_radius
        length = delta.length
        if length < 1e-9:
            return 0.0
        direction = delta.normalized()
        allowed = length
        for frac in self.ray_heights:
            p = base + Vector((0, 0, height * frac))
            hit = self.collision.raycast(p, direction, length + r + 0.05, kinds=HORIZONTAL_KINDS)
            if hit is not None:
                d = max(0.0, hit["dist"] - r - 0.02)
                allowed = min(allowed, d)
        return allowed

    def _try_step(self, base, delta, height):
        """Step-up assist: try full delta lifted by step_height, land on ground below."""
        s = self.settings
        for lift in (s.step_height, s.step_height * 0.6, 0.12):
            cand = base + delta + Vector((0, 0, lift))
            if not self.capsule_free(cand, height):
                continue
            # find ground below the lifted candidate and stand on it
            g = self._ground_below(cand, lift + 0.6)
            if g is None or g["dist"] > lift + 0.6:
                continue
            if g["normal"].z < 0.4:
                continue
            # ray starts at cand.z + 0.05
            ground_z = cand.z + 0.05 - g["dist"]
            rise = ground_z - base.z
            if -0.05 <= rise <= s.step_height + 0.05:
                return Vector((cand.x, cand.y, ground_z + 0.001))
        return None

    # ---------------------------------------------------------- vertical axis
    def _move_vertical(self, pos, vel, dt, state):
        s = self.settings
        z = pos.z
        new_z = z + vel.z * dt
        grounded = state.grounded
        r = s.player_radius

        # ceiling check when rising
        if vel.z > 0:
            head = pos + Vector((0, 0, state.height_cur))
            hit = self.collision.raycast(head + Vector((0, 0, 0.05)), Vector((0, 0, 1)), vel.z * dt + 0.1, kinds=HORIZONTAL_KINDS | {"walkable"})
            if hit is not None and hit["dist"] <= vel.z * dt + 0.1:
                new_z = min(new_z, head.z + hit["dist"] - state.height_cur - 0.02 + 0.1)
                vel.z = min(vel.z, 0.0)

        # ground check
        # ground check: ray starts at probe + 0.05, so surface z = start_z - dist
        probe = Vector((pos.x, pos.y, new_z))
        ray_start_z = new_z + 0.05
        fall_dist = max(0.45, abs(vel.z) * dt + 0.45) if vel.z < -0.5 else 0.45
        hit = self._ground_below(probe, fall_dist)
        landed = False
        if hit is not None:
            # only count upward-facing surfaces as ground (prevents landing on ceiling/underside)
            if hit["normal"].z < 0.4:
                hit = None
        if hit is not None:
            ground_z = ray_start_z - hit["dist"]
            if vel.z <= 0.05 and new_z <= ground_z + 0.03:
                new_z = ground_z + 0.001
                vel.z = 0.0
                landed = True
            elif grounded and vel.z <= 0.2:
                dz = ground_z - z
                if 0.0 <= dz <= s.step_height:
                    new_z = ground_z + 0.001
                elif -s.step_height <= dz < 0.0 and vel.z <= 0.0:
                    pass
        return new_z, landed

    # ------------------------------------------------------------- spawn util
    def spawn_point(self, preferred):
        """Validate/repair a spawn position. Returns feet Vector or None.

        The preferred point may sit inside geometry or far above ground, so
        we probe downward from progressively higher origins and accept only
        surfaces at or below the candidate (never a ceiling/roof above it).
        """
        s = self.settings
        for lift in [0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0]:
            cand = preferred + Vector((0, 0, lift))
            g = self.collision.raycast(
                cand + Vector((0, 0, 2.0)), Vector((0, 0, -1)), 8.0,
                kinds=GROUND_KINDS,
            )
            if g is None:
                continue
            # ray starts at cand.z + 2.0 + 0.05; surface z = start - dist
            surface_z = cand.z + 2.05 - g["dist"]
            if surface_z > cand.z + 0.6:
                continue  # nearest surface is a ceiling/roof above the candidate
            feet = Vector((cand.x, cand.y, surface_z + 0.001))
            if self.capsule_free(feet, s.player_height):
                return feet
        return None
