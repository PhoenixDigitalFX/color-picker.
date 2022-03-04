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

def reload_autopalette():  
    bpy.ops.gpencil.autoload_palette()  

    pname = (__package__).split('.')[0]
    prefs = bpy.context.preferences.addons[pname].preferences  
    if not prefs.autoload_mode.autocheck:
        return None

    timer = prefs.autoload_mode.timerval
    print("Auto Update of the palette, next in ", timer, "seconds")
    return timer

def update_autocheck_mode(self, context):
    if self.autocheck and not bpy.app.timers.is_registered(reload_autopalette):
        bpy.app.timers.register(reload_autopalette)
    elif not self.autocheck and bpy.app.timers.is_registered(reload_autopalette):
        bpy.app.timers.unregister(reload_autopalette)
class GPCOLORPICKER_autoloadPalette(PropertyGroup):
    active: BoolProperty(default=True, name="Autoload mode on")
    path: StringProperty(default="/home/amelie.fondevilla/.config/blender/3.0/scripts/GPpalettes/", name="Palettes path", subtype="DIR_PATH")
    autocheck : BoolProperty(default=False, name="Set automatic updates", update=update_autocheck_mode)
    timerval: FloatProperty(default=3, name="Timer", subtype='TIME', unit='TIME')

class GPCOLORPICKER_preferences(AddonPreferences):
    bl_idname = __name__

    icon_scale: IntProperty(
        name="Icon scale",
        min=100, default=460, max=800
    )    
    theme: PointerProperty(type=GPCOLORPICKER_theme)
    mat_mode: EnumProperty(name="Material Mode", items=[("from_active", "From Active", 'Set Materials from active object'), ("from_palette", "From Palette", 'Set Materials GP Palettes')], \
                            default="from_palette")
    assign_mat: BoolProperty(name="Assign material on selection", default= True,  \
        description="Check this option if you want the materials you selected to be assigned automatically to the current object. Otherwise, selecting a material will only work if the object already has it.")
    autoload_mode: PointerProperty(type=GPCOLORPICKER_autoloadPalette, name="Autoload")

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
        if self.mat_mode == "from_palette":
            row = mats.row()
            row.prop(self.autoload_mode, "active", text="Autoload palettes", toggle=-1)
            if self.autoload_mode.active:
                row.prop(self.autoload_mode, "path", text="")
                row = mats.row()
                row.operator("gpencil.autoload_palette", text="Update", icon= "FILE_REFRESH")
                row.prop(self.autoload_mode, "autocheck")
                if self.autoload_mode.autocheck:
                    row.prop(self.autoload_mode, "timerval")

        prv = scol.box()
        prv.label(text="Keymap", icon='NONE')
        if len(addon_keymaps) > 0:
            kmi = addon_keymaps[0][1]
            row = prv.row()
            row.label(text="Press Key")
            row.prop(kmi, 'type', text="")
    
classes = [ GPCOLORPICKER_theme, \
            GPCOLORPICKER_autoloadPalette, \
            GPCOLORPICKER_preferences
          ]


def register():
    from . gpmatpalette import register as register_palette
    register_palette()

    from . gpcolorpicker import register as register_picker
    register_picker(addon_keymaps)

    from . gppaletteeditor import register as register_editor
    register_editor(addon_keymaps)

    for cls in classes:
        bpy.utils.register_class(cls) 
    
    if not bpy.app.timers.is_registered(reload_autopalette):
        bpy.app.timers.register(reload_autopalette)
    
def unregister():        
    if bpy.app.timers.is_registered(reload_autopalette):
        bpy.app.timers.unregister(reload_autopalette)

    # Remove the hotkey
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    from . gppaletteeditor import unregister as unregister_editor
    unregister_editor()
    
    from . gpcolorpicker import unregister as unregister_picker
    unregister_picker()

    from .gpmatpalette import unregister as unregister_palette
    unregister_palette()

if __name__ == "__main__":
    register() 
