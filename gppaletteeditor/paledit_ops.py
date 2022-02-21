import bpy
import numpy as np
from .. gpcolorpicker.picker_settings import GPCOLORPICKER_settings
from .. gpcolorpicker.picker_interactions import get_selected_mat_id, CachedData
from .. gpcolorpicker.picker_draw import draw_callback_px
import time

### ----------------- Operator definition
class GPCOLORPICKER_OT_paletteEditor(bpy.types.Operator):
    bl_idname = "gpencil.palette_edit"
    bl_label = "GP Palette Editor"  

    @classmethod
    def poll(cls, context):
        return True


    def modal(self, context, event):
        context.area.tag_redraw()  

        def mat_selected_in_range():
            i = self.mat_selected
            return (i >= 0) and (i < self.cached_data.mat_nb)

        if event.type == 'MOUSEMOVE':
            self.mat_selected = get_selected_mat_id(event,self.region_dim, self.origin, self.cached_data.mat_nb, \
                                             self.settings.interaction_radius, self.cached_data.custom_angles)

        elif (event.type == 'LEFTMOUSE'):
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'}

        elif (event.type == self.settings.switch_key) and (event.value == 'PRESS'):
            bpy.context.scene.gpmatpalettes.next()
            self.cached_data.refresh()

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}

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

        # Setting handlers
        mhandle = context.window_manager.modal_handler_add(self)
        if not mhandle:
            return {'CANCELLED'}  

        self._handle = context.space_data.draw_handler_add(draw_callback_px, \
                                (self,context,self.cached_data,self.settings), \
                                                        'WINDOW', 'POST_PIXEL')
        return {'RUNNING_MODAL'}    