# Properties definition for Palette data
import bpy, math
from bpy.types import PropertyGroup
from bpy.props import *
import numpy as np
from . palette_maths import get_unset_intervals

''' --- Material Item --- '''
class GPMatItem(PropertyGroup):
    name: StringProperty(name= "Name")

    image: PointerProperty(type=bpy.types.Image, name="Image", description="Image to be displayed in the picker when material is in selection")
    layer: StringProperty(name="Layer", description="Layer to switch to when material is selected")

    angle: FloatProperty(name="Angle", description="Material angle position in the picker", subtype="ANGLE", default=-1)
    is_angle_movable: BoolProperty(name="Movable", description="The angle is computed dynamically",default=True)

    has_pick_line: BoolProperty(name="Has Pickline", default=False)
    ox : FloatProperty(name="Origin X", default=0, description="Pickline origin x coordinate")
    oy : FloatProperty(name="Origin Y", default=0, description="Pickline origin y coordinate")

    ''' Clear all material item data '''
    def clear(self):
        self.image = None
    
    ''' Getter for angle property '''
    def get_angle(self, only_if_not_movable = False):
        if only_if_not_movable and self.is_angle_movable:
            return -1
        return self.angle

    ''' Setter for angle property'''
    def set_angle(self, a, auto=False):
        self.angle = a
        self.is_angle_movable = auto

    ''' Setter for pickline origin (both x and y coordinates)'''
    def set_origin(self, origin, auto=False):
        self.ox = origin[0]
        self.oy = origin[1]
        self.has_pick_line = not auto
    
    ''' Getter for pickline origin (both x and y coordinates)
        If with_bool is set to True, an additionnal 3D coord will be added
        indicating whether the pickline exists or not
    '''
    def get_origin(self, with_bool = False):
        if with_bool:
            return [self.ox, self.oy, self.has_pick_line]
        return [self.ox, self.oy]

''' --- Palette --- '''

''' Update callback for the Image property
'''
def update_im(self, context):
    self.is_dirty = True
    if self.image:
        self.image.pack()

''' Update callback for the is_obsolete property
    We use a lock to prevent direct modification in the UI
'''
def update_with_lock(self, context):
    if self.is_obsolete != self.lock_obsolete:
        self.is_obsolete = self.lock_obsolete
class GPMatPalette(PropertyGroup):
    bl_idname= "scene.gpmatpalettes.palette"

    name: StringProperty(name="Name", default="unnamed")
    materials: CollectionProperty(name = "Materials", description="List of materials sorted by angle", type=GPMatItem)
    image: PointerProperty(name="Image", type=bpy.types.Image, update=update_im)
    visible: BoolProperty(name="Visible", default=True)

    autoloaded: BoolProperty(name="Autoloaded", default=False)
    source_path: StringProperty(name="Source Path", default = "", subtype='FILE_PATH')
    timestamp: StringProperty(name="Timestamp", default="")

    is_dirty: BoolProperty(name="Dirty", description="The palette was modified recently", default=False)
    is_obsolete: BoolProperty(name = "Obsolete", description="A new version of the palette exists", default=False,  update=update_with_lock)
    lock_obsolete: BoolProperty(default=False)
    
    pending_material: PointerProperty(type=bpy.types.Material)

    ''' Automatic completion of material angle positions
        useful when some are not specified
    '''
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
    
    ''' Get material index from angle position
        Useful to insert a material at a certain angle position
    '''
    def get_index_by_angle(self, angle):
        ind = 0
        for m in self.materials:
            a = m.angle
            if (a >= angle):
                return ind
            ind += 1
        return ind
    
    ''' Insert a new material at a given angle position
    '''
    def set_material_by_angle(self, name, angle, auto=False):
        ind = self.get_index_by_angle(angle)
        matit = self.set_material(name, ind)
        matit.set_angle(angle, auto)
        return matit

    ''' Insert a new material at a given collection index
        If index is unspecified or < 0, the material will be inserted at the end of the collection
    '''
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
    
    ''' Remove a material from the collection (given by collection index) '''
    def remove_material(self, ind):
        self.materials.remove(ind)
        self.is_dirty = True

    ''' Clearing all palette data '''
    def clear(self):
        for m in self.materials:
            m.clear()
        self.materials.clear()
        self.image = None
    
    ''' Number of materials in collection '''
    def count(self):
        return len(self.materials)
    
    ''' Can a material be added to collection '''
    def is_material_available(self, mat):
        if (not mat) or (not mat.is_grease_pencil):
            return False
        return not mat.name in self.materials
    
    ''' Timestamp comparison function '''
    def is_same_timestamp(self, other_tmstp):
        return (self.timestamp == other_tmstp)

    ''' Adds the pending material in the collection
        Useful in palette editor on addmaterial operator
    '''
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

    ''' Setter for the is_obsolete property
        We use a lock to prevent direct modification in the UI
    '''
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

    is_dirty: BoolProperty(name="Dirty", description="The palette collection was modified recently", default=False)
    is_obsolete: BoolProperty(name="Obsolete", description="The palette collection is based on obsolete files", default=False)

    mem_dir: IntProperty(name="Mem dir", description="Last direction of navigation between palettes", default=1)

    ''' Get active palette '''
    def active(self):
        if (self.active_index < 0) or (self.active_index >= len(self.palettes)):
            return None
        return self.palettes[self.active_index]

    ''' Get next visible palette
        in increasing index order if dir == 1
        in decreasing index order if dir == -1
        in same order as previous call if dir == 0
    '''
    def next(self, dir=0):
        if dir != 0:
            # this is useful for the update callback of active_index
            self.mem_dir = dir
        self.active_index = (self.active_index + self.mem_dir) % len(self.palettes)

    ''' Get nb of palettes in collection'''
    def count(self):
        return len(self.palettes)
    
    ''' Return True if no palettes in collection, False otherwise '''
    def is_empty(self):
        return (self.count() == 0)

    ''' Removes all the palettes and clears the associated data '''
    def clear(self):
        for p in self.palettes:
            p.clear()

        self.palettes.clear()
        self.active_index = -1

    ''' Creates and adds a new palette with the given name '''
    def add_palette(self, name):
        npal = self.palettes.add()
        npal.name = name
        self.active_index = self.count()-1
        npal.image = None
        self.is_dirty = True
    
    ''' Removes the palette at the given id in the collection '''
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

    ''' Removes the palette of the given name in collection '''
    def remove_palette(self, name):
        ind = self.palettes.find(name)
        if ind < 0:
            return        
        self.remove_palette_by_id(ind)

    ''' Checks if the collection or any palette has recently been changed '''
    def needs_refresh(self):
        return (self.is_dirty) or any([p.is_dirty for p in self.palettes])
    
    ''' Removes all the dirty flags of the collection '''
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
    