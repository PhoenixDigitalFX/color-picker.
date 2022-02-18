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

addon_keymaps = [] 
### ----------------- User Preferences
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import *
class GPCOLORPICKER_theme(PropertyGroup):
    pie_color: FloatVectorProperty(
            subtype='COLOR', name="Pie Color", min=0, max=1, size=4, default=(0.1,0.1,0.1,1.))
    line_color: FloatVectorProperty(
        subtype='COLOR', name="Line Color", min=0, max=1, size=4, default=(0.96,0.96,0.96,1.))
    text_color: FloatVectorProperty(
        subtype='COLOR', name="Text Color", min=0, max=1, size=4, default=(0.,0.,0.,1.))

class GPCOLORPICKER_preferences(AddonPreferences):
    bl_idname = __name__

    icon_scale: IntProperty(
        name="Icon scale",
        min=100, default=460, max=800
    )    
    theme: PointerProperty(type=GPCOLORPICKER_theme)
    mat_mode: EnumProperty(name="Material Mode", items=[("from_active", "From Active", 'Set Materials from active object'), ("from_file", "From File", 'Set Materials from JSON file')], \
                            default="from_file")
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

        prv = scol.box()
        prv.label(text="Keymap", icon='NONE')
        if len(addon_keymaps) > 0:
            kmi = addon_keymaps[0][1]
            row = prv.row()
            row.label(text="Press Key")
            row.template_event_from_keymap_item(kmi)
            row = prv.row(align=True)
            row.prop(kmi, 'map_type', text="")
            row.prop(kmi, 'type', text="")
    
classes = [ GPCOLORPICKER_theme, \
            GPCOLORPICKER_preferences
          ]

def register():
    from . gpmatpalette import register as register_palette
    register_palette()

    from . gpcolorpicker import register as register_picker
    register_picker(addon_keymaps)

    for cls in classes:
        bpy.utils.register_class(cls)    
    

def unregister():        
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    from . gpcolorpicker import unregister as unregister_picker
    unregister_picker(addon_keymaps)

    from .gpmatpalette import unregister as unregister_palette
    unregister_palette()

if __name__ == "__main__":
    register() 
