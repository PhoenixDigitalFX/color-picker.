import bpy
from . palette_props import GPMatPalettes
from bpy.props import *

class GPCOLORPICKER_UL_PaletteList(bpy.types.UIList):
    bl_idname="GPCOLORPICKER_UL_PaletteList"
    
    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):

        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            col = layout.column()
            decorated_name = item.name
            
            if item.autoloaded:
                decorated_name = '[' + decorated_name + ']'

            if not item.visible:
                decorated_name = '~' + decorated_name
            
            col.label(text=decorated_name)

            col = layout.column()
            col.label(text=item.source_path)

            pname = (__package__).split('.')[0]
            prefs = context.preferences.addons[pname].preferences
            autoload_mode = False
            if prefs: 
                autoload_mode = prefs.autoload_mode.active

            col = layout.column()
            if item.source_path and item.is_obsolete:
                rlp = col.operator("scene.reload_palette", icon="FILE_REFRESH", text="", emboss=False)
                rlp.palette_index = index

            col = layout.column()
            if not (autoload_mode and item.autoloaded):
                rmp = col.operator("scene.remove_palette", icon="X", text="", emboss=False)
                rmp.palette_index = index

            col = layout.column()
            if item.visible:
                tpv_icon = 'HIDE_OFF'
            else:
                tpv_icon = 'HIDE_ON'
            tpv = col.operator("scene.toggle_pal_visibility", icon=tpv_icon, text="", emboss=False)
            tpv.palette_index = index


class GPCOLORPICKER_PT_Palette(bpy.types.Panel):
    bl_label="Grease Pencil palettes"
    bl_idname="SCENE_PT_gppalette"
    bl_space_type="PROPERTIES"
    bl_region_type="WINDOW"
    bl_context="scene"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Active palettes")
        gpmp = bpy.context.scene.gpmatpalettes        
        row.operator("scene.reload_all_palettes", icon="FILE_REFRESH", text="")
        if gpmp.is_obsolete:
            row.operator("scene.export_palette", icon="EXPORT", text="")
        row.operator("gpencil.palette_load", icon="FILE_NEW", text="")

        row = layout.row()
        row.template_list("GPCOLORPICKER_UL_PaletteList",'GP_Palettes', \
                        dataptr=gpmp, propname="palettes", \
                        active_dataptr=gpmp, active_propname="active_index", \
                        )

classes = [GPCOLORPICKER_UL_PaletteList, GPCOLORPICKER_PT_Palette]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)