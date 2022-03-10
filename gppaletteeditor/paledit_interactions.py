# Useful functions for palette editor related interactions 
import bpy
import numpy as np
from math import pi, cos, sin, atan2
from . paledit_maths import is_in_boundaries, pol2cart
from .. gpcolorpicker import picker_interactions as gpcp

''' Simple override of the picker's cache data structure ''' 
class CachedData(gpcp.CachedData):
    pass
   

''' -------- INTERACTION AREAS -------- '''

''' Potential marks to be drawn in the palette editor icon '''
class SelectionMark:
    def __init__(self):
        self.position = np.zeros(2)
        self.color = np.zeros(4)
        self.radius = 1
        # Type of mark
        # 0 : dot
        # 1 : cross
        # 2 : pencil (not used because ugly)
        self.type = 0 


''' Abstract Interaction Area class '''
class InteractionArea():
    mark=None

    ''' Called at each draw if no interaction is running '''
    def refresh(self, cache, settings):
        pass

    ''' Checks if the given position is withing the selection area of the interaction '''
    def is_in_selection(self, op, cache, settings, pos):
        return False

    ''' Called when interaction area is not in selection '''
    def display_not_in_selection(self, op, cache, settings, pos):
        pass

    ''' Called when interaction area is in selection '''
    def display_in_selection(self, op, cache, settings, pos):
        pass
    
    ''' Called when interaction area is in selection and the mouse left click is pressed '''
    def on_click_press(self, op, cache, settings, context):
        pass

    ''' Called when interaction area is running and the mouse is moved (left click still pressed) '''
    def on_mouse_move(self, op, cache, settings, pos):
        pass

    ''' Called when interaction area is running and the mouse left click is released '''
    def on_click_release(self, op, cache, settings, context):
        pass

    ''' Called when cancellation key is called while the interaction is running '''
    def cancel_run(self, op, cache, settings, context):
        pass

    ''' Checks if the interaction area has a mark to be drawn if in selection '''
    def has_mark(self):
        return not (self.mark is None)

''' Override for circle based interaction areas '''
class RadialInteractionArea(InteractionArea):
    def __init__(self, origin, radius):
        self.org = origin
        self.rds = radius

    def is_in_selection(self, op, cache, settings, pos):
        return np.linalg.norm(pos-self.org) < self.rds 


''' Move Material position in the Palette Editor '''
class MoveMaterialAngleInteraction(RadialInteractionArea):
    def __init__(self, op, cache, settings, id):
        self.id = id
        self.refresh(cache, settings)

    def refresh(self, cache, settings):
        self.th = cache.angles[self.id]
        udir = np.asarray([cos(self.th),sin(self.th)])
        self.org = settings.mat_centers_radius*udir
        self.rds = settings.selected_radius

    def display_not_in_selection(self, op, cache, settings, pos):
        if (op.mat_selected == self.id):
            op.mat_selected = -1

    def display_in_selection(self, op, cache, settings, pos):
        op.mat_selected = self.id
    
    def on_mouse_move(self, op, cache, settings, pos):
        nth = atan2(pos[1], pos[0]) % (2*pi)
        
        cache.angles[self.id] = nth
        cache.is_custom_angle[self.id] = True
    
    def on_click_release(self, op, cache, settings, context):
        self.refresh(cache, settings)
        op.write_cache_in_palette(context)
    
''' Move Material pickline in the Palette Editor '''
class MoveMaterialPickerInteraction(RadialInteractionArea):
    def __init__(self, op, cache, settings, id):
        self.mark = SelectionMark()
        self.mark.color = settings.mark_color
        self.mark.radius = settings.mat_line_width
        self.id = id
        self.overall_rds = settings.mat_centers_radius 
        self.overall_rds -= settings.mat_radius
        self.name = cache.materials[self.id].name
        self.refresh(cache, settings)

    def init_org(self, cache, _, i, init_z=True):
        org = pol2cart(self.overall_rds, cache.angles[i])
        if init_z:
            return np.append(org, 0)
        return org

    def refresh(self, cache, settings):
        if (cache.pick_origins[self.id][2] == 0):
            self.org = self.init_org(cache, settings, self.id, False)
        else:
            o = cache.pick_origins[self.id]
            self.org = o[0:2] * self.overall_rds
        self.rds = settings.mat_radius*0.75
        self.mark.position = self.org
    
    def on_mouse_move(self, op, cache, settings, pos):     
        cache.pick_origins[self.id][0:2] = pos/self.overall_rds
        cache.pick_origins[self.id][2] = 1
        self.refresh(cache, settings)

    def on_click_release(self, op, cache, settings, context):
        pos = cache.pick_origins[self.id][0:2]
        if np.linalg.norm(pos) > 1.:
            cache.pick_origins[self.id] = self.init_org(cache, settings, self.id)/self.overall_rds
        self.refresh(cache, settings)
        op.write_cache_in_palette(context)

''' Removes Material from the active palette '''
class RemoveMaterialInteraction(RadialInteractionArea):
    def __init__(self, op, cache, settings, id):
        self.id = id
        self.mark = SelectionMark()
        self.mark.color = settings.mark_color
        self.mark.radius = settings.mat_radius*0.25
        self.mark.type = 0
        self.refresh(cache, settings)

    def refresh(self, cache, settings):
        self.th = cache.angles[self.id]
        udir = np.asarray([cos(self.th),sin(self.th)])
        overall_rds = settings.mat_centers_radius+1.5*settings.mat_radius
        self.org = overall_rds*udir
        self.rds = settings.mat_radius
        self.mark.position = self.org
    
    def on_click_release(self, op, cache, settings, context):
        bpy.ops.scene.remove_mat_palette('INVOKE_DEFAULT', mat_index=self.id)

''' Adds Material in the active palette '''
class AddMaterialInteraction(InteractionArea):
    def __init__(self, op, cache, settings):
        self.th = -1
        self.mark = SelectionMark()
        self.mark.color = settings.mark_color
        self.mark.radius = settings.mat_radius*0.5
        self.mark.type = 1 # cross-like mark

    def is_in_selection(self, op, cache, settings, pos):
        R = settings.mat_centers_radius
        r = settings.mat_radius + settings.mat_line_width
        d = np.linalg.norm(pos)
        self.th = atan2(pos[1], pos[0]) % (2*pi)
        self.mark.position = pol2cart(R, self.th)

        if (d > R + r) or (d < R - r) :
            return False

        for a in cache.angles:
            if abs(a - self.th) < r/R:
                return False

        return True
    
    def on_click_release(self, op, cache, settings, context):
        bpy.ops.scene.add_mat_palette('INVOKE_DEFAULT', angle=self.th)


''' Adds Palette in the collection '''
class NewPaletteInteraction(RadialInteractionArea):
    def __init__(self, op, settings):
        self.org = np.zeros(2)
        self.rds = settings.mc_outer_radius
        self.mark = SelectionMark()
        self.mark.color[0:3] = settings.mc_line_color[0:3]
        self.mark.color[3] = 0.5
        self.mark.radius = settings.mc_inner_radius*0.5
        self.mark.type = 1 # cross-like mark
        self.mark.position = self.org

    def on_click_release(self, op, cache, settings, context):
        bpy.ops.scene.new_palette('INVOKE_DEFAULT')

''' Edits Image of the active Palette '''
class EditImageInteraction(RadialInteractionArea):
    def __init__(self, op, cache, settings):
        self.rds = settings.mc_inner_radius*0.25
        self.org = np.zeros(2)

        self.mark = SelectionMark()
        self.mark.position = self.org
        self.mark.color = settings.mc_fill_color
        self.mark.radius = self.rds*0.3
        self.mark.type = 0

    def on_click_release(self, op, cache, settings, context):
        bpy.ops.scene.edit_palette_image('INVOKE_DEFAULT')

