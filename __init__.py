# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy

bl_info = {
    "name": "GP Color Picker",
    "author": "Les Fées Spéciales (LFS)",
    "description": "Quickly switch between materials of the active Grease pencil object",
    "blender": (3, 0, 0),
    "version": (1, 1, 0),
    "location": "Press S in Draw mode with a GP object activated",
    "category": "Materials"
}

addon_keymaps = [] 
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import *

''' Color theme of the addon '''
class GPCOLORPICKER_theme(PropertyGroup):
    pie_color: FloatVectorProperty(
            subtype='COLOR', name="Pie Color", min=0, max=1, size=4, default=(0.1,0.1,0.1,1.))
    line_color: FloatVectorProperty(
        subtype='COLOR', name="Line Color", min=0, max=1, size=4, default=(0.96,0.96,0.96,1.))
    text_color: FloatVectorProperty(
        subtype='COLOR', name="Text Color", min=0, max=1, size=4, default=(0.,0.,0.,1.))

''' --- Autoload useful functions --- '''

''' Check if palette files are obsolete (useful in Autocheck mode)'''
def refresh_obsoletes():  
    bpy.ops.scene.check_obsolete_palettes() 

    pname = (__package__).split('.')[0]
    prefs = bpy.context.preferences.addons[pname].preferences  
    if not prefs.autoload_mode.autocheck:
        return None

    timer = prefs.autoload_mode.timerval
    return timer

''' Register the refresh function as recurrent function if autocheck mode is on '''
def update_autocheck_mode(self, context):
    if self.autocheck and not bpy.app.timers.is_registered(refresh_obsoletes):
        bpy.app.timers.register(refresh_obsoletes)
    elif not self.autocheck and bpy.app.timers.is_registered(refresh_obsoletes):
        bpy.app.timers.unregister(refresh_obsoletes)

''' Select a default path for autoloaded palettes'''
def set_default_palette_path():
    pname = (__package__).split('.')[0]
    prefs = bpy.context.preferences.addons[pname].preferences  
    if prefs.autoload_mode.path:
        return 
    palette_path = bpy.utils.user_resource('SCRIPTS', path='GPpalettes')
    from os.path import isdir
    if isdir(palette_path):
        prefs.autoload_mode.path = palette_path

''' Autoload palette preferences settings '''
class GPCOLORPICKER_autoloadPalette(PropertyGroup):
    active: BoolProperty(default=False, name="Autoload mode ON", description="In autoload mode, palettes in the specified folder are automatically imported at file opening.")
    path: StringProperty(default="", name="Palettes path", subtype="DIR_PATH", description="Path chosen for the autoload palette mode")
    autocheck : BoolProperty(default=True, name="Set automatic checks", update=update_autocheck_mode, description="In autocheck mode, active palette files are frequently checked. If the file appears obsolete, a warning symbol appears in the palette panel.")
    timerval: IntProperty(default=60, name="Timer", subtype='TIME', min=5, description="Frequency (in seconds) of the autochecks for obsolete palettes.")

''' --- Keymapping useful functions --- '''
''' Note : keymaps are entered by hand in the addon preferences structures so that they can be saved after the file is closed'''
''' We thus restrict ourselves to a combination of CTRL+ADD+SHIFT+TYPE possibilities'''

''' When the keymap is updated in preference, we update the corresponding keymap item in the config'''
def update_keymap(self, context):
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps['3D View']
    kmi = km.keymap_items[self.kmi]
    kmi.ctrl = self.ctrl_mdf
    kmi.alt = self.alt_mdf
    kmi.shift = self.shift_mdf
    kmi.type = self.key_type

type_enum = ['NONE', 'LEFTMOUSE', 'MIDDLEMOUSE', 'RIGHTMOUSE', 'BUTTON4MOUSE', 'BUTTON5MOUSE', 'BUTTON6MOUSE', 'BUTTON7MOUSE', 'PEN', 'ERASER', 'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'TRACKPADPAN', 'TRACKPADZOOM', 'MOUSEROTATE', 'MOUSESMARTZOOM', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE', 'EVT_TWEAK_L', 'EVT_TWEAK_M', 'EVT_TWEAK_R', \
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', \
    'ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', \
    'LEFT_CTRL', 'LEFT_ALT', 'LEFT_SHIFT', 'RIGHT_ALT', 'RIGHT_CTRL', 'RIGHT_SHIFT', \
    'OSKEY', 'APP', 'GRLESS', 'ESC', 'TAB', 'RET', 'SPACE', 'LINE_FEED', 'BACK_SPACE', 'DEL', \
    'SEMI_COLON', 'PERIOD', 'COMMA', 'QUOTE', 'ACCENT_GRAVE', 'MINUS', 'PLUS', 'SLASH', 'BACK_SLASH', 'EQUAL', 'LEFT_BRACKET', 'RIGHT_BRACKET', 'LEFT_ARROW', 'DOWN_ARROW', 'RIGHT_ARROW', 'UP_ARROW', \
    'NUMPAD_2', 'NUMPAD_4', 'NUMPAD_6', 'NUMPAD_8', 'NUMPAD_1', 'NUMPAD_3', 'NUMPAD_5', 'NUMPAD_7', 'NUMPAD_9', 'NUMPAD_PERIOD', 'NUMPAD_SLASH', 'NUMPAD_ASTERIX', 'NUMPAD_0', 'NUMPAD_MINUS', 'NUMPAD_ENTER', 'NUMPAD_PLUS', \
    'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12', 'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 'F20', 'F21', 'F22', 'F23', 'F24', \
    'PAUSE', 'INSERT', 'HOME', 'PAGE_UP', 'PAGE_DOWN', 'END', 'MEDIA_PLAY', 'MEDIA_STOP', 'MEDIA_FIRST', 'MEDIA_LAST', 'TEXTINPUT', 'WINDOW_DEACTIVATE', \
    'TIMER', 'TIMER0', 'TIMER1', 'TIMER2', 'TIMER_JOBS', 'TIMER_AUTOSAVE', 'TIMER_REPORT', 'TIMERREGION', \
    'NDOF_MOTION', 'NDOF_BUTTON_MENU', 'NDOF_BUTTON_FIT', 'NDOF_BUTTON_TOP', 'NDOF_BUTTON_BOTTOM', 'NDOF_BUTTON_LEFT', 'NDOF_BUTTON_RIGHT', 'NDOF_BUTTON_FRONT', 'NDOF_BUTTON_BACK', 'NDOF_BUTTON_ISO1', 'NDOF_BUTTON_ISO2', 'NDOF_BUTTON_ROLL_CW', 'NDOF_BUTTON_ROLL_CCW', 'NDOF_BUTTON_SPIN_CW', 'NDOF_BUTTON_SPIN_CCW', 'NDOF_BUTTON_TILT_CW', 'NDOF_BUTTON_TILT_CCW', 'NDOF_BUTTON_ROTATE', 'NDOF_BUTTON_PANZOOM', 'NDOF_BUTTON_DOMINANT', 'NDOF_BUTTON_PLUS', 'NDOF_BUTTON_MINUS', 'NDOF_BUTTON_ESC', 'NDOF_BUTTON_ALT', 'NDOF_BUTTON_SHIFT', 'NDOF_BUTTON_CTRL', \
    'NDOF_BUTTON_1', 'NDOF_BUTTON_2', 'NDOF_BUTTON_3', 'NDOF_BUTTON_4', 'NDOF_BUTTON_5', 'NDOF_BUTTON_6', 'NDOF_BUTTON_7', 'NDOF_BUTTON_8', 'NDOF_BUTTON_9', 'NDOF_BUTTON_10', 'NDOF_BUTTON_A', 'NDOF_BUTTON_B', 'NDOF_BUTTON_C', \
    'ACTIONZONE_AREA', 'ACTIONZONE_REGION', 'ACTIONZONE_FULLSCREEN', 'XR_ACTION']
type_dct = [ (n,n,n,i) if n else None for i,n in enumerate(type_enum) ]

''' Keymapping to invoke the color picker '''
class GPCOLORPICKER_PickerKM(PropertyGroup):
    bl_dsc = "Invoke Picker"
    from . gpcolorpicker import GPCOLORPICKER_OT_wheel
    kmi: StringProperty(name="Keymap item name", default=GPCOLORPICKER_OT_wheel.bl_idname)
    key_type: EnumProperty(items=type_dct, name="Keymap type", default='A', update=update_keymap)
    ctrl_mdf: BoolProperty(name="Keymap Ctrl modifier", default=False, update=update_keymap)
    shift_mdf: BoolProperty(name="Keymap Shift modifier", default=False, update=update_keymap)
    alt_mdf: BoolProperty(name="Keymap Alt modifier", default=False, update=update_keymap)

''' Keymapping to invoke the palette editor '''
class GPCOLORPICKER_EditPaletteKM(PropertyGroup):
    bl_dsc = "Invoke Palette Editor"
    from . gppaletteeditor import GPCOLORPICKER_OT_paletteEditor
    kmi: StringProperty(name="Keymap item name", default=GPCOLORPICKER_OT_paletteEditor.bl_idname)
    key_type: EnumProperty(items=type_dct, name="Keymap type", default='A', update=update_keymap)
    ctrl_mdf: BoolProperty(name="Keymap Ctrl modifier", default=False, update=update_keymap)
    shift_mdf: BoolProperty(name="Keymap Shift modifier", default=True, update=update_keymap)
    alt_mdf: BoolProperty(name="Keymap Alt modifier", default=True, update=update_keymap)
    
''' --- Overall Addon preferences --- '''
class GPCOLORPICKER_preferences(AddonPreferences):
    bl_idname = __name__

    icon_scale: IntProperty(name="Icon scale", min=100, default=460, max=800)    
    theme: PointerProperty(type=GPCOLORPICKER_theme)
    mat_mode: EnumProperty(name="Material Mode", default="from_palette",\
             items=[("from_active", "From Active", 'Set Materials from active object'), ("from_palette", "From Palette", 'Set Materials GP Palettes')])
    assign_mat: BoolProperty(name="Assign material on selection", default= True,  \
        description="Check this option if you want the materials you selected to be assigned automatically to the current object. Otherwise, selecting a material will only work if the object already has it.")
    autoload_mode: PointerProperty(type=GPCOLORPICKER_autoloadPalette, name="Autoload")
    picker_keymap: PointerProperty(type=GPCOLORPICKER_PickerKM, name="Picker keymap")
    palette_edit_keymap: PointerProperty(type=GPCOLORPICKER_EditPaletteKM, name="Palette Edit keymap")
    use_default_brushes: BoolProperty(name="Use default brushes", default=True, description="With this mode, you can define a default brush for any material, the brush will be selected when the material is picked with the GP Color Picker")

    def draw(self, context):
        layout = self.layout
        frow = layout.row()
        fcol = frow.column()
        stgs = fcol.box()
        stgs.label(text="Settings", icon='MODIFIER')
        stgs.prop(self, "icon_scale", slider=True)

        # THEME prefs
        props = fcol.box()
        props.label(text="Theme", icon='RESTRICT_COLOR_ON')
        props.prop(self.theme, 'pie_color', text="Pie Color")
        props.prop(self.theme, 'line_color', text="Line Color")
        props.prop(self.theme, 'text_color', text="Text Color")

        # MATERIALS MODE prefs
        scol = frow.column()
        mats = scol.box()
        mats.label(text="Materials", icon='MATERIAL')
        mats.row().prop_tabs_enum(self, "mat_mode")
        if self.mat_mode == "from_palette":
            # AUTOLOAD MODE prefs
            row = mats.row()
            row.prop(self.autoload_mode, "active", text="Autoload palettes")

            if self.autoload_mode.active:
                row.prop(self.autoload_mode, "path", text="")
                row.operator("scene.autoload_palette", text="", icon= "FILE_REFRESH")

            # AUTOCHECK MODE prefs
            row = mats.row()
            row.prop(self.autoload_mode, "autocheck")
            if self.autoload_mode.autocheck:
                row.prop(self.autoload_mode, "timerval")

            # DEFAULT BRUSH mode
            row = mats.row()
            row.prop(self, "use_default_brushes")

        # KEYMAPPING prefs
        prv = scol.box()
        prv.label(text="Keymap", icon='BLENDER')

        # Invoke Picker KM
        row = prv.row()
        row.label(text=self.picker_keymap.bl_dsc)
        row.prop(self.picker_keymap, "ctrl_mdf", icon="EVENT_CTRL", text="")
        row.prop(self.picker_keymap, "alt_mdf", icon="EVENT_ALT", text="")
        row.prop(self.picker_keymap, "shift_mdf", icon="EVENT_SHIFT", text="")
        row.prop(self.picker_keymap, "key_type", text="")

        # Palette Editor KM
        row = prv.row()
        row.label(text=self.palette_edit_keymap.bl_dsc)
        row.prop(self.palette_edit_keymap, "ctrl_mdf", icon="EVENT_CTRL", text="")
        row.prop(self.palette_edit_keymap, "alt_mdf", icon="EVENT_ALT", text="")
        row.prop(self.palette_edit_keymap, "shift_mdf", icon="EVENT_SHIFT", text="")
        row.prop(self.palette_edit_keymap, "key_type", text="")
    
''' --- Class Registration --- '''
classes = [ GPCOLORPICKER_theme, \
            GPCOLORPICKER_autoloadPalette, \
            GPCOLORPICKER_PickerKM, \
            GPCOLORPICKER_EditPaletteKM, \
            GPCOLORPICKER_preferences
          ]

def register():
    for cls in classes:
        bpy.utils.register_class(cls) 

    from . gpmatpalette import register as register_palette
    register_palette()

    from . gpcolorpicker import register as register_picker
    register_picker(addon_keymaps)

    from . gppaletteeditor import register as register_editor
    register_editor(addon_keymaps)

    prefs = bpy.context.preferences.addons[__package__].preferences
    if prefs and (not bpy.app.timers.is_registered(refresh_obsoletes)):
        bpy.app.timers.register(refresh_obsoletes)
    
    set_default_palette_path()

def unregister():        
    if bpy.app.timers.is_registered(refresh_obsoletes):
        bpy.app.timers.unregister(refresh_obsoletes)

    # Remove the hotkey
    for km, kmi, dsc in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    from . gppaletteeditor import unregister as unregister_editor
    unregister_editor()
    
    from . gpcolorpicker import unregister as unregister_picker
    unregister_picker()

    from .gpmatpalette import unregister as unregister_palette
    unregister_palette()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register() 
