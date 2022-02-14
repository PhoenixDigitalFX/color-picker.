import bpy
from . gpmatpalette import GPMatPalettes

class GPCOLORPICKER_UL_PaletteList(bpy.types.UIList):
    bl_idname="GPCOLORPICKER_UL_PaletteList"

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):

        # We could write some code to decide which icon to use here...
        refresh_icon = 'FILE_REFRESH'
        toggle_visibility = 'HIDE_ON'
        
        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            col = layout.column()
            col.label(text=item.name)

            col = layout.column()
            col.label(text=item.source_path)

            col = layout.column()
            col.label(text='', icon=refresh_icon)

            col = layout.column()
            props = col.operator("scene.remove_palette", icon="X", text="")
            props.palette_index = index

            # col = layout.column()
            # col.label(text='', icon=toggle_visibility)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="")



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
        row.operator("gpencil.file_load", icon="FILE_NEW", text="")

        row = layout.row()
        gpmp = bpy.context.scene.gpmatpalettes
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