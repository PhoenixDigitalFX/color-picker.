import bpy
from . paledit_ops import GPCOLORPICKER_OT_paletteEditor

default_invoke_key = "A"

def register(addon_keymaps):
    from . paledit_ops import register as register_ops
    register_ops()

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(GPCOLORPICKER_OT_paletteEditor.bl_idname, \
                                    type=default_invoke_key, value='PRESS',shift=True, alt=True)
        addon_keymaps.append((km, kmi, "Invoke Palette Editor"))

def unregister():        
    from . paledit_ops import unregister as unregister_ops
    unregister_ops()