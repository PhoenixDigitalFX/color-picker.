import bpy
from . paledit_ops import GPCOLORPICKER_OT_paletteEditor

classes = [GPCOLORPICKER_OT_paletteEditor]
default_invoke_key = "A"

def register(addon_keymaps):
    for cls in classes:
        bpy.utils.register_class(cls)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(GPCOLORPICKER_OT_paletteEditor.bl_idname, \
                                    type=default_invoke_key, value='PRESS',shift=True, alt=True)
        addon_keymaps.append((km, kmi))

def unregister():        
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)