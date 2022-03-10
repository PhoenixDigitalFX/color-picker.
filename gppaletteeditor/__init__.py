import bpy
from . paledit_ops import GPCOLORPICKER_OT_paletteEditor

def register(addon_keymaps):
    from . paledit_ops import register as register_ops
    register_ops()

    # Read keymap from preferences if exists. Default otherwise.
    pname = (__package__).split('.')[0]
    prefs = bpy.context.preferences.addons[pname].preferences
    if prefs is None : 
        kmi_type = 'A'
        kmi_ctrl = False
        kmi_shift = True
        kmi_alt = True
    else:
        kmi_type = prefs.palette_edit_keymap.key_type
        kmi_ctrl = prefs.palette_edit_keymap.ctrl_mdf
        kmi_shift = prefs.palette_edit_keymap.shift_mdf
        kmi_alt = prefs.palette_edit_keymap.alt_mdf

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(GPCOLORPICKER_OT_paletteEditor.bl_idname, value='PRESS',\
                    type=kmi_type, shift=kmi_shift, alt=kmi_alt, ctrl=kmi_ctrl)
        addon_keymaps.append((km, kmi, "Invoke Palette Editor"))

def unregister():        
    from . paledit_ops import unregister as unregister_ops
    unregister_ops()