import bpy
from . picker_ops import GPCOLORPICKER_OT_wheel

classes = [GPCOLORPICKER_OT_wheel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():        
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)