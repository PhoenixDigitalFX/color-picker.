import math
import bpy,gpu
from bpy.types import PropertyGroup
from bpy.props import *

class GPMatItem(PropertyGroup):
    mat_name: StringProperty()
    custom_angle: FloatProperty(subtype='ANGLE', default=-1)
    image: StringProperty(subtype='FILE_NAME')
    layer: StringProperty()

    def clear(self):
        # Remove image from database
        if self.image in bpy.data.images:
            bpy.data.images.remove(bpy.data.images[self.image])
        self.image = ""

class GPMatPalette(PropertyGroup):
    bl_idname= "scene.gpmatpalette"
    materials: CollectionProperty(type=GPMatItem)
    image: StringProperty(subtype='FILE_NAME')

    # Safety check to use custom angles
    # all materials should have one, and the angles should be in increasing order
    def hasCustomAngles(self):
        a = 0
        for m in self.materials:
            if (m.custom_angle < a) or (m.custom_angle > 2*math.pi):
                return False
            a = m.custom_angle
        return True        
        
    def clear(self):
        for m in self.materials:
            m.clear()

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
    