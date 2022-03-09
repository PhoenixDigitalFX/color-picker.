# Properties definition for Palette data
import bpy, math
from bpy.types import PropertyGroup
from bpy.props import *
import numpy as np
from . palette_maths import get_unset_intervals

''' Position of a material in the picker'''
class GPMatItem(PropertyGroup):
    name: StringProperty(name= "Material name")

    image: PointerProperty(type=bpy.types.Image, name="Material palette image")
    layer: StringProperty(name="Material layers")

    angle: FloatProperty(subtype="ANGLE", default=-1, name="Material position around the wheel")
    is_angle_movable: BoolProperty(default=True, name="Is position computed by default or set manually")

    has_pick_line: BoolProperty(default=False, name="Material has pickline")
    ox : FloatProperty(default=0, name="Pickline origin x coordinate")
    oy : FloatProperty(default=0, name="Pickline origin y coordinate")

    def clear(self):
        pass
    
    def get_angle(self, only_if_not_movable = False):
        if only_if_not_movable and self.is_angle_movable:
            return -1
        return self.angle
    
    def set_angle(self, a, auto=False):
        self.angle = a
        self.is_angle_movable = auto

    def set_origin(self, origin, auto=False):
        self.ox = origin[0]
        self.oy = origin[1]
        self.has_pick_line = not auto
    
    def get_origin(self, with_bool = False):
        if with_bool:
            return [self.ox, self.oy, self.has_pick_line]
        return [self.ox, self.oy]

def update_im(self, context):
    self.is_dirty = True
    if self.image:
        self.image.pack()

def update_with_lock(self, context):
    if self.is_obsolete != self.lock_obsolete:
        self.is_obsolete = self.lock_obsolete
class GPMatPalette(PropertyGroup):
    bl_idname= "scene.gpmatpalettes.palette"
    name: StringProperty(default="unnamed")
    materials: CollectionProperty(type=GPMatItem)
    image: PointerProperty(type=bpy.types.Image, update=update_im)
    source_path: StringProperty(subtype='FILE_PATH')
    visible: BoolProperty(default=True)
    is_dirty: BoolProperty(default=False)
    is_obsolete: BoolProperty(default=False, name = "Obsolete", description="A new version of the palette exists", update=update_with_lock)
    lock_obsolete: BoolProperty(default=False)
    pending_material: PointerProperty(type=bpy.types.Material)
    autoloaded: BoolProperty(default=False)
    timestamp: StringProperty(default="")

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
            if m.has_pick_line:
                continue
            a = m.get_angle()
            m.set_origin([math.cos(a), math.sin(a)], auto=True)
    
    def get_index_by_angle(self, angle):
        ind = 0
        for m in self.materials:
            a = m.angle
            if (a >= angle):
                return ind
            ind += 1
        return ind
    
    def set_material_by_angle(self, name, angle, auto=False):
        ind = self.get_index_by_angle(angle)
        matit = self.set_material(name, ind)
        matit.set_angle(angle, auto)
        return matit

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
        self.autocomp_positions()
        return self.materials[name]
    

    def remove_material(self, ind):
        self.materials.remove(ind)
        self.is_dirty = True

    def clear(self):
        for m in self.materials:
            m.clear()
        self.materials.clear()
        self.image = None

    def count(self):
        return len(self.materials)
    
    def is_material_available(self, mat):
        if (not mat) or (not mat.is_grease_pencil):
            return False
        return not mat.name in self.materials
    
    def is_same_timestamp(self, other_tmstp):
        return (self.timestamp == other_tmstp)

    def accept_pending_material(self, angle=-1):
        if not self.is_material_available(self.pending_material):
            self.pending_material = None
            return False
        mat = self.pending_material
        if angle >= 0:
            self.set_material_by_angle(mat.name, angle)
        else:
            self.set_material(mat.name)
        self.pending_material = None
        self.is_dirty = True
        return True

    def set_obsolete(self, val):
        self.lock_obsolete = val
        self.is_obsolete = self.lock_obsolete

''' --- Palette collection container --- '''

''' Update callback for active index : switch to next visible palette '''
def update_palette_active_index(self, context):
    if self.active_index == -1:
        return
    if self.palettes[self.active_index].visible:
        return
    if not any([p.visible for p in self.palettes]):
        self.active_index = -1
        return
    # Next visible palette in the memorized direction
    self.next()
class GPMatPalettes(PropertyGroup):
    bl_idname= "scene.gpmatpalettes"
        
    palettes: CollectionProperty(name= "Palettes", type=GPMatPalette)
    active_index: IntProperty(name="Active palette index", default=-1, update=update_palette_active_index)

    is_dirty: BoolProperty(name="Was palette collection just modified", default=False)
    is_obsolete: BoolProperty(name="Is palette collection based on obsolete files", default=False)

    mem_dir: IntProperty(name="Last direction of navigation between palettes", default=1)

    def __init__(self):
        self.palettes.clear()
        self.active_index = -1

    def active(self):
        if (self.active_index < 0) or (self.active_index >= len(self.palettes)):
            return None
        return self.palettes[self.active_index]

    def next(self, dir=0):
        if dir != 0:
            # this is useful for the update callback of active_index
            self.mem_dir = dir
        self.active_index = (self.active_index + self.mem_dir) % len(self.palettes)

    def count(self):
        return len(self.palettes)
    
    def is_empty(self):
        return (self.count() == 0)

    def clear(self):
        for p in self.palettes:
            p.clear()

        self.palettes.clear()
        self.active_index = -1

    def add_palette(self, name):
        npal = self.palettes.add()
        npal.name = name
        self.active_index = self.count()-1
        npal.image = None
        self.is_dirty = True
    
    def remove_palette_by_id(self, index):
        npal = self.count()
        active_ind = self.active_index

        pal = self.palettes[index]
        pal.clear()
        self.palettes.remove(index)

        if active_ind == npal-1:
            self.active_index = npal-2
        elif active_ind == index:
            self.next(1)

    def remove_palette(self, name):
        ind = self.palettes.find(name)
        if ind < 0:
            return        
        self.remove_palette_by_id(ind)

    def needs_refresh(self):
        return (self.is_dirty) or any([p.is_dirty for p in self.palettes])
    
    def all_refreshed(self):
        self.is_dirty = False
        for p in self.palettes:
            p.is_dirty = False

classes = [ GPMatItem, GPMatPalette, GPMatPalettes]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gpmatpalettes = PointerProperty(type=GPMatPalettes)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    