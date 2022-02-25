import bpy,gpu,os
from bpy.types import PropertyGroup
from bpy.props import *
import numpy as np
import math
from . palette_maths import get_unset_intervals

class GPMatImage(PropertyGroup):
    name: StringProperty(subtype='FILE_NAME')
    path: StringProperty(subtype='FILE_PATH')

    def get(self):
        if not self.is_registered():
            if not self.file_exists():
                return None
            self.reload()
        return bpy.data.images[self.name]

    def is_registered(self):
        return (self.name in bpy.data.images)
    
    def file_exists(self):
        return os.path.isfile(self.path)
    
    def load(self, path, path_prefix="", overload_existing=False):
        self.path = os.path.join(path_prefix, path)
        self.reload(overload_existing)

    def reload(self, check_existing=False):
        im = bpy.data.images.load(filepath=self.path, check_existing=check_existing)
        self.name = im.name
    
    def remove(self):
        if not self.is_registered(): 
            return
        bpy.data.images.remove(bpy.data.images[self.name])
    
    def isempty(self):
        return (self.name == "")

    def clear(self):
        self.remove()
        self.name = ""
        self.path = ""
    
class GPMatPosInPicker(PropertyGroup):
    ox : FloatProperty(default=0)
    oy : FloatProperty(default=0)
    has_pick_line: BoolProperty(default=False)
    angle: FloatProperty(subtype="ANGLE", default=-1)
    is_angle_movable: BoolProperty(default=True)


class GPMatItem(PropertyGroup):
    name: StringProperty()
    pos_in_picker: PointerProperty(type=GPMatPosInPicker)
    image: PointerProperty(type=GPMatImage)
    layer: StringProperty()

    def clear(self):
        # Remove image from database
        self.image.clear()
    
    def has_pick_line(self):
        return self.pos_in_picker.has_pick_line
    
    def is_angle_movable(self):
        return self.pos_in_picker.is_angle_movable
    
    def get_angle(self, only_if_not_movable = False):
        if only_if_not_movable and self.pos_in_picker.is_angle_movable:
            return -1
        return self.pos_in_picker.angle
    
    def set_angle(self, a, auto=False):
        self.pos_in_picker.angle = a
        self.pos_in_picker.is_angle_movable = auto

    def set_origin(self, origin, auto=False):
        pp = self.pos_in_picker
        pp.ox = origin[0]
        pp.oy = origin[1]
        pp.has_pick_line = not auto
    
    def get_origin(self, with_bool = False):
        pp = self.pos_in_picker
        if with_bool:
            return [pp.ox, pp.oy, pp.has_pick_line]
        return [pp.ox, pp.oy]


class GPMatPalette(PropertyGroup):
    bl_idname= "scene.gpmatpalettes.palette"
    name: StringProperty(default="unnamed")
    materials: CollectionProperty(type=GPMatItem)
    image: PointerProperty(type=GPMatImage)
    source_path: StringProperty(subtype='FILE_PATH')
    visible: BoolProperty(default=True)

    def autocomp_positions(self):
        angles = [(m.get_angle(True), i) for i,m in enumerate(self.materials)]
        angles_to_set = get_unset_intervals(angles)
        for (a, b, ids) in angles_to_set:
            b_ = b
            if a >= b:
                b_ += 2*math.pi
            angles = np.linspace(a,b_,len(ids)+2)[1:-1]
            for i,mat_id in enumerate(ids):
                a = angles[i] % (2*math.pi)
                self.materials[mat_id].set_angle(a, auto=True)
        
        for m in self.materials:
            if m.pos_in_picker.has_pick_line:
                continue
            a = m.get_angle()
            m.set_origin([math.cos(a), math.sin(a)], auto=True)
    
    def get_index_by_angle(self, angle):
        ind = 0
        for m in self.materials:
            a = m.pos_in_picker.angle
            if (a >= angle):
                return ind
            ind += 1
        return ind
    
    def set_material_by_angle(self, name, angle, auto=False):
        ind = self.get_index_by_angle(angle)
        matit = self.set_material(name, ind)
        matit.set_angle(angle, auto)

    def set_material(self, name, index = -1):
        old_id = self.count()
        if name in self.materials:
            old_id = self.materials.find(name)
            if old_id < index:
                index = index - 1
        else:
            matit = self.materials.add()
            matit.name = name
        if (index >= 0) and (index != old_id):
            self.materials.move(old_id, index)
        return self.materials[name]

    def clear(self):
        for m in self.materials:
            m.clear()
        self.materials.clear()
        self.image.clear()

    def count(self):
        return len(self.materials)

def update_palette_active_index(self,context):
    if self.active_index == -1:
        return
    if self.palettes[self.active_index].visible:
        return
    if not any([p.visible for p in self.palettes]):
        self.active_index = -1
        return
    self.next()
class GPMatPalettes(PropertyGroup):
    bl_idname= "scene.gpmatpalettes"
        
    palettes: CollectionProperty(type=GPMatPalette)
    active_index: IntProperty(default=-1, update=update_palette_active_index)

    def __init__(self):
        self.palettes.clear()
        self.active_index = -1

    def active(self):
        if (self.active_index < 0) or (self.active_index >= len(self.palettes)):
            return None
        return self.palettes[self.active_index]

    def next(self):
        self.active_index = (self.active_index + 1) % len(self.palettes)

    def nextVisible(self):
        if not any([p.visible for p in self.palettes]):
            return

        self.next()
        while not self.palettes[self.active_index].visible:
            self.next()

    def count(self):
        return len(self.palettes)

    def clear(self):
        for p in self.palettes:
            p.clear()

        self.palettes.clear()
        self.active_index = -1

classes = [GPMatImage, GPMatPosInPicker, GPMatItem, GPMatPalette, GPMatPalettes]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gpmatpalettes = PointerProperty(type=GPMatPalettes)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    