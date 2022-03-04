import bpy
from . picker_ops import GPCOLORPICKER_OT_wheel

classes = [GPCOLORPICKER_OT_wheel]
default_invoke_key = "A"

def register(addon_keymaps):
    for cls in classes:
        bpy.utils.register_class(cls)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(GPCOLORPICKER_OT_wheel.bl_idname, \
                                    type=default_invoke_key, value='PRESS')
        addon_keymaps.append((km, kmi, "Invoke Picker"))

def unregister():        
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)