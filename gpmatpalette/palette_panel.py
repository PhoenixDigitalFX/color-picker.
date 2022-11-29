# Panel displaying the list of active palettes and a set of useful tools
import bpy

''' Palette UI List item '''
class GPCOLORPICKER_UL_PaletteList(bpy.types.UIList):
    bl_idname="GPCOLORPICKER_UL_PaletteList"
    
    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):

        if self.layout_type in {'DEFAULT', 'COMPACT', 'GRID'}:
            # Palette name
            col = layout.column()          
            if item.autoloaded:
                decorated_name = '[' + item.name + ']'
                col.label(text=decorated_name)
            else:
                col.prop(item, 'name', text='', emboss=False)
            col.enabled = item.visible

            # Warning if palette is obsolete
            col = layout.column()
            if item.is_obsolete:
                col.prop(item, "is_obsolete", text="", icon="ERROR", emboss=False)

            # Reload palette
            col = layout.column()
            if item.source_path:
                rlp = col.operator("scene.reload_palette", icon="FILE_REFRESH", text="", emboss=False)
                rlp.palette_index = index

            # Remove palette
            col = layout.column()
            if not item.autoloaded:
                rmp = col.operator("scene.remove_palette", icon="X", text="", emboss=False)
                rmp.palette_index = index

            # Toggle palette visibility
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
        
        # Palettes Header
        row = layout.row()
        row.label(text="Active palettes")
        row.operator("scene.reload_all_palettes", icon="FILE_REFRESH", text="")
        row.operator("scene.export_palette", icon="EXPORT", text="")
        row.operator("scene.import_palette", icon="FILE_NEW", text="")

        # Palettes List
        row = layout.row()
        
        col = row.column()
        gpmp = context.scene.gpmatpalettes
        col.template_list("GPCOLORPICKER_UL_PaletteList",'GP_Palettes', \
                        dataptr=gpmp, propname="palettes", \
                        active_dataptr=gpmp, active_propname="active_index", \
                        )

        col = row.column(align=True)
        col.separator()
        col.operator('scene.move_palette', icon='TRIA_UP', text='').move_up = True
        col.operator('scene.move_palette', icon='TRIA_DOWN', text='').move_up = False

classes = [GPCOLORPICKER_UL_PaletteList, GPCOLORPICKER_PT_Palette]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)