import bpy
import numpy as np
from math import pi, cos, sin, atan2
from . paledit_maths import is_in_boundaries, pol2cart

class InteractionArea():
    def is_in_selection(self, pos):
        return False

    def display_not_in_selection(self, op, cache, settings, pos):
        pass

    def display_in_selection(self, op, cache, settings, pos):
        pass
    
    def start_running(self, op, cache, settings, context):
        pass
    
    def run(self, op, cache, settings, pos):
        pass

    def stop_running(self, op, cache, settings, context):
        pass

    def cancel_run(self, op, cache, settings, context):
        pass

class RadialInteractionArea(InteractionArea):
    def __init__(self, origin, radius):
        self.org = origin
        self.rds = radius

    def is_in_selection(self, pos):
        return np.linalg.norm(pos-self.org) < self.rds 

class MoveMaterialAngleInteraction(RadialInteractionArea):
    def __init__(self, op, cache, settings, id):
        self.id = id
        self.refresh_position(cache, settings)

    def refresh_position(self, cache, settings):
        self.th = cache.get_mat_angle(self.id)
        udir = np.asarray([cos(self.th),sin(self.th)])
        self.org = settings.mat_centers_radius*udir
        self.rds = settings.selected_radius + settings.mat_line_width

    def display_not_in_selection(self, op, cache, settings, pos):
        if (op.mat_selected == self.id):
            op.mat_selected = -1

    def display_in_selection(self, op, cache, settings, pos):
        op.mat_selected = self.id

    def run(self, op, cache, settings, pos):
        nmt = cache.mat_nb
        if not cache.use_custom_angles():
            cache.custom_angles = [ cache.get_mat_angle(i) for i in range(nmt) ]
        nth = atan2(pos[1], pos[0]) % (2*pi)

        R = settings.mat_centers_radius
        r = settings.mat_radius + settings.mat_line_width
        
        if is_in_boundaries(R, r, cache.custom_angles, self.id, nth):
            cache.custom_angles[self.id] = nth
    
    def stop_running(self, op, cache, settings, context):
        self.refresh_position(cache, settings)
        op.write_cache_in_palette(context)
    
class MoveMaterialPickerInteraction(RadialInteractionArea):
    def __init__(self, op, cache, settings, id):
        self.id = id
        self.refresh_position(cache, settings)

        R = settings.mat_centers_radius - settings.mat_radius
        c_pos = pol2cart(R, cache.get_mat_angle(id))
        print(f"Mat {cache.materials[self.id].name} : init origin {self.org}, center {c_pos}")
    
    def init_org(self, cache, settings, i, init_z=True):
        th = cache.get_mat_angle(i)
        R = settings.mat_centers_radius - settings.mat_radius
        org = pol2cart(R,th)
        if init_z:
            return np.append(org, 0)
        return org

    def refresh_position(self, cache, settings):
        if (not cache.use_pick_lines()) or (cache.pick_origins[self.id][2] == 0):
            self.org = self.init_org(cache, settings, self.id, False)
        else:
            o = cache.pick_origins[self.id]
            self.org = o[0:2]
        self.rds = settings.mat_radius*0.5
    
    def is_in_boundaries(self, settings, pos):
        return True
        return len(pos) < settings.mat_centers_radius

    def run(self, op, cache, settings, pos):
        nmt = cache.mat_nb
        if not cache.use_pick_lines():
            cache.pick_origins = [ self.init_org(cache, settings, i) for i in range(nmt) ]
        
        if self.is_in_boundaries(settings, pos):
            cache.pick_origins[self.id][0:2] = pos
            cache.pick_origins[self.id][2] = 1

    def stop_running(self, op, cache, settings, context):
        self.refresh_position(cache, settings)
        op.write_cache_in_palette(context)

        c_org = False
        if cache.use_pick_lines():
            c_org = cache.pick_origins[self.id]
        print(f"Mat {cache.materials[self.id].name} : moved origin to {self.org}, cache {c_org}")
