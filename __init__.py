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

def set_default_palette_path():
    pname = (__package__).split('.')[0]
    prefs = bpy.context.preferences.addons[pname].preferences  
    if prefs.autoload_mode.path:
        return 
        
    import os 
    user_path = bpy.utils.resource_path('USER')
    palette_path = os.path.join(user_path, "scripts", "GPpalettes")
    if os.path.isdir(palette_path):
        prefs.autoload_mode.path = palette_path

class GPCOLORPICKER_autoloadPalette(PropertyGroup):
    active: BoolProperty(default=True, name="Autoload mode on")
    path: StringProperty(default="", name="Palettes path", subtype="DIR_PATH")
    autocheck : BoolProperty(default=False, name="Set automatic updates", update=update_autocheck_mode)
    timerval: IntProperty(default=120, name="Timer", subtype='TIME', min=30)

def update_keymap(self, context):
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps['3D View']
    kmi = km.keymap_items[self.kmi]
    kmi.ctrl = self.ctrl_mdf
    kmi.alt = self.alt_mdf
    kmi.shift = self.shift_mdf
    kmi.type = self.key_type
class GPCOLORPICKER_PickerKM(PropertyGroup):
    kmi: StringProperty(name="Keymap item name", default="gpencil.color_pick")
    key_type: StringProperty(name="Keymap type", default='A', update=update_keymap)
    ctrl_mdf: BoolProperty(name="Keymap Ctrl modifier", default=False, update=update_keymap)
    shift_mdf: BoolProperty(name="Keymap Shift modifier", default=False, update=update_keymap)
    alt_mdf: BoolProperty(name="Keymap Alt modifier", default=False, update=update_keymap)
class GPCOLORPICKER_EditPaletteKM(PropertyGroup):
    kmi: StringProperty(name="Keymap item name", default="gpencil.palette_edit")
    key_type: StringProperty(name="Keymap type", default='A', update=update_keymap)
    ctrl_mdf: BoolProperty(name="Keymap Ctrl modifier", default=False, update=update_keymap)
    shift_mdf: BoolProperty(name="Keymap Shift modifier", default=True, update=update_keymap)
    alt_mdf: BoolProperty(name="Keymap Alt modifier", default=True, update=update_keymap)
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

    picker_keymap: PointerProperty(type=GPCOLORPICKER_PickerKM, name="Picker keymap")
    palette_edit_keymap: PointerProperty(type=GPCOLORPICKER_EditPaletteKM, name="Palette Edit keymap")

    def draw(self, context):
        layout = self.layout
        frow = layout.row()
        fcol = frow.column()
        stgs = fcol.box()
        stgs.label(text="Settings", icon='MODIFIER')
        stgs.prop(self, "icon_scale", slider=True)

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
            row.prop(self.autoload_mode, "active", text="Autoload palettes")

            if self.autoload_mode.active:
                row.prop(self.autoload_mode, "path", text="")
                row = mats.row()

                txt_updates = "Update"
                if self.autoload_mode.autocheck:
                    txt_updates = ""
                row.operator("gpencil.autoload_palette", text=txt_updates, icon= "FILE_REFRESH")
                row.prop(self.autoload_mode, "autocheck")
                if self.autoload_mode.autocheck:
                    row.prop(self.autoload_mode, "timerval")

        prv = scol.box()
        prv.label(text="Keymap", icon='BLENDER')

        row = prv.row()
        row.label(text=self.picker_keymap.kmi)
        row.prop(self.picker_keymap, "ctrl_mdf", icon="EVENT_CTRL", text="")
        row.prop(self.picker_keymap, "alt_mdf", icon="EVENT_ALT", text="")
        row.prop(self.picker_keymap, "shift_mdf", icon="EVENT_SHIFT", text="")
        row.prop(self.picker_keymap, "key_type")

        row = prv.row()
        row.label(text=self.palette_edit_keymap.kmi)
        row.prop(self.palette_edit_keymap, "ctrl_mdf", icon="EVENT_CTRL", text="")
        row.prop(self.palette_edit_keymap, "alt_mdf", icon="EVENT_ALT", text="")
        row.prop(self.palette_edit_keymap, "shift_mdf", icon="EVENT_SHIFT", text="")
        row.prop(self.palette_edit_keymap, "key_type")
    
classes = [ GPCOLORPICKER_theme, \
            GPCOLORPICKER_autoloadPalette, \
            GPCOLORPICKER_PickerKM, \
            GPCOLORPICKER_EditPaletteKM, \
            GPCOLORPICKER_preferences
          ]


def register():
    for cls in classes:
        bpy.utils.register_class(cls) 

    from . gpmatpalette import register as register_palette
    register_palette()

    from . gpcolorpicker import register as register_picker
    register_picker(addon_keymaps)

    from . gppaletteeditor import register as register_editor
    register_editor(addon_keymaps)
        
    if not bpy.app.timers.is_registered(reload_autopalette):
        bpy.app.timers.register(reload_autopalette)
    
    set_default_palette_path()

def unregister():        
    if bpy.app.timers.is_registered(reload_autopalette):
        bpy.app.timers.unregister(reload_autopalette)

    # Remove the hotkey
    for km, kmi, dsc in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    from . gppaletteeditor import unregister as unregister_editor
    unregister_editor()
    
    from . gpcolorpicker import unregister as unregister_picker
    unregister_picker()

    from .gpmatpalette import unregister as unregister_palette
    unregister_palette()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register() 
