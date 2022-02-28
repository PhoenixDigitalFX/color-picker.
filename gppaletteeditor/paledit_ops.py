from email.policy import default
import bpy
import numpy as np
from .. gpcolorpicker.picker_settings import GPCOLORPICKER_settings
from . paledit_draw import draw_callback_px
from . paledit_interactions import *

class GPCOLORPICKER_OT_newPalette(bpy.types.Operator):
    bl_idname = "gpencil.new_palette"
    bl_label = "GP New Palette"

    pal_name: bpy.props.StringProperty(name="New Palette Name")
    is_pal_name_valid: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        if not self.is_pal_name_valid :
            return {'CANCELLED'}       

        palettes = context.scene.gpmatpalettes
        npal = palettes.add()
        npal.name = self.pal_name

        bpy.ops.ed.undo_push()
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop(self, "pal_name")
        
        row = layout.row()
        gpmp = context.scene.gpmatpalettes
        self.is_pal_name_valid = False 
        if not self.pal_name:
            row.label(text="Palette name is empty")
        elif (self.pal_name in gpmp.palettes):
            row.label(text="Already exists")
        else:
            self.is_pal_name_valid = True           

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
class GPCOLORPICKER_OT_addMaterialInPalette(bpy.types.Operator):
    bl_idname = "gpencil.add_mat_palette"
    bl_label = "GP Add Material to Palette"

    @classmethod
    def poll(cls, context):
        return context.scene.gpmatpalettes.active()
    
    angle: bpy.props.FloatProperty(subtype='ANGLE', default=0)
    mat_name: bpy.props.StringProperty(name="New Material Name")
    is_mat_name_valid: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        if not self.is_mat_name_valid :
            return {'CANCELLED'}       

        gpmp = context.scene.gpmatpalettes.active()      
        gpmp.set_material_by_angle(self.mat_name, self.angle)  

        bpy.ops.ed.undo_push()
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop_search(self, "mat_name", bpy.data, "materials")
        
        row = layout.row()
        gpmp = context.scene.gpmatpalettes.active()
        self.is_mat_name_valid = False       
        if not self.mat_name:
            row.label(text="No material selected")
        elif not (self.mat_name in bpy.data.materials):
            row.label(text="Material not found") 
        elif not (bpy.data.materials[self.mat_name].is_grease_pencil):
            row.label(text="Material is not Grease Pencil")
        elif self.mat_name in gpmp.materials:
            row.label(text="Already in current palette")
        else:
            self.is_mat_name_valid = True           

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


### ----------------- Operator definition
class GPCOLORPICKER_OT_paletteEditor(bpy.types.Operator):
    bl_idname = "gpencil.palette_edit"
    bl_label = "GP Palette Editor"  

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

        if not self.running_interaction:
            gpmp = context.scene.gpmatpalettes.active()
            if len(gpmp.materials) != len(cache.materials):
                cache.refresh()
                self.init_interaction_areas(context, mouse_local)

        if event.type == 'MOUSEMOVE':
            if self.running_interaction:
                self.running_interaction.run(self, cache, stgs, mouse_local)
            elif itsel and itsel.is_in_selection(self, cache, stgs, mouse_local):
                itsel.display_in_selection(self, cache, stgs, mouse_local)
            else:
                self.interaction_in_selection = None                        
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

            palettes = context.scene.gpmatpalettes
            if palettes.is_empty():
                return {'RUNNING_MODAL'}            
            if not self.empty_palette and (palettes.active_index == palettes.count()-1):
                self.empty_palette = True
            else:
                self.empty_palette = False
                palettes.next()
                cache.refresh()
            self.init_interaction_areas(context, mouse_local)

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            if self.running_interaction:
                self.running_interaction.cancel_run(self, cache, stgs, context)
                self.running_interaction = None
            itsel = None
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'}
        
        return {'RUNNING_MODAL'}

    def init_interaction_areas(self, context, mouse_local=None):
        self.mat_selected = -1
        stgs = self.settings
        self.interaction_areas = []
        cache = self.cached_data

        if self.empty_palette:
            self.interaction_areas.append(NewPaletteInteraction(self, stgs))
        else:
            for i in range(self.cached_data.mat_nb):         
                self.interaction_areas.append(MoveMaterialPickerInteraction(self, cache, stgs, i))
                self.interaction_areas.append(MoveMaterialAngleInteraction(self, cache, stgs, i))
            self.interaction_areas.append(AddMaterialPickerInteraction(self, cache, stgs))
        
        if mouse_local is None:
            return 

        self.interaction_in_selection = None  
        itsel = self.interaction_in_selection 
        for itar in self.interaction_areas:
            if (not itsel) and (itar.is_in_selection(self, cache, stgs, mouse_local)):
                itar.display_in_selection(self, cache, stgs, mouse_local)
                self.interaction_in_selection = itar
            else:
                itar.display_not_in_selection(self, cache, stgs, mouse_local)

    def invoke(self, context, event):  
        self.report({'INFO'}, "Entering palette edit mode")

        pname = (__package__).split('.')[0]
        prefs = context.preferences.addons[pname].preferences
        if prefs is None : 
            self.report({'WARNING'}, "Could not load user preferences, running with default values")
        self.settings = GPCOLORPICKER_settings(prefs)  

        # Get event related data
        self.invoke_key = event.type
        self.region_dim = np.asarray([context.region.width,context.region.height])
        self.origin = np.asarray([event.mouse_region_x,event.mouse_region_y]) - 0.5*self.region_dim  

        # Init Cached Data
        gpmp = context.scene.gpmatpalettes.active()
        self.empty_palette = (gpmp is None)
        if gpmp:
            self.cached_data = CachedData(not self.settings.mat_from_active)
        else:
            self.cached_data = None

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


classes = [GPCOLORPICKER_OT_paletteEditor, GPCOLORPICKER_OT_addMaterialInPalette, GPCOLORPICKER_OT_newPalette]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)