import bpy

bl_info = {
    "name": "GP Color Picker",
    "author": "Les Fées Spéciales (LFS)",
    "description": "Quickly switch between materials of the active Grease pencil object",
    "blender": (3, 0, 0),
    "version": (1,0,1),
    "location": "Press S in Draw mode with a GP object activated",
    "category": "00"
}

from . op import GPCOLORPICKER_OT_wheel,settings

### ----------------- User Preferences
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import *
import json, os
class GPCOLORPICKER_theme(PropertyGroup):
    pie_color: FloatVectorProperty(
            subtype='COLOR', name="Pie Color", min=0, max=1, size=4, default=(0.4,0.4,0.4,1.))
    line_color: FloatVectorProperty(
        subtype='COLOR', name="Line Color", min=0, max=1, size=4, default=(0.96,0.96,0.96,1.))
    text_color: FloatVectorProperty(
        subtype='COLOR', name="Text Color", min=0, max=1, size=4, default=(0.,0.,0.,1.))

class GPCOLORPICKER_preferences(AddonPreferences):
    bl_idname = __name__
    crt_fpt = ''

    # TODO: add keymap in prefs    
    icon_scale: IntProperty(
        name="Icon scale",
        min=100, default=250, max=500
    )    

    def on_file_update(self, value):
        fpt = self.json_fpath
        if fpt == self.crt_fpt:
            return

        if not os.path.isfile(fpt):
            print("Error : {} path not found".format(fpt))
            return 

        fnm = os.path.basename(fpt)
        ext = fnm.split(os.extsep)
        
        if (len(ext) < 2) or (ext[-1] != "json"):
            print("Error : {} is not a json file".format(fnm))
            return 
        
        #TODO: fix this update that does not work
        self.crt_fpt = fpt
        
        ifl = open(fpt, 'r')
        ctn = json.load(ifl)
        ifl.close()

        print(ctn)

    theme: PointerProperty(type=GPCOLORPICKER_theme)
    json_fpath: StringProperty(
        subtype='FILE_PATH', name='File path', update=on_file_update, options={'TEXTEDIT_UPDATE'})

    mat_mode: EnumProperty(name="Material Mode", items=[("from_active", "From Active", 'Set Materials from active object'), ("from_file", "From File", 'Set Materials from JSON file')], \
                            default="from_file")

    def draw(self, context):
        layout = self.layout
        frow = layout.row()
        fcol = frow.column()
        stgs = fcol.box()
        stgs.label(text="Settings", icon='MODIFIER')
        stgs.prop(self, "icon_scale")

        props = fcol.box()
        props.label(text="Theme", icon='RESTRICT_COLOR_ON')
        props.prop(self.theme, 'pie_color', text="Pie Color")
        props.prop(self.theme, 'line_color', text="Line Color")
        props.prop(self.theme, 'text_color', text="Text Color")

        scol = frow.column()
        mats = scol.box()
        mats.label(text="Materials", icon='MATERIAL')
        mats.row().prop_tabs_enum(self, "mat_mode")

        if self.mat_mode == "from_file":
            mats.prop(self, "json_fpath")

        prv = scol.box()
        prv.label(text="Preview", icon='NONE')
    

addon_keymaps = [] 
        
def register():
    bpy.utils.register_class(GPCOLORPICKER_OT_wheel)
    bpy.utils.register_class(GPCOLORPICKER_theme)
    bpy.utils.register_class(GPCOLORPICKER_preferences)
    
    # Add the hotkey
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(GPCOLORPICKER_OT_wheel.bl_idname, \
                                    type=settings.key_shortcut, value='PRESS')
        addon_keymaps.append((km, kmi))
    

def unregister():        
    # Remove the hotkey
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_class(GPCOLORPICKER_theme)
    bpy.utils.unregister_class(GPCOLORPICKER_preferences)
    bpy.utils.unregister_class(GPCOLORPICKER_OT_wheel)
    
    
if __name__ == "__main__":
    register() 
