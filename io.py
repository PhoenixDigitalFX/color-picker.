import json, os, bpy

def upload_material(name, mdat):
    # Get material
    mat = bpy.data.materials.get(name)
    if mat is None:
        # create material
        mat = bpy.data.materials.new(name=name)
        bpy.data.materials.create_gpencil_data(mat)
    elif not mat.is_grease_pencil:
        print(f"Error: Material {name} exists and is not GP.")
        return False
        
    # Assign it to object
    ob = bpy.context.active_object
    if not name in ob.data.materials:
        ob.data.materials.append(mat)

    # Setting up material settings
    m = mat.grease_pencil
    count_ignored = 0
    for k,v in mdat.items():
        if not hasattr(m, k):
            print("Attr ignored ", k)
            count_ignored += 1 
            continue
        setattr(m, k, v)

    return True

def updatePalette(name_set):
    bpy.context.scene.gpmatpalette.clear()
    for name in name_set:
        gpmatit = bpy.context.scene.gpmatpalette.add()
        gpmatit.mat_name = name

### ----------------- Operator definition
class GPCOLORPICKER_OT_getJSONFile(bpy.types.Operator):
    bl_idname = "gpencil.file_load"
    bl_label = "Load File"    

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context): 
        fpt = self.filepath       

        if not os.path.isfile(fpt):
            print("Error : {} path not found".format(fpt))
            return 

        fnm = os.path.basename(fpt)
        ext = fnm.split(os.extsep)
        
        if (len(ext) < 2) or (ext[-1] != "json"):
            print("Error : {} is not a json file".format(fnm))
            return 
        
        ifl = open(fpt, 'r')
        ctn = json.load(ifl)
        ifl.close()

        for name,mat in ctn.items():
            print(f"Material {name}")
            upload_material(name, mat)

        updatePalette(ctn.keys())
        
        # Update data in user preferences
        prefs = context.preferences.addons[__package__].preferences
        if prefs is None : 
            self.report({'WARNING'}, "Could not load user preferences")
        else:
            prefs.json_fpath = fpt

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}