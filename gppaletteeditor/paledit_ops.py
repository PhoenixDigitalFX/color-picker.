# Palette Editor related operators
import bpy, time
import numpy as np
from .. gpcolorpicker.picker_settings import GPCOLORPICKER_settings
from .. gpcolorpicker.picker_interactions import get_selected_brush_id, get_selected_mat_id
from . paledit_draw import draw_callback_px
from . paledit_interactions import *

''' Main Operator : Invokes the palette editor mode '''
class GPCOLORPICKER_OT_paletteEditor(bpy.types.Operator):
    bl_idname = "scene.palette_edit"
    bl_label = "GP Palette Editor"  

    ''' Accepts cached data and writes it into Blender file palette data '''
    def write_cache_in_palette(self, context):
        cache = self.cached_data
        if not cache.from_palette:
            return

        pal = context.scene.gpmatpalettes.active()
        nmt = cache.mat_nb
        for i in range(nmt):
            mname = cache.materials[i].name

            a = cache.angles[i]
            matit = pal.materials[i]
            if cache.is_custom_angle[i] and (a != matit.get_angle()):
                pal.set_material_by_angle(mname, a)

            if len(matit.picklines) != len(cache.pick_origins[i]):
                pal.is_dirty = True
            matit.picklines.clear()
            matit.set_origins(cache.pick_origins[i])
    
    # Change the selected material & brush
    def refresh_selections(self, event):
        cache = self.cached_data
        stg = self.settings

        # print(f"Mat locked {self.mat_locked}, mat selected {self.mat_selected}")

        msel = get_selected_mat_id(event, self.region_dim, self.origin, cache.mat_nb, \
                                            stg.interaction_radius, cache.angles)

        if not self.mat_locked:    
            self.mat_selected = msel

        if (msel == self.mat_selected) and (self.mat_selected >= 0):
            nb_brush = len(cache.brushes[self.mat_selected])
            int_area = stg.mat_centers_radius + stg.mat_radius*stg.selection_ratio
            self.brush_selected = get_selected_brush_id(event, self.region_dim, self.origin, nb_brush, \
                                int_area, stg.brush_radius)
        else:
            self.brush_selected = -1

    def modal(self, context, event):       
        # Getting mouse location
        mouse_pos = np.asarray([event.mouse_region_x,event.mouse_region_y])
        mouse_local = mouse_pos - 0.5*self.region_dim - self.origin

        cache = self.cached_data
        stgs = self.settings
        itsel = self.interaction_in_selection
        gpmp = context.scene.gpmatpalettes

        self.refresh_selections(event)

        # Refreshing cache and interaction areas if necessary
        if gpmp.needs_refresh():
            if gpmp.is_dirty and self.empty_palette:
                self.empty_palette = False
            cache.refresh(context)
            self.init_interaction_areas(context, mouse_local)
            gpmp.all_refreshed()
        elif not self.running_interaction:
            for itar in self.interaction_areas:
                itar.refresh(cache, stgs)

        context.area.tag_redraw()  
        if event.type == 'MOUSEMOVE':      
            if not self.running_interaction is None:
                self.running_interaction.on_mouse_move(self, cache, stgs, mouse_local)
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
                itsel.on_click_press(self, cache, stgs, context)
                self.running_interaction = itsel

        elif (event.type == 'LEFTMOUSE') and (event.value == 'RELEASE'):
            if self.running_interaction:
                self.running_interaction.on_click_release(self, cache, stgs, context)
                self.running_interaction = None
            
        elif (event.type == self.settings.switch_key) and (event.value == 'PRESS'):
            if self.running_interaction:
                self.running_interaction.cancel_run(self, cache, stgs, context)
                self.running_interaction = None
            self.interaction_in_selection = None
            dir = 1
            if event.shift:
                dir = -1

            if gpmp.is_empty():
                return {'RUNNING_MODAL'}            
            if not self.empty_palette and \
                ( (dir and (gpmp.active_index == gpmp.count()-1)) or \
                   (not dir and gpmp.active_index == 0) ):
                self.empty_palette = True
            else:
                self.empty_palette = False
                bpy.context.scene.gpmatpalettes.next(dir)
                cache.refresh(context)
            self.init_interaction_areas(context, mouse_local)

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            if self.running_interaction:
                self.running_interaction.cancel_run(self, cache, stgs, context)
                self.running_interaction = None
                return {'RUNNING_MODAL'}
            else:
                itsel = None
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'FINISHED'}
        
        return {'RUNNING_MODAL'}

    ''' Sets up all interaction areas given the current palette content in the cache '''
    def init_interaction_areas(self, context, mouse_local=np.zeros(2)):
        self.mat_selected = -1
        self.mat_locked = False
        self.brush_selected = -1
        stgs = self.settings
        self.interaction_areas = []
        cache = self.cached_data

        if self.empty_palette:
            self.interaction_areas.append(NewPaletteInteraction(self, stgs))
        else:
            for i in range(cache.mat_nb):         
                self.interaction_areas.append(AddMaterialPickerInteraction(self, cache, stgs, i))
                for j in range(len(cache.pick_origins[i])):
                    self.interaction_areas.append(MoveMaterialPickerInteraction(self, cache, stgs, i, j))
                self.interaction_areas.append(MoveMaterialAngleInteraction(self, cache, stgs, i))
                self.interaction_areas.append(RemoveMaterialInteraction(self, cache, stgs, i))
                self.interaction_areas.append(AddBrushInteraction(self, cache, stgs, i))
            self.interaction_areas.append(AddMaterialInteraction(self, cache, stgs))
            self.interaction_areas.append(EditImageInteraction(self, cache, stgs))

        self.interaction_in_selection = None  
        for itar in self.interaction_areas:
            if (not self.interaction_in_selection) and (itar.is_in_selection(self, cache, stgs, mouse_local)):
                itar.display_in_selection(self, cache, stgs, mouse_local)
                self.interaction_in_selection = itar
            else:
                itar.display_not_in_selection(self, cache, stgs, mouse_local)

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
        self.report({'INFO'}, "Entering palette edit mode")
        # Timer initialization
        self.tsart = time.time()
        self.timeout = False

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
        self.npalettes = context.scene.gpmatpalettes.count()
        self.empty_palette = (self.npalettes == 0)
        self.cached_data = CachedData(context)

        # Init interactions areas
        self.interaction_in_selection = None
        self.running_interaction = None
        self.init_interaction_areas(context)

        # Setting handlers
        mhandle = context.window_manager.modal_handler_add(self)
        if not mhandle:
            return {'CANCELLED'}  

        self._handle = context.space_data.draw_handler_add(draw_callback_px, \
                                (self,context,self.cached_data,self.settings), \
                                                        'WINDOW', 'POST_PIXEL')
        return {'RUNNING_MODAL'}    

''' ----- Sides Operators : Palette editions needing additional UILayout -----'''

''' Edit Palette Image
    UI : select image template layout
'''
class GPCOLORPICKER_OT_editImage(bpy.types.Operator):
    bl_idname = "scene.edit_palette_image"
    bl_label = "GP Edit Palette Image"

    @classmethod
    def poll(cls, context):
        return context.scene.gpmatpalettes.active()

    def execute(self, context):
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        pal = context.scene.gpmatpalettes.active()
        row = layout.row()
        row.template_ID(pal, "image", new="image.new", open="image.open")

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

''' Adds a new Palette in Collection
    UI : user input name of the Palette
'''
class GPCOLORPICKER_OT_newPalette(bpy.types.Operator):
    bl_idname = "scene.new_palette"
    bl_label = "GP New Palette"

    pal_name: bpy.props.StringProperty(name="New Palette Name")
    is_pal_name_valid: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        if not self.is_pal_name_valid :
            return {'CANCELLED'}       

        gpmp = context.scene.gpmatpalettes
        gpmp.add_palette(self.pal_name)

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
        elif self.pal_name.startswith("__"):
            row.label(text="Palette name cannot start with __")
        else:
            self.is_pal_name_valid = True           

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
''' Adds an existing material in Palette 
    UI : select material template layout
'''
class GPCOLORPICKER_OT_addMaterialInPalette(bpy.types.Operator):
    bl_idname = "scene.add_mat_palette"
    bl_label = "GP Add Material to Palette"

    @classmethod
    def poll(cls, context):
        return context.scene.gpmatpalettes.active()
    
    angle: bpy.props.FloatProperty(name="Position angle", subtype='ANGLE', default=0)

    def execute(self, context):
        
        pal = context.scene.gpmatpalettes.active()      
        pal.accept_pending_material(self.angle)

        bpy.ops.ed.undo_push()
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout

        pal = context.scene.gpmatpalettes.active()
        row = layout.row()
        row.template_ID(pal, "pending_material")

        row = layout.row()
        if (pal.pending_material) and (not pal.is_material_available(pal.pending_material)):
            row.label(text="Material not available")      

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

''' Removes a material from the Palette
    UI: confirmation popup
'''
class GPCOLORPICKER_OT_removeMaterialFromPalette(bpy.types.Operator):
    bl_idname = "scene.remove_mat_palette"
    bl_label = "GP Remove Material from Palette"

    mat_index: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        return context.scene.gpmatpalettes.active()

    def execute(self, context):
        gpmp = context.scene.gpmatpalettes
        gpmp.active().remove_material(self.mat_index)
        
        return {'FINISHED'}   

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_confirm(self, event)


''' Adds an existing material in Palette 
    UI : select material template layout
'''
class GPCOLORPICKER_OT_addBrushInMaterial(bpy.types.Operator):
    bl_idname = "scene.add_brush_mat"
    bl_label = "GP Add Brush to Material"

    mat_index: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        return context.scene.gpmatpalettes.active()

    def execute(self, context):     
        pal = context.scene.gpmatpalettes.active()
        pal.materials[self.mat_index].accept_pending_brush()

        return {'FINISHED'}   

    def draw(self, context):
        layout = self.layout

        pal = context.scene.gpmatpalettes.active()
        mat = pal.materials[self.mat_index]
        row = layout.row()
        row.template_ID(mat, "pending_brush")  

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

classes = [GPCOLORPICKER_OT_paletteEditor, \
        GPCOLORPICKER_OT_addMaterialInPalette, \
        GPCOLORPICKER_OT_removeMaterialFromPalette, \
        GPCOLORPICKER_OT_newPalette, \
        GPCOLORPICKER_OT_addBrushInMaterial, \
        GPCOLORPICKER_OT_editImage]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)