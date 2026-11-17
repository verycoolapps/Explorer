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
# subject to civil and civil and criminal prosecution under Indonesian
# Law No. 28/2014 on Copyright and applicable international IP treaties.
#
# PROHIBITED: Copy · Redistribute · Modify · Decompile · Sublicense
# FOR LICENSING: wa.me/6281519250845
# =============================================================================

"""Camera rig: first/third-person camera, player marker, flashlight."""

import bpy
from mathutils import Vector


class CameraRig:
    def __init__(self, engine):
        self.engine = engine
        self.cam = None
        self.marker = None
        self.flash = None
        self.tp_distance = 4.0
        self._base_rot_mode = None

    # ------------------------------------------------------------------ create
    def create(self, scene, settings):
        # temp camera copying lens/clip of scene camera
        src = scene.camera
        cam_data = bpy.data.cameras.new("EXPLORER_Camera")
        if src is not None and src.data is not None:
            cam_data.lens = src.data.lens
            cam_data.sensor_width = src.data.sensor_width
            cam_data.clip_end = src.data.clip_end
        cam_data.clip_start = 0.05
        cam_data.type = "PERSP"
        self.cam = bpy.data.objects.new("EXPLORER_Camera", cam_data)
        scene.collection.objects.link(self.cam)

        # player marker cylinder
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.28, depth=1.7, location=(0, 0, 0.85))
        self.marker = bpy.context.active_object
        if self.marker is not None:
            self.marker.name = "EXPLORER_Player"
            self.marker.display_type = "WIRE"
            self.marker.hide_render = True
            self.marker.hide_set(False)
            if self.marker.data is not None and hasattr(self.marker.data, "color"):
                self.marker.color = (0.2, 0.9, 1.0, 1.0)
            for c in self.marker.users_collection:
                pass

        # flashlight spot
        light_data = bpy.data.lights.new("EXPLORER_Flash", type="SPOT")
        light_data.energy = 750.0
        light_data.spot_size = 0.9
        light_data.spot_blend = 0.4
        light_data.shadow_soft_size = 0.1
        self.flash = bpy.data.objects.new("EXPLORER_Flash", light_data)
        scene.collection.objects.link(self.flash)
        self.flash.hide_render = False
        self.flash.data.use_shadow = settings.quality != "LOW"

    # ------------------------------------------------------------------ update
    def update(self, context, dt):
        s = self.engine.settings
        state = self.engine.player_state
        if self.cam is None:
            return
        eye = state.eye_pos(s)
        mode = s.camera_mode
        if mode == "TP":
            self._update_tp(context, eye, state)
        else:
            self.cam.location = eye
            self.cam.rotation_mode = "QUATERNION"
            self.cam.rotation_quaternion = self.engine.look_quat()
            if self.marker is not None:
                self.marker.location = state.pos + Vector((0, 0, state.height_cur * 0.5))
                self.marker.hide_set(False)
        # flashlight follows camera
        if self.flash is not None:
            self.flash.location = self.cam.location
            self.flash.rotation_quaternion = self.cam.rotation_quaternion
        # marker visibility per mode
        if self.marker is not None:
            self.marker.hide_set(mode != "FP")

    def _update_tp(self, context, eye, state):
        cam = self.cam
        cam.rotation_mode = "QUATERNION"
        back = -self.engine.forward_vec()
        # pull-in raycast from head backwards
        dist = self.tp_distance
        hit = self.engine.collision.raycast(eye, back, self.tp_distance + 0.3)
        if hit is not None:
            dist = max(0.5, hit["dist"] - 0.25)
        desired = eye + back * dist
        cam.location = desired
        look_target = eye + self.engine.forward_vec() * 2.0
        direction = look_target - desired
        if direction.length > 1e-6:
            cam.rotation_quaternion = direction.to_track_quat("-Z", "Y")
        if self.marker is not None:
            self.marker.location = state.pos + Vector((0, 0, state.height_cur * 0.5))
            self.marker.hide_set(False)

    # ------------------------------------------------------------------ finish
    def remove_temp(self, scene):
        for obj in (self.cam, self.marker, self.flash):
            if obj is not None:
                try:
                    bpy.data.objects.remove(obj, do_unlink=True)
                except Exception:
                    pass
        self.cam = None
        self.marker = None
        self.flash = None

    def wheel_zoom(self, delta):
        self.tp_distance = max(1.0, min(8.0, self.tp_distance + delta * 0.5))
