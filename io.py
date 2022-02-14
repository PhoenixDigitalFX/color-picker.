import json, os, bpy, gpu, math

def upload_image(impath, is_relative=True, fpath=""):
    fullpath = impath
    if is_relative:
        fullpath = os.path.dirname(fpath) + os.path.sep + fullpath
    if not os.path.isfile(fullpath):
        print("Error : File {} not found".format(fullpath))
        return ""
    im = bpy.data.images.load(filepath=fullpath, check_existing=False)
    return im.name

def srgb_to_linearrgb(c):
    '''from https://blender.stackexchange.com/a/158902/4979'''
    if   c < 0:       return 0
    elif c < 0.04045: return c/12.92
    else:             return ((c+0.055)/1.055)**2.4

def hex2rgba(hex, alpha):
    '''from https://blender.stackexchange.com/a/158902/4979'''
    h = hex
    if type(h) is str:
        h = int(h, 16)
    r = (h & 0xff0000) >> 16
    g = (h & 0x00ff00) >> 8
    b = (h & 0x0000ff)
    return tuple([srgb_to_linearrgb(c/0xff) for c in (r,g,b)] + [alpha])

def upload_material(name, mdat):
    # Get material
    mat = bpy.data.materials.get(name)
    if mat is None:
        # create material
        mat = bpy.data.materials.new(name=name)
        mat.use_fake_user = True
        bpy.data.materials.create_gpencil_data(mat)
    elif not mat.is_grease_pencil:
        print(f"Error: Material {name} exists and is not GP.")
        return False

    # Setting up material settings
    m = mat.grease_pencil
    for k,v in mdat.items():
        if not hasattr(m, k):
            continue
        if (k.find("color") >= 0)  \
            and isinstance(v[0], str):
                setattr(m, k, hex2rgba(v[0],v[1]))
                continue
        setattr(m, k, v)

    return True


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
            return {'CANCELLED'}

        fnm = os.path.basename(fpt)
        ext = fnm.split(os.extsep)
        
        if (len(ext) < 2) or (ext[-1] != "json"):
            print("Error : {} is not a json file".format(fnm))
            return {'CANCELLED'}
        
        ifl = open(fpt, 'r')
        data = json.load(ifl)
        ifl.close()
        
        if not "materials" in data :
            print("Error : {} does not contain any material".format(fnm))
            return {'CANCELLED'}

        gpmatpalette = bpy.context.scene.gpmatpalette
        gpmatpalette.clear()
        # Parse JSON
        is_relative_path = False
        if ("image" in data) and ("path" in data["image"]):
            im_data = data["image"]
            is_relative_path = ("relative" in im_data) and (im_data["relative"])
            gpmatpalette.image = upload_image(im_data["path"], is_relative_path, fpt)
        hasImage = not (gpmatpalette.image == "")

        for name,mat_data in data["materials"].items():
            if not upload_material(name, mat_data):
                continue

            gpmatit = gpmatpalette.materials.add()
            gpmatit.mat_name = name

            if "position" in mat_data.keys():
                def posdeg2rad(deg):
                    rad = deg*math.pi/180.
                    while rad < 0:
                        rad += 2*math.pi
                    return rad
                gpmatit.custom_angle = posdeg2rad(mat_data["position"])
            
            if hasImage and ("image" in mat_data.keys()):
                gpmatit.image = upload_image(mat_data["image"], is_relative_path, fpt)

            if "layer" in mat_data.keys():
                gpmatit.layer = mat_data["layer"]

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