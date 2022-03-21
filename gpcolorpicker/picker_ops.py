# GP Color Picker invoke operator
import bpy
import numpy as np
from . picker_draw import draw_callback_px
from . picker_settings import GPCOLORPICKER_settings
from . picker_interactions import get_selected_mat_id, get_selected_brush_id, pick_material, CachedData
import time

class GPCOLORPICKER_OT_wheel(bpy.types.Operator):
    bl_idname = "gpencil.color_pick"
    bl_label = "GP Color Picker"  

    @classmethod
    def poll(cls, context):
        return  (context.area.type == 'VIEW_3D') and \
                (context.mode == 'PAINT_GPENCIL') and \
                (context.active_object is not None) and \
                (context.active_object.type == 'GPENCIL')
    
    # Change the selected material & brush
    def refresh_selections(self, event):
        cache = self.cached_data
        stg = self.settings

        self.mat_selected = get_selected_mat_id(event, self.region_dim, self.origin, cache.mat_nb, \
                                            stg.interaction_radius, cache.angles)
        if self.mat_selected >= 0:
            nb_brush = len(cache.map_bsh[self.mat_selected])
            int_area = stg.mat_centers_radius + stg.mat_radius*stg.selection_ratio
            self.brush_selected = get_selected_brush_id(event, self.region_dim, self.origin, nb_brush, \
                                int_area, stg.brush_radius)
        else:
            self.brush_selected = -1

    def modal(self, context, event):
        context.area.tag_redraw()  

        if event.type == 'MOUSEMOVE':
            self.refresh_selections(event)
        
        elif (event.type == self.settings.switch_key) and (event.value == 'PRESS'):
            # Change the active palette when the switch key is pressed (default: TAB)
            dir = 1
            if event.shift:
                dir = -1
            bpy.context.scene.gpmatpalettes.next(dir)
            self.cached_data.refresh(context)
            self.refresh_selections(event)

        elif ((event.type == self.invoke_key) \
                and (event.value == 'RELEASE') and (self.mat_selected != -1)) \
                    or (event.type == 'LEFTMOUSE'):
            # Change the active material and quit picker when a material is selected
            if pick_material(self.cached_data, context, self.settings, self.mat_selected):   
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                bpy.ops.ed.undo_push()
                return {'FINISHED'}                

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # Cancel execution 
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}
    
    
    ''' May be used for performance issue
        check_time returns the total time passed since the user invoked the picker
    '''
    def check_time(self):
        if self.timeout:
            return
        print("Timer : ", time.time() - self.tsart)
        # we prevent other calls to check_time 
        # (it was mainly used in the draw function which is called continuously)
        self.timeout = True

    def invoke(self, context, event):  
        # Timer initialization
        self.tsart = time.time()
        self.timeout = False

        # Get addon preferences
        pname = (__package__).split('.')[0]
        prefs = context.preferences.addons[pname].preferences
        if prefs is None : 
            self.report({'WARNING'}, "Could not load user preferences, running with default values")

        # Initialize picker appearance settings
        self.settings = GPCOLORPICKER_settings(prefs)  

        # Get active palette
        gpmp = context.scene.gpmatpalettes.active()
        if (not self.settings.mat_from_active) and (not gpmp):
            self.report({'WARNING'}, "No active palette")
            return {'CANCELLED'}

        # Get event related data
        self.invoke_key = event.type
        self.region_dim = np.asarray([context.region.width,context.region.height])
        self.origin = np.asarray([event.mouse_region_x,event.mouse_region_y]) - 0.5*self.region_dim  

        self.mat_selected = -1
        self.active_obj = context.active_object

        # Init Cache containing materials and palette related data
        self.cached_data = CachedData(context, not self.settings.mat_from_active)
        if self.cached_data.mat_nb == 0:
            self.report({'WARNING'}, "No material to pick")

        # Setting handlers
        mhandle = context.window_manager.modal_handler_add(self)
        if not mhandle:
            return {'CANCELLED'}  

        self._handle = context.space_data.draw_handler_add(draw_callback_px, (self,context,self.cached_data,self.settings), \
                                                        'WINDOW', 'POST_PIXEL')
        return {'RUNNING_MODAL'}    
