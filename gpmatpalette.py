import math
import bpy,gpu
from bpy.types import PropertyGroup
from bpy.props import *

class GPMatItem(PropertyGroup):
    mat_name: StringProperty()
    custom_angle: FloatProperty(subtype='ANGLE', default=-1)

class GPMatPalette(PropertyGroup):
    bl_idname= "scene.gpmatpalette"
    materials: CollectionProperty(type=GPMatItem)
    image: StringProperty(subtype='FILE_NAME')

    def hasCustomAngles(self):
        for m in self.materials:
            if m.custom_angle < 0:
                return False
        return True        
        
    def clear(self):
        self.materials.clear()
        
        # Remove image from database
        if self.image in bpy.data.images:
            bpy.data.images.remove(bpy.data.images[self.image])
        self.image = ""

def register_data():
    bpy.utils.register_class(GPMatItem)
    bpy.utils.register_class(GPMatPalette)
    bpy.types.Scene.gpmatpalette = PointerProperty(type=GPMatPalette)

def unregister_data():
    bpy.context.scene.gpmatpalette.clear()
    bpy.utils.unregister_class(GPMatPalette)
    bpy.utils.unregister_class(GPMatItem)
    