import bpy

bl_info = {
    "name": "GP Color Picker",
    "author": "Les Fées Spéciales (LFS)",
    "description": "Quickly switch between materials of the active Grease pencil object",
    "blender": (3, 0, 0),
    "version": (1, 1, 0),
    "location": "Press S in Draw mode with a GP object activated",
    "category": "Materials"
}

from . op import GPCOLORPICKER_OT_wheel,settings

addon_keymaps = [] 

### ----------------- User Preferences
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import *
from . io import GPCOLORPICKER_OT_getJSONFile
class GPCOLORPICKER_theme(PropertyGroup):
    pie_color: FloatVectorProperty(
            subtype='COLOR', name="Pie Color", min=0, max=1, size=4, default=(0.1,0.1,0.1,1.))
    line_color: FloatVectorProperty(
        subtype='COLOR', name="Line Color", min=0, max=1, size=4, default=(0.96,0.96,0.96,1.))
    text_color: FloatVectorProperty(
        subtype='COLOR', name="Text Color", min=0, max=1, size=4, default=(0.,0.,0.,1.))

class GPCOLORPICKER_preferences(AddonPreferences):
    bl_idname = __name__

    # TODO: add keymap in prefs    
    icon_scale: IntProperty(
        name="Icon scale",
        min=100, default=250, max=500
    )    

    json_fpath: StringProperty(subtype="FILE_PATH")
    theme: PointerProperty(type=GPCOLORPICKER_theme)
    mat_mode: EnumProperty(name="Material Mode", items=[("from_active", "From Active", 'Set Materials from active object'), ("from_file", "From File", 'Set Materials from JSON file')], \
                            default="from_active")
    assign_mat: BoolProperty(name="Assign material on selection", default= True,  \
        description="Check this option if you want the materials you selected to be assigned automatically to the current object. Otherwise, selecting a material will only work if the object already has it.")

    def draw(self, context):
        layout = self.layout
        frow = layout.row()
        fcol = frow.column()
        stgs = fcol.box()
        stgs.label(text="Settings", icon='MODIFIER')
        stgs.prop(self, "icon_scale")

        props = fcol.box()
        props.label(text="Theme", icon='RESTRICT_COLOR_ON')
        props.prop(self.theme, 'pie_color', text="Pie Color")
        props.prop(self.theme, 'line_color', text="Line Color")
        props.prop(self.theme, 'text_color', text="Text Color")

        scol = frow.column()
        mats = scol.box()
        mats.label(text="Materials", icon='MATERIAL')
        mats.row().prop_tabs_enum(self, "mat_mode")

        if self.mat_mode == "from_file":
            row = mats.row()
            row.operator("gpencil.file_load", icon="FILEBROWSER", text="Load")
            row.label(text=self.json_fpath)
            row = mats.row()
            row.prop(self, "assign_mat")

        prv = scol.box()
        prv.label(text="Keymap", icon='NONE')
        if len(addon_keymaps) > 0:
            prv.template_keymap_item_properties(addon_keymaps[0][1])
    
classes = [ GPCOLORPICKER_OT_wheel, \
            GPCOLORPICKER_OT_getJSONFile, \
            GPCOLORPICKER_theme, \
            GPCOLORPICKER_preferences
          ]

def register():
    from . gpmatpalette import register_data
    register_data()

    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add the hotkey
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(GPCOLORPICKER_OT_wheel.bl_idname, \
                                    type=settings.key_shortcut, value='PRESS')
        addon_keymaps.append((km, kmi))
    

def unregister():        
    # Remove the hotkey
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    from . gpmatpalette import unregister_data
    unregister_data()

if __name__ == "__main__":
    register() 
