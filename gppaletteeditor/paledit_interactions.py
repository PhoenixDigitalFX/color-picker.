import bpy
import numpy as np
from math import pi, cos, sin, atan2
from . paledit_maths import is_in_boundaries, pol2cart
from .. gpcolorpicker import picker_interactions as gpcp

class CachedData(gpcp.CachedData):
    def refresh(self):
        super().refresh()

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
        self.th = cache.angles[self.id]
        udir = np.asarray([cos(self.th),sin(self.th)])
        self.org = settings.mat_centers_radius*udir
        self.rds = settings.selected_radius + settings.mat_line_width

    def display_not_in_selection(self, op, cache, settings, pos):
        if (op.mat_selected == self.id):
            op.mat_selected = -1

    def display_in_selection(self, op, cache, settings, pos):
        op.mat_selected = self.id

    def run(self, op, cache, settings, pos):
        nth = atan2(pos[1], pos[0]) % (2*pi)
        
        cache.angles[self.id] = nth
        cache.is_custom_angle[self.id] = True
    
    def stop_running(self, op, cache, settings, context):
        self.refresh_position(cache, settings)
        op.write_cache_in_palette(context)
    
class MoveMaterialPickerInteraction(RadialInteractionArea):
    def __init__(self, op, cache, settings, id):
        self.id = id
        self.overall_rds = settings.mat_centers_radius - settings.mat_radius
        self.name = cache.materials[self.id].name
        self.refresh_position(cache, settings)

    def init_org(self, cache, _, i, init_z=True):
        org = pol2cart(self.overall_rds, cache.angles[i])
        if init_z:
            return np.append(org, 0)
        return org

    def display_not_in_selection(self, op, _, __, ____):
        if (op.origin_selected == self.id):
            op.origin_selected = -1

    def display_in_selection(self, op, _, __, ___):
        op.origin_selected = self.id

    def refresh_position(self, cache, settings):
        if (cache.pick_origins[self.id][2] == 0):
            self.org = self.init_org(cache, settings, self.id, False)
        else:
            o = cache.pick_origins[self.id]
            self.org = o[0:2] * self.overall_rds
        self.rds = settings.mat_radius*0.5
    
    def run(self, op, cache, _, pos):     
        cache.pick_origins[self.id][0:2] = pos/self.overall_rds
        cache.pick_origins[self.id][2] = 1

    def stop_running(self, op, cache, settings, context):
        pos = cache.pick_origins[self.id][0:2]
        if np.linalg.norm(pos) > 1.:
            cache.pick_origins[self.id] = self.init_org(cache, settings, self.id)/self.overall_rds
        self.refresh_position(cache, settings)
        op.write_cache_in_palette(context)