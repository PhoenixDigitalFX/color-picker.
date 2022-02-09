import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, CollectionProperty, PointerProperty

class GPMatItem(PropertyGroup):
    mat_name: StringProperty()

class GPMatPalette(PropertyGroup):
    materials: CollectionProperty(type=GPMatItem)
    image: StringProperty(subtype='FILE_PATH')

    def clear(self):
        self.materials.clear()
        self.image = ''

def register_data():
    bpy.utils.register_class(GPMatItem)
    bpy.utils.register_class(GPMatPalette)
    bpy.types.Scene.gpmatpalette = PointerProperty(type=GPMatPalette)

def unregister_data():
    bpy.utils.unregister_class(GPMatPalette)
    bpy.utils.unregister_class(GPMatItem)
    