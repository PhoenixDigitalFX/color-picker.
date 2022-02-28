import bpy
import numpy as np
from .. gpcolorpicker.picker_settings import GPCOLORPICKER_settings
from . paledit_draw import draw_callback_px
from . paledit_interactions import *

class GPCOLORPICKER_OT_addMaterialInPalette(bpy.types.Operator):
    bl_idname = "gpencil.add_mat_palette"
    bl_label = "GP Add Material to Palette"
    bl_property = "mat_name"

    @classmethod
    def poll(cls, context):
        return context.scene.gpmatpalettes.active()
    
    mat_name: bpy.props.StringProperty(name="New Material Name")

    def execute(self, context):
        if (not (self.mat_name in bpy.data.materials)) \
            or (not (bpy.data.materials[self.mat_name].is_grease_pencil)) :
            print("Invalid value")
            return {'CANCELLED'}

        print("Got Material ", self.mat_name)
        
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop_search(self, "mat_name", bpy.data, "materials")
        
        row = layout.row()
        gpmp = context.scene.gpmatpalettes.active()
        if not self.mat_name:
            row.label(text="No material selected")
        elif not (self.mat_name in bpy.data.materials):
            row.label(text="Material not found") 
        elif not (bpy.data.materials[self.mat_name].is_grease_pencil):
            row.label(text="Material is not Grease Pencil")
        elif self.mat_name in gpmp.materials:
            row.label(text="Already in current palette")           

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
        cache = self.cached_data
        if not cache.from_palette:
            return

        pal = context.scene.gpmatpalettes.active()
        nmt = cache.mat_nb
        for i in range(nmt):
            mname = cache.materials[i].name

            a = cache.angles[i]
            if cache.is_custom_angle[i] and (a != pal.materials[mname].get_angle()):
                pal.set_material_by_angle(mname, a)
            
            if (cache.pick_origins[i][2] > 0):
                matit = pal.materials[mname]
                matit.set_origin(cache.pick_origins[i][0:2])

    def modal(self, context, event):
        context.area.tag_redraw()  
        # Find mouse position
        mouse_pos = np.asarray([event.mouse_region_x,event.mouse_region_y])
        mouse_local = mouse_pos - 0.5*self.region_dim - self.origin

        cache = self.cached_data
        stgs = self.settings

        itsel = self.interaction_in_selection

        if event.type == 'MOUSEMOVE':
            if self.running_interaction:
                self.running_interaction.run(self, cache, stgs, mouse_local)
            elif itsel and itsel.is_in_selection(self, cache, stgs, mouse_local):
                itsel.display_in_selection(self, cache, stgs, mouse_local)
            else:
                itsel = None                        
                for itar in self.interaction_areas:
                    if (not itsel) and (itar.is_in_selection(self, cache, stgs, mouse_local)):
                        itar.display_in_selection(self, cache, stgs, mouse_local)
                        self.interaction_in_selection = itar
                    else:
                        itar.display_not_in_selection(self, cache, stgs, mouse_local)

        elif (event.type == 'LEFTMOUSE') and (event.value == 'PRESS'):
            if itsel:
                itsel.start_running(self, cache, stgs, context)
                self.running_interaction = itsel

        elif (event.type == 'LEFTMOUSE') and (event.value == 'RELEASE'):
            if self.running_interaction:
                self.running_interaction.stop_running(self, cache, stgs, context)
                self.running_interaction = None
            
        elif (event.type == self.settings.switch_key) and (event.value == 'PRESS'):
            if self.running_interaction:
                self.running_interaction.cancel_run(self, cache, stgs, context)
                self.running_interaction = None
            self.interaction_in_selection = None
            bpy.context.scene.gpmatpalettes.next()
            self.cached_data.refresh()
            self.init_interaction_areas(context)

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            if self.running_interaction:
                self.running_interaction.cancel_run(self, cache, stgs, context)
                self.running_interaction = None
            itsel = None
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'}
        
        return {'RUNNING_MODAL'}

    def init_interaction_areas(self, context):
        self.mat_selected = -1
        self.origin_selected = -1
        self.add_mat_cursor = -1

        cache = self.cached_data
        stgs = self.settings

        self.interaction_areas = []
        for i in range(self.cached_data.mat_nb):         
            self.interaction_areas.append(MoveMaterialPickerInteraction(self, cache, stgs, i))
            self.interaction_areas.append(MoveMaterialAngleInteraction(self, cache, stgs, i))
        self.interaction_areas.append(AddMaterialPickerInteraction(self, cache, stgs))

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

        # Init Cached Data
        self.cached_data = CachedData(not self.settings.mat_from_active)
        if self.cached_data.mat_nb == 0:
            self.report({'WARNING'}, "No material to pick")

        # Init interactions areas
        self.init_interaction_areas(context)
        self.interaction_in_selection = None
        self.running_interaction = None

        # Setting handlers
        mhandle = context.window_manager.modal_handler_add(self)
        if not mhandle:
            return {'CANCELLED'}  

        self._handle = context.space_data.draw_handler_add(draw_callback_px, \
                                (self,context,self.cached_data,self.settings), \
                                                        'WINDOW', 'POST_PIXEL')
        return {'RUNNING_MODAL'}    


classes = [GPCOLORPICKER_OT_paletteEditor, GPCOLORPICKER_OT_addMaterialInPalette]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)