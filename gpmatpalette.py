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
    bl_idname= "scene.gpmatpalettes.palette"
    name: StringProperty(default="unnamed")
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

class GPMatPalettes(PropertyGroup):
    bl_idname= "scene.gpmatpalettes"
        
    palettes: CollectionProperty(type=GPMatPalette)
    active_index: IntProperty(default=-1)

    def active(self):
        if (self.active_index < 0) or (self.active_index >= len(self.palettes)):
            return None
        return self.palettes[self.active_index]

    def next(self):
        self.active_index = (self.active_index + 1) % len(self.palettes)



def register_data():
    bpy.utils.register_class(GPMatItem)
    bpy.utils.register_class(GPMatPalette)
    bpy.utils.register_class(GPMatPalettes)
    bpy.types.Scene.gpmatpalettes = PointerProperty(type=GPMatPalettes)

def unregister_data():
    bpy.utils.unregister_class(GPMatPalettes)
    bpy.utils.unregister_class(GPMatPalette)
    bpy.utils.unregister_class(GPMatItem)
    