# Import/Export Palette useful functions
import json, os, bpy, gpu, math
from . palette_maths import hex2rgba
import datetime as dt

''' ---------- IMPORT PALETTES ---------- '''

''' Load an image in Blender database and pack it '''
def load_image(imname, path_prefix, check_existing=True):
    fullpath = os.path.join(path_prefix, imname)
    im = bpy.data.images.load(filepath=fullpath, check_existing=check_existing)
    if im:
        im.pack()
    return im

''' Reads and loads a GP material in Blender database '''
def upload_material(name, mdat, fdir):
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
        # Color Attributes
        if (k.find("color") >= 0)  \
            and isinstance(v[0], str):
                setattr(m, k, hex2rgba(v[0],v[1]))
                continue
        # Image attributes
        if (k.find("image") >= 0) \
            and (not v is None):
            im = load_image(v, fdir)
            setattr(m, k, im)
            continue
        setattr(m, k, v)

    return True

''' Reads and loads a palette content in Blender data'''
def upload_palette(pname, data, fpt, palette):
    # Image
    is_relative_path = False
    fdir = ""
    if ("image" in data) and ("path" in data["image"]):
        im_data = data["image"]
        is_relative_path = ("relative" in im_data) and (im_data["relative"])
        if is_relative_path:
            fdir = os.path.dirname(fpt)
            palette.image = load_image(im_data["path"], fdir)

    for name,mat_data in data["materials"].items():
        # Material content
        if not upload_material(name, mat_data, fdir):
            continue
        
        # Material position in picker
        gpmatit = None        
        if "position" in mat_data.keys():
            def posdeg2rad(deg):
                rad = deg*math.pi/180.
                while rad < 0:
                    rad += 2*math.pi
                return rad
            angle = posdeg2rad(mat_data["position"])
            gpmatit = palette.set_material_by_angle(name, angle)
        else:
            gpmatit = palette.set_material(name)
        
        if not gpmatit:
            print("Could not import material ", name)
            continue
        
        # Material pickline
        if "origin" in mat_data.keys():
            gpmatit.set_origins([mat_data["origin"]])

        if "origins" in mat_data.keys():
            gpmatit.set_origins(mat_data["origins"])
        
        # Material Image
        if palette.image and ("image" in mat_data.keys()):
            gpmatit.image = load_image(mat_data["image"], fdir)

        # Material layer
        if "layer" in mat_data.keys():
            gpmatit.layer = mat_data["layer"]
    
    if palette.count() == 0:
        print(f"No materials in palette {pname} Aborting upload")
        return None

    palette.autocomp_positions()   
    palette.name = pname
    palette.source_path = fpt
    palette.is_obsolete = False

    return palette

''' Reads and loads a palette collection from a JSON file
    If palette_names is not empty, only the palettes whose name are in the set will be loaded
    If clear_existing is set to True, each imported palette will be cleared before reading
    Returns the names of the imported palettes
'''
def parseJSONFile(json_file, palette_names=set(), clear_existing = False):
    if not os.path.isfile(json_file):
        print("Error : {} path not found".format(json_file))
        return {'CANCELLED'}

    fnm = os.path.basename(json_file)
    ext = fnm.split(os.extsep)
    
    if (len(ext) < 2) or (ext[-1] != "json"):
        print("Error : {} is not a json file".format(fnm))
        return {'CANCELLED'}
    
    ifl = open(json_file, 'r')
    data = json.load(ifl)
    ifl.close()

    gpmatpalettes = bpy.context.scene.gpmatpalettes
    palettes = gpmatpalettes.palettes
    parsed_palettes = set()

    timestamp = ""
    if "__meta__" in data:
        timestamp  = data["__meta__"]["timestamp"]

    # Parse JSON
    for pname, pdata in data.items():
        # Fields starting with __ refers to internal data
        if pname.startswith("__"):
            continue

        if (len(palette_names) > 0) and (not pname in palette_names):
            continue

        if not pname in palettes:
            palette = palettes.add()
            ind = len(palettes)-1
        else:
            palette = palettes[pname]
            ind = palettes.find(pname)
            if clear_existing:
                palette.clear()
        
        palette.timestamp = timestamp
        upload_palette(pname, pdata, json_file, palette)

        if not palette:
            print("Nothing found in palette ", pname)
            continue
        gpmatpalettes.active_index = ind
        parsed_palettes.add(pname)
    return parsed_palettes

''' Get all JSON files in given directory 
    with a given maximal recursion level
    returns a set containing all the JSON file paths
'''
def getJSONfiles(dir, max_rec_level=2, level=0):
    files = set()
    if level == max_rec_level:
        return files
    for f in os.listdir(dir):
        fpath = os.path.join(dir, f)
        if os.path.isfile(fpath) and f.endswith((".json", ".JSON")):
            files.add(fpath)
        if os.path.isdir(fpath):
            files = files.union(getJSONfiles(fpath, max_rec_level, level+1))
    return files

''' ---------- EXPORT PALETTES ---------- '''

''' Writes an image from the Blender file database
    at the given file directory with the given extension format
    returns the full image file path
'''
def write_image(image, filedir, ext):
    import os.path as pth
    impath = pth.join(filedir, image.name)
    if (not impath.endswith(ext.upper())) \
        and (not impath.endswith(ext)):
        impath += ext   

    saved_format = image.file_format
    image.file_format = (ext[1:]).upper()     

    if not image.has_data:
        image.save_render(impath)     
    else:
        saved_fpath = image.filepath
        image.pack()
        image.filepath = impath
        image.save()
        image.filepath = saved_fpath

    image.file_format = saved_format  
    
    return impath

''' GP Material attributes taken into account for export '''
variables = ["alignment_mode", "alignment_rotation", "color","fill_color","fill_image","fill_style","flip","ghost", \
            "gradient_type","hide","lock","mix_color", "mix_factor", "mix_stroke_factor", "mode", "pass_index", "pixel_size", \
            "show_fill",  "show_stroke", "stroke_image", "stroke_style", "texture_angle", "texture_offset", "texture_scale", \
            "use_fill_holdout", "use_overlap_strokes", "use_stroke_holdout"]

''' Reads all material attributes from the Blender file data
    returns a dictionnary containing all the attributes
    side effect : writes image files if the material contains texture attributes
'''
def get_material_data(mat, fdir):
    def parse_attr(attr):
        dtp = [int, float, bool, str]
        if (attr is None) or any([isinstance(attr, t) for t in dtp]):
            return attr
        if (isinstance(attr, bpy.types.Image)):
            impath = write_image(attr, fdir, ".png")
            return os.path.basename(impath)
        return [attr[k] for k in range(len(attr))]
    mdat = { v:parse_attr(getattr(mat,v)) for v in variables }

    return mdat

''' Writes all palettes contained in a JSON file
    at the given file path
    side effect : writes image files if the palettes contain some 
'''
def export_palettes_content(filepath):
    gpmp = bpy.context.scene.gpmatpalettes.palettes
    pal_dct = {}
    ext = ".png"
    tmstp = str(dt.datetime.now())
    for pal in gpmp:
        pal.timestamp = tmstp

    pal_dct["__meta__"] = {}
    pal_dct["__meta__"]["timestamp"] = tmstp

    filedir= os.path.dirname(filepath)

    for pname,pdata in gpmp.items():
        pal_dct[pname] = {}
        dat_mats = {m.name:m.grease_pencil for m in bpy.data.materials if m.is_grease_pencil}

        if pdata.image:
            impath = write_image(pdata.image, filedir, ext)
            imname = os.path.basename(impath)
            relpath = True
            pal_dct[pname]["image"] = {"path":imname, "relative":relpath} 

        pal_dct[pname]["materials"] = {}
        mat_dct = pal_dct[pname]["materials"]
        for mname, mdata in pdata.materials.items(): 
            mat_dct[mname] = get_material_data(dat_mats[mname], filedir)

            mat_dct[mname]["position"] = mdata.get_angle(True)*180/math.pi

            if mdata.has_pickline():
                mat_dct[mname]["origins"] = mdata.get_origins()

            if mdata.image:
                mat_dct[mname]["image"] = os.path.basename(mdata.image.filepath)

            if mdata.layer:
                mat_dct[mname]["layer"] = mdata.layer
    return pal_dct
