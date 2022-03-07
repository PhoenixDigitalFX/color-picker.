import bpy
from . picker_ops import GPCOLORPICKER_OT_wheel

classes = [GPCOLORPICKER_OT_wheel]
default_invoke_key = "A"

def register(addon_keymaps):
    for cls in classes:
        bpy.utils.register_class(cls)

    pname = (__package__).split('.')[0]
    prefs = bpy.context.preferences.addons[pname].preferences
    if prefs is None : 
        kmi_type = 'A'
        kmi_ctrl = False
        kmi_shift = False
        kmi_alt = False
    else:
        kmi_type = prefs.picker_keymap.key_type
        kmi_ctrl = prefs.picker_keymap.ctrl_mdf
        kmi_shift = prefs.picker_keymap.shift_mdf
        kmi_alt = prefs.picker_keymap.alt_mdf

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(GPCOLORPICKER_OT_wheel.bl_idname, value='PRESS', \
                                type=kmi_type, ctrl=kmi_ctrl, alt=kmi_alt, shift = kmi_shift)
        addon_keymaps.append((km, kmi, "Invoke Picker"))

def unregister():        
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)