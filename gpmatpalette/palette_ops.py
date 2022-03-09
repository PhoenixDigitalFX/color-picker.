import os, bpy, json
from . palette_io import getJSONfiles, parseJSONFile, export_palettes_content

''' Check if one or more palette files are now obsolete '''
class GPCOLORPICKER_OT_checkObsoletePalettes(bpy.types.Operator):
    bl_idname = "scene.check_obsolete_palettes"
    bl_label = "Check obsolete palettes"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context): 
        from json import load

        def get_palette_names(pth):
            ifl = open(pth, 'r')
            data = load(ifl)
            ifl.close()
            tmstp = ""
            if ("__meta__" in data) and ("timestamp" in
             data["__meta__"]): 
                tmstp = data["__meta__"]["timestamp"]
            pal_names = set( pname for pname in data.keys() if (not pname.startswith("__")) )
            return pal_names, tmstp

        # Get palette dir in user preferences
        pname = (__package__).split('.')[0]
        prefs = context.preferences.addons[pname].preferences
        if prefs is None : 
            self.report({'WARNING'}, "Could not load user preferences")
            return {'CANCELLED'}

        palette_files = set()
      
        dirpath = prefs.autoload_mode.path
        if prefs.autoload_mode.active and os.path.isdir(dirpath):
            palette_files = getJSONfiles(dirpath)  

        gpmp = context.scene.gpmatpalettes
        palette_files.union({pal.source_path for pal in gpmp.palettes})

        for pth in palette_files:
            pal_names, tmstp = get_palette_names(pth)
            for pname in pal_names:
                if not pname in gpmp.palettes:
                    gpmp.is_obsolete = True
                    continue
                if (tmstp) and (not gpmp.palettes[pname].is_same_timestamp(tmstp)):
                    gpmp.palettes[pname].set_obsolete(True)
                    gpmp.is_obsolete = True

        return {"FINISHED"}

''' Automatic import of the palettes in the files in the autoload path'''
class GPCOLORPICKER_OT_autoloadPalette(bpy.types.Operator):
    bl_idname = "scene.autoload_palette"
    bl_label = "Autoload palette"    

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context): 
        # Get palette dir in user preferences
        pname = (__package__).split('.')[0]
        prefs = context.preferences.addons[pname].preferences
        if prefs is None : 
            self.report({'WARNING'}, "Could not load user preferences")
            return {'CANCELLED'}
      
        dirpath = prefs.autoload_mode.path
        if not os.path.isdir(dirpath):
            self.report({'WARNING'}, "Invalid palette path")
            return {'CANCELLED'}
        
        # Remove previously autoloaded palettes
        gpmp = context.scene.gpmatpalettes
        autoloaded_pal = set(pal.name for pal in gpmp.palettes if pal.autoloaded)
        for pname in autoloaded_pal:
            gpmp.remove_palette(pname)

        # Load palettes
        palette_files = getJSONfiles(dirpath)   
        palette_names = set()
        for pfile in palette_files:
            palette_names = palette_names.union(parseJSONFile(pfile))
                     
        for pname in palette_names:
            gpmp.palettes[pname].autoloaded = True 
            gpmp.palettes[pname].set_obsolete(False)

        return {"FINISHED"}

class GPCOLORPICKER_OT_importPalettes(bpy.types.Operator):
    bl_idname = "scene.import_palette"
    bl_label = "Import Palette"    

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context): 
        fpt = self.filepath     

        palette_names = parseJSONFile(fpt, clear_existing=True)

        gpmp = context.scene.gpmatpalettes
        for pname in palette_names:
            pal = gpmp.palettes[pname]
            pal.source_path = fpt
            pal.autoloaded = False 
            pal.set_obsolete(False)

        # Update data in user preferences
        pname = (__package__).split('.')[0]
        prefs = context.preferences.addons[pname].preferences
        if prefs is None : 
            self.report({'WARNING'}, "Could not load user preferences")
        else:
            prefs.json_fpath = fpt

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

''' Exports a palette collection to a JSON file + potential image files '''
class GPCOLORPICKER_OT_exportPalette(bpy.types.Operator):
    bl_idname = "scene.export_palette"
    bl_label = "Export Palette"    

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    @classmethod
    def poll(cls, context):
        return not context.scene.gpmatpalettes.is_empty()

    def execute(self, context): 
        fpt = self.filepath         

        data = export_palettes_content(self.filepath)
        
        with open(fpt, 'w') as outfile:
            json.dump(data, outfile, indent=4)
        
        self.report({'INFO'}, f"Palettes exported to {self.filepath}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

''' Removes a palette '''
class GPCOLORPICKER_OT_removePalette(bpy.types.Operator):
    bl_idname = "scene.remove_palette"
    bl_label = "Remove GP Palette"

    palette_index: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context): 
        gpmp = context.scene.gpmatpalettes
        npal = len(gpmp.palettes)
        if (self.palette_index < 0) or (self.palette_index >= npal):
            return {'CANCELLED'}

        gpmp.remove_palette_by_id(self.palette_index)

        return {'FINISHED'}

''' Reloads all palettes collection'''
class GPCOLORPICKER_OT_reloadAllPalettes(bpy.types.Operator):
    bl_idname = "scene.reload_all_palettes"
    bl_label = "Reload all GP Palettes"

    @classmethod
    def poll(cls, context):
        return not context.scene.gpmatpalettes.is_empty()

    def execute(self, context): 
        gpmp = context.scene.gpmatpalettes

        pnames = set(pal.name for pal in gpmp.palettes)
        fpaths = set(pal.source_path for pal in gpmp.palettes)
        
        for fpt in fpaths:
            parseJSONFile(fpt, palette_names=pnames, clear_existing=True)
        
        for pname in pnames:
            gpmp.palettes[pname].set_obsolete(False)

        return {'FINISHED'}

''' Reloads palette content from source file '''
class GPCOLORPICKER_OT_reloadPalette(bpy.types.Operator):
    bl_idname = "scene.reload_palette"
    bl_label = "Reload GP Palette"

    palette_index: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context): 
        gpmp = context.scene.gpmatpalettes
        npal = len(gpmp.palettes)
        if (self.palette_index < 0) or (self.palette_index >= npal):
            return {'CANCELLED'}

        pal = gpmp.palettes[self.palette_index]
        fpath = pal.source_path
        pname = pal.name

        parseJSONFile(fpath, palette_names=(pname), clear_existing=True)

        gpmp.palettes[pname].set_obsolete(False)

        return {'FINISHED'}

''' Toggle palette visibility '''
class GPCOLORPICKER_OT_togglePaletteVisibility(bpy.types.Operator):
    bl_idname = "scene.toggle_pal_visibility"
    bl_label= "Toggle Palette Visibility"

    palette_index: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context): 
        gpmp = context.scene.gpmatpalettes
        npal = len(gpmp.palettes)
        if (self.palette_index < 0) or (self.palette_index >= npal):
            return {'CANCELLED'}

        pal = gpmp.palettes[self.palette_index]
        pal.visible = not pal.visible

        if gpmp.active_index == self.palette_index:
            gpmp.next(1)

        return {'FINISHED'}

classes = [GPCOLORPICKER_OT_checkObsoletePalettes, \
            GPCOLORPICKER_OT_autoloadPalette, \
            GPCOLORPICKER_OT_importPalettes, \
            GPCOLORPICKER_OT_exportPalette, \
            GPCOLORPICKER_OT_removePalette, \
            GPCOLORPICKER_OT_reloadAllPalettes, \
            GPCOLORPICKER_OT_reloadPalette, \
            GPCOLORPICKER_OT_togglePaletteVisibility]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)