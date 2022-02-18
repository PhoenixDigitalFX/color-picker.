import bpy
from . picker_ops import GPCOLORPICKER_OT_wheel,settings

classes = [GPCOLORPICKER_OT_wheel]

def register(addon_keymaps):
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


def unregister(addon_keymaps):        
    # Remove the hotkey
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)