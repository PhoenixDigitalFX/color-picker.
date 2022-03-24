# Useful functions for palette editor related interactions 
import bpy
import numpy as np
from math import pi, cos, sin, atan2
from . paledit_maths import is_in_boundaries, pol2cart
from .. gpcolorpicker import picker_cache as gpcp

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
    def on_click_press(self, op, cache, settings, context, pos):
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

    def is_in_selection(self, op, cache, settings, pos):
        return (op.mat_selected == self.id) \
            and (super().is_in_selection(op, cache, settings, pos))

    def refresh(self, cache, settings):
        self.th = cache.angles[self.id]
        udir = np.asarray([cos(self.th),sin(self.th)])
        self.org = settings.mat_centers_radius*udir
        self.rds = settings.mat_radius*settings.selection_ratio
    
    def on_click_press(self, op, cache, settings, context, pos):
        self.has_moved = False
    
    def on_mouse_move(self, op, cache, settings, pos):
        nth = atan2(pos[1], pos[0]) % (2*pi)
        
        cache.angles[self.id] = nth
        cache.is_custom_angle[self.id] = True
        self.has_moved = True

    def on_click_release(self, op, cache, settings, context):
        if not self.has_moved:
            op.mat_locked = not op.mat_locked
            return

        self.refresh(cache, settings)
        op.write_cache_in_palette(context)
    
''' Move Material pickline in the Palette Editor '''
class MoveMaterialPickerInteraction(RadialInteractionArea):
    def __init__(self, op, cache, settings, mat_id, pln_id):
        self.mark = SelectionMark()
        self.mark.color = settings.mark_color
        self.mark.radius = settings.mat_line_width
        self.mat_id = mat_id
        self.pln_id = pln_id
        self.overall_rds = settings.mat_centers_radius 
        self.overall_rds -= settings.mat_radius
        self.name = cache.materials[self.mat_id].name
        self.refresh(cache, settings)

    def is_in_selection(self, op, cache, settings, pos):
        return (op.mat_selected == self.mat_id) \
            and (super().is_in_selection(op, cache, settings, pos))

    def refresh(self, cache, settings):
        o = cache.pick_origins[self.mat_id][self.pln_id]
        self.org = o * self.overall_rds
        self.rds = settings.mat_radius*0.75
        self.mark.position = self.org
    
    def on_mouse_move(self, op, cache, settings, pos): 
        cache.pick_origins[self.mat_id][self.pln_id] = pos/self.overall_rds
        self.refresh(cache, settings)

    def on_click_release(self, op, cache, settings, context):
        pos = cache.pick_origins[self.mat_id][self.pln_id][0:2]
        if np.linalg.norm(pos) > 1.:
            cache.pick_origins[self.mat_id].pop(self.pln_id)
        op.write_cache_in_palette(context)

''' Add Material pickline in the Palette Editor '''
class AddMaterialPickerInteraction(MoveMaterialPickerInteraction):
    def __init__(self, op, cache, settings, id):
        self.was_added = False
        super().__init__(op, cache, settings, id, -1)

    def refresh(self, cache, settings):
        if not self.was_added:
            self.org = pol2cart(self.overall_rds, cache.angles[self.mat_id])
            self.rds = settings.mat_radius*0.75
            self.mark.position = self.org
        else:
            super().refresh(cache, settings)
    
    def on_click_press(self, op, cache, settings, context, pos):
        cache.pick_origins[self.mat_id].append(self.org)
        self.was_added = True

    def on_click_release(self, op, cache, settings, context):
        super().on_click_release(op, cache, settings, context)
        self.was_added = False

''' Removes Material from the active palette '''
class RemoveMaterialInteraction(RadialInteractionArea):
    def __init__(self, op, cache, settings, id):
        self.id = id
        self.mark = SelectionMark()
        self.mark.color = settings.mark_color
        self.mark.radius = settings.mat_radius*0.25
        self.mark.type = 0
        self.refresh(cache, settings)

    def is_in_selection(self, op, cache, settings, pos):
        return (op.mat_selected == self.id) \
            and (super().is_in_selection(op, cache, settings, pos))

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
        if (op.mat_locked):
            return False

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

    def is_in_selection(self, op, cache, settings, pos):
        return (not op.mat_locked) \
            and (super().is_in_selection(op, cache, settings, pos))

    def on_click_release(self, op, cache, settings, context):
        bpy.ops.scene.edit_palette_image('INVOKE_DEFAULT')

''' Adds Brush in material '''
class AddBrushInteraction(RadialInteractionArea):
    def __init__(self, op, cache, settings, id):
        self.id = id
        self.mark = SelectionMark()
        self.mark.color = settings.mark_color
        self.mark.radius = settings.mat_radius*0.25
        self.mark.type = 1
        self.refresh(cache, settings)

    def refresh(self, cache, settings):
        self.th = cache.angles[self.id]
        udir = np.asarray([cos(self.th),sin(self.th)])
        overall_rds = settings.mat_centers_radius+2.5*settings.mat_radius
        nbrushes= len(cache.brushes[self.id])
        overall_rds += nbrushes*settings.brush_radius*2.5
        self.org = overall_rds*udir
        self.rds = settings.brush_radius
        self.mark.position = self.org
    
    def on_click_release(self, op, cache, settings, context):
        bpy.ops.scene.add_brush_mat('INVOKE_DEFAULT', mat_index=self.id)


''' Moves Brush in material '''
class MoveBrushInteraction(RadialInteractionArea):
    def __init__(self, op, cache, settings, mat_id, bsh_id):
        self.mat_id = mat_id
        self.bsh_id = bsh_id
        self.refresh(cache, settings)

    def is_in_selection(self, op, cache, settings, pos):
        return (op.mat_selected == self.mat_id) \
            and (super().is_in_selection(op, cache, settings, pos))

    def refresh(self, cache, settings):
        if self.bsh_id < 0:
            print(f"ERROR : Brush {self.bsh_id} not assigned to material {self.mat_id}")
            return            
        self.th = cache.angles[self.mat_id]
        udir = np.asarray([cos(self.th),sin(self.th)])       

        R = settings.overall_brush_radius
        r = 2*settings.brush_radius + settings.brush_interrad

        x = cache.brushes_pos[self.mat_id][self.bsh_id]
        self.org = (R + (x+0.5)*r)*udir
        self.rds = settings.brush_radius

    def on_click_press(self, op, cache, settings, context, pos):    
        self.init_pos = np.linalg.norm(pos)

    def on_mouse_move(self, op, cache, settings, pos):
        r = 2*settings.brush_radius + settings.brush_interrad
        dpos = (np.linalg.norm(pos) - self.init_pos)/r

        cpos = cache.brushes_pos[self.mat_id][self.bsh_id] + dpos
        if cpos == int(cpos):
            cpos += 0.001

        nbrushes = len(cache.brushes[self.mat_id])
        if cpos > nbrushes:
            cpos = nbrushes

        cache.brushes_pos[self.mat_id][self.bsh_id] = cpos
        self.init_pos = np.linalg.norm(pos)

    def on_click_release(self, op, cache, settings, context):      
        self.refresh(cache, settings)
        op.write_cache_in_palette(context)