from calendar import c
import bpy
import numpy as np
from .. gpcolorpicker.picker_settings import GPCOLORPICKER_settings
from .. gpcolorpicker.picker_interactions import *
from .. gpcolorpicker.picker_draw import draw_callback_px
from . paledit_maths import angle_boundaries, is_in_boundaries
from . paledit_interactions import *

class GPCOLORPICKER_OT_moveMaterialOrigin(bpy.types.Operator):
    bl_idname = "gpencil.move_mat_origin"
    bl_label = "GP Palette Editor : move material origin"  

    my_float: bpy.props.FloatProperty(name="Some Floating Point")
    my_bool: bpy.props.BoolProperty(name="Toggle Option")
    my_string: bpy.props.StringProperty(name="String Value")

    def execute(self, context):
        message = (
            "Popup Values: %f, %d, '%s'" %
            (self.my_float, self.my_bool, self.my_string)
        )
        self.report({'INFO'}, message)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

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

        pal.materials.foreach_set("custom_angle", cache.custom_angles)

    def move_custom_angle(self, mti, nth):
        cache = self.cached_data
        nmt = cache.mat_nb
        if (nmt == 0) or (mti < 0) or (mti >= nmt):
            return
        
        if not cache.use_custom_angles():
            cache.custom_angles = [ i*2*pi/nmt for i in range(nmt) ]

        R = self.settings.mat_centers_radius
        r = self.settings.mat_radius + self.settings.mat_line_width

        if is_in_boundaries(R, r, cache.custom_angles, mti, nth):
            cache.custom_angles[mti] = nth

    def modal(self, context, event):
        context.area.tag_redraw()  
        # Find mouse position
        mouse_pos = np.asarray([event.mouse_region_x,event.mouse_region_y])
        mouse_local = mouse_pos - 0.5*self.region_dim - self.origin

        # def mat_selected_in_range():
        #     i = self.mat_selected
        #     return (i >= 0) and (i < self.cached_data.mat_nb)

        if event.type == 'MOUSEMOVE':
            if self.running_interaction:
                self.running_interaction.run(mouse_local)
            else:
                for itar in self.interaction_areas:
                    if itar.is_in_selection():
                        itar.display_selection(mouse_local)

            # if self.is_mat_dragged:
            #     dt = get_mouse_arg(event, self.region_dim, self.origin)
            #     self.move_custom_angle(self.mat_selected, dt)
            # else:
            #     self.mat_selected = get_selected_mat_id(event,self.region_dim, self.origin, self.cached_data.mat_nb, \
            #                      self.settings.interaction_radius, self.cached_data.custom_angles)

        elif (event.type == 'LEFTMOUSE') and (event.value == 'PRESS'):
            for itar in self.interaction_areas:
                if itar.is_in_selection():
                    itar.start_running()
                    self.running_interaction = itar
                    break

            # if mat_selected_in_range():
            #     self.is_mat_dragged = True

        elif (event.type == 'LEFTMOUSE') and (event.value == 'RELEASE'):
            if self.running_interaction:
                self.running_interaction.stop_running()
                self.running_interaction = None
            # self.is_mat_dragged = False
            # self.write_cache_in_palette(context)
            
        elif (event.type == self.settings.switch_key) and (event.value == 'PRESS'):
            if self.running_interaction:
                self.running_interaction.cancel_run()
                self.running_interaction = None

            bpy.context.scene.gpmatpalettes.next()
            self.cached_data.refresh()
            self.mat_selected = get_selected_mat_id(event,self.region_dim, self.origin, self.cached_data.mat_nb, \
                              self.settings.interaction_radius, self.cached_data.custom_angles)

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            if self.running_interaction:
                self.running_interaction.cancel_run()
                self.running_interaction = None

            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}

    def init_interaction_areas(self, context):
        self.interaction_areas = []
        gpmp = context.scene.gpmatpalettes.active()
        
        for i in range(cache.mat_nb):
            self.interaction_areas.append(MoveMaterialAngleInteraction(m))

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
        self.cur_arg = 0
        self.is_mat_dragged = False

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


classes = [GPCOLORPICKER_OT_paletteEditor, GPCOLORPICKER_OT_moveMaterialOrigin]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)