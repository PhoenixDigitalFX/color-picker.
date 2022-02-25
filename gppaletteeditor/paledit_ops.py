from calendar import c
import bpy
import numpy as np
from .. gpcolorpicker.picker_settings import GPCOLORPICKER_settings
from .. gpcolorpicker.picker_interactions import *
from . paledit_draw import draw_callback_px
from . paledit_interactions import *

### ----------------- Operator definition
class GPCOLORPICKER_OT_paletteEditor(bpy.types.Operator):
    bl_idname = "gpencil.palette_edit"
    bl_label = "GP Palette Editor"  

    @classmethod
    def poll(cls, context):
        return True

    def write_cache_in_palette(self, context):
        pal = context.scene.gpmatpalettes.active()
        cache = self.cached_data
        if not cache.from_palette:
            return

        nmt = cache.mat_nb
        for i in range(nmt):
            mpos = pal.materials[i].pos_in_picker
            mpos.has_pick_line = (cache.pick_origins[i][2] > 0)
            if mpos.has_pick_line :
                mpos.ox = cache.pick_origins[i][0]
                mpos.oy = cache.pick_origins[i][1]

        pal.materials.foreach_set("custom_angle", cache.custom_angles)

    def modal(self, context, event):
        context.area.tag_redraw()  
        # Find mouse position
        mouse_pos = np.asarray([event.mouse_region_x,event.mouse_region_y])
        mouse_local = mouse_pos - 0.5*self.region_dim - self.origin

        cache = self.cached_data
        stgs = self.settings

        if event.type == 'MOUSEMOVE':
            if self.running_interaction:
                self.running_interaction.run(self, cache, stgs, mouse_local)
            else:
                for itar in self.interaction_areas:
                    if itar.is_in_selection(mouse_local):
                        itar.display_in_selection(self, cache, stgs, mouse_local)
                    else:
                        itar.display_not_in_selection(self, cache, stgs, mouse_local)

        elif (event.type == 'LEFTMOUSE') and (event.value == 'PRESS'):
            for itar in self.interaction_areas:
                if itar.is_in_selection(mouse_local):
                    itar.start_running(self, cache, stgs, context)
                    self.running_interaction = itar
                    break

        elif (event.type == 'LEFTMOUSE') and (event.value == 'RELEASE'):
            if self.running_interaction:
                self.running_interaction.stop_running(self, cache, stgs, context)
                self.running_interaction = None
            
        elif (event.type == self.settings.switch_key) and (event.value == 'PRESS'):
            if self.running_interaction:
                self.running_interaction.cancel_run(self, cache, stgs, context)
                self.running_interaction = None

            bpy.context.scene.gpmatpalettes.next()
            self.cached_data.refresh()
            self.init_interaction_areas(context)
            self.mat_selected = get_selected_mat_id(event,self.region_dim, self.origin, self.cached_data.mat_nb, \
                              self.settings.interaction_radius, self.cached_data.custom_angles)

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            if self.running_interaction:
                self.running_interaction.cancel_run(self, cache, stgs, context)
                self.running_interaction = None

            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'}
        
        return {'RUNNING_MODAL'}

    def init_interaction_areas(self, context):
        self.mat_selected = -1
        cache = self.cached_data
        stgs = self.settings

        self.interaction_areas = []
        for i in range(self.cached_data.mat_nb):         
            self.interaction_areas.append(MoveMaterialPickerInteraction(self, cache, stgs, i))
            self.interaction_areas.append(MoveMaterialAngleInteraction(self, cache, stgs, i))

    def invoke(self, context, event):  
        self.report({'INFO'}, "Entering palette edit mode")

        pname = (__package__).split('.')[0]
        prefs = context.preferences.addons[pname].preferences
        if prefs is None : 
            self.report({'WARNING'}, "Could not load user preferences, running with default values")
        self.settings = GPCOLORPICKER_settings(prefs)  

        gpmp = context.scene.gpmatpalettes.active()
        if (not self.settings.mat_from_active) and (not gpmp):
            self.report({'WARNING'}, "No active palette")
            return {'CANCELLED'}

        # Get event related data
        self.invoke_key = event.type
        self.region_dim = np.asarray([context.region.width,context.region.height])
        self.origin = np.asarray([event.mouse_region_x,event.mouse_region_y]) - 0.5*self.region_dim  

        self.mat_selected = -1  

        # Init Cached Data
        self.cached_data = CachedData(not self.settings.mat_from_active)
        if self.cached_data.mat_nb == 0:
            self.report({'WARNING'}, "No material to pick")

        # Init interactions areas
        self.init_interaction_areas(context)
        self.running_interaction = None

        # Setting handlers
        mhandle = context.window_manager.modal_handler_add(self)
        if not mhandle:
            return {'CANCELLED'}  

        self._handle = context.space_data.draw_handler_add(draw_callback_px, \
                                (self,context,self.cached_data,self.settings), \
                                                        'WINDOW', 'POST_PIXEL')
        return {'RUNNING_MODAL'}    


classes = [GPCOLORPICKER_OT_paletteEditor]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)