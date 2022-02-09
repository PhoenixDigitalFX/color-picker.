import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, CollectionProperty

class GPMatItem(PropertyGroup):
    mat_name: StringProperty()

def register_data():
    bpy.utils.register_class(GPMatItem)
    bpy.types.Scene.gpmatpalette = CollectionProperty(type=GPMatItem)

def unregister_data():
    bpy.utils.unregister_class(GPMatItem)
    