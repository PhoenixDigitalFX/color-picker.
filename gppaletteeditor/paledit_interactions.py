import bpy
import numpy as np
from math import pi, cos, sin, atan2
from . paledit_maths import is_in_boundaries

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
        if not cache.use_custom_angles():
            self.th = self.id*2*pi/cache.mat_nb
        else:
            self.th = cache.custom_angles[self.id]
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
            cache.custom_angles = [ i*2*pi/nmt for i in range(nmt) ]
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

    def refresh_position(self, cache, settings):
        if not cache.use_custom_angles():
            self.th = self.id*2*pi/cache.mat_nb
        else:
            self.th = cache.custom_angles[self.id]
        udir = np.asarray([cos(self.th),sin(self.th)])
        self.org = settings.mat_centers_radius*udir
        self.rds = settings.selected_radius + settings.mat_line_width
    
    def stop_running(self, op, cache, settings, context):
        self.refresh_position(cache, settings)
        op.write_cache_in_palette(context)