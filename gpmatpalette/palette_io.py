# Import/Export Palette useful functions
import json, os, bpy, gpu, math
from . palette_maths import hex2rgba, rgba2hex
import datetime as dt

''' ---------- IMPORT PALETTES ---------- '''
''' Load an image in Blender database and pack it '''
def load_image(imname, path_prefix, check_existing=True):
    fullpath = os.path.join(path_prefix, imname)
    im = bpy.data.images.load(filepath=fullpath, check_existing=check_existing)
    if im:
        im.pack()
    return im

def parse_attr(name_attr, val_attr, item, fdir):
    if not hasattr(item, name_attr):
        return False

    # Color Attributes
    if name_attr.endswith("color")  \
        and isinstance(val_attr[0], str):
            setattr(item, name_attr, hex2rgba(val_attr[0],val_attr[1]))
            return True
    # Image attributes
    if (name_attr.find("image") >= 0) \
        and (not val_attr is None):
        im = load_image(val_attr, fdir)
        setattr(item, name_attr, im)
        return True
    # Curve attributes
    if (name_attr.find("curve") >= 0):
        return False
    setattr(item, name_attr, val_attr)
    return True

''' Reads and loads a GP material in Blender database '''
def upload_material(name, mdat, fdir):
    # Get material
    mat = bpy.data.materials.get(name)
    if mat is None:
        # create material
        mat = bpy.data.materials.new(name=name)
        mat.use_fake_user = True
        bpy.data.materials.create_gpencil_data(mat)
        mat.asset_generate_preview()
    elif not mat.is_grease_pencil:
        print(f"Error: Material {name} exists and is not GP.")
        return False

    # Setting up material settings
    m = mat.grease_pencil
    for k,v in mdat.items():
        parse_attr(k, v, m, fdir)

    return True

''' Reads and loads a GP brush in Blender database '''
def upload_brush(name, bdat, fdir):
    # Get brush
    bsh = bpy.data.brushes.get(name)
    if bsh is None:
        # create brush
        bsh = bpy.data.brushes.new(name=name, mode='PAINT_GPENCIL')
        bpy.data.brushes.create_gpencil_data(bsh)
        bsh.use_fake_user = True

    # Setting up brush settings
    gpstg = "gpencil_settings"
    for k,v in bdat.items():
        if k == gpstg:
            continue
        parse_attr(k, v, bsh, fdir)
    
    if not gpstg in bdat:
        return

    for k,v in bdat[gpstg].items():
        parse_attr(k, v, bsh.gpencil_settings, fdir)

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
        # [obsolete] Material content
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
    fdir = os.path.dirname(json_file)

    timestamp = ""
    if "__meta__" in data:
        timestamp  = data["__meta__"]["timestamp"]

    # Parse JSON
    if "__materials__" in data:
        mat_dct = data["__materials__"]
        for mname, mdat in mat_dct.items():
            upload_material(mname, mdat, fdir)

    if "__brushes__" in data:
        bsh_dct = data["__brushes__"]
        for bname, bdat in bsh_dct.items():
            upload_brush(bname, bdat, fdir)

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
mat_attr = ["alignment_mode", "alignment_rotation", "color","fill_color","fill_image","fill_style","flip","ghost", \
            "gradient_type","hide","lock","mix_color", "mix_factor", "mix_stroke_factor", "mode", "pass_index", "pixel_size", \
            "show_fill",  "show_stroke", "stroke_image", "stroke_style", "texture_angle", "texture_offset", "texture_scale", \
            "use_fill_holdout", "use_overlap_strokes", "use_stroke_holdout"]

''' Reads all material attributes from the Blender file data
    returns a dictionnary containing all the attributes
    side effect : writes image files if the material contains texture attributes
'''
def get_material_data(mat, fdir):
    default_mat = bpy.data.materials["__DefaultMat__"].grease_pencil
    def parse_attr(attr):
        dtp = [int, float, bool, str]
        if (attr is None) or any([isinstance(attr, t) for t in dtp]):
            return attr
        if (isinstance(attr, bpy.types.Image)):
            impath = write_image(attr, fdir, ".png")
            return os.path.basename(impath)
        return [attr[k] for k in range(len(attr))]
    mdat = { v:parse_attr(getattr(mat,v)) for v in mat_attr  \
            if (getattr(mat,v) != getattr(default_mat, v))}

    return mdat

''' GP Brushes attributes taken into account for export '''   
def get_props_dict(item):    
    def equals_default(item, pname, prop):
        ptype = prop.type
        val = getattr(item,pname)
        if (ptype in {'INT','FLOAT', 'BOOLEAN'}) and prop.is_array:
            return all([ (v==d) for v,d in zip(val,prop.default_array) ])  

        elif ptype in {'INT','FLOAT', 'BOOLEAN','STRING','ENUM'}:
            return (val == prop.default)

        elif ptype == 'POINTER':
            pass

        return True

    def parse_prop(item, pname, pval):
        ptype = pval.type
        if (ptype in {'INT','FLOAT', 'BOOLEAN'}) and pval.is_array:
            arr = getattr(item,pname)
            if pval.subtype in {'COLOR', 'COLOR_GAMMA'}:
                return rgba2hex(arr)
            return [v for v in arr]

        elif ptype in {'INT','FLOAT', 'BOOLEAN','STRING','ENUM'}:
            return getattr(item,pname)

        elif ptype == 'POINTER':
            pass
        
        else:
            print(f"Unknown property type {pname} : {ptype}")
        return None
     
    return { k:parse_prop(item, k, v) for k,v in item.bl_rna.properties.items() if not equals_default(item, k, v)}

''' Reads all brush attributes from the Blender file data
    returns a dictionnary containing all the attributes
    side effect : writes image files if the brush contains texture attributes
'''
def get_brush_data(bsh, fdir):
    bdat = get_props_dict(bsh)
    bdat["gpencil_settings"] = get_props_dict(bsh.gpencil_settings)
    return bdat

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

    # Palettes
    mat_names, brush_names = set(), set()
    for pname,pdata in gpmp.items():
        pal_dct[pname] = {}

        if pdata.image:
            impath = write_image(pdata.image, filedir, ext)
            imname = os.path.basename(impath)
            relpath = True
            pal_dct[pname]["image"] = {"path":imname, "relative":relpath} 

        pal_dct[pname]["materials"] = {}
        mat_dct = pal_dct[pname]["materials"]    
        
        for mat in pdata.materials: 
            mname = mat.get_name()
            mat_names.add(mname)
            mat_dct[mname] = {}
            mat_dct[mname]["position"] = mat.get_angle(True)*180/math.pi

            if mat.has_pickline():
                mat_dct[mname]["origins"] = mat.get_origins(np_arr = False)

            if mat.image:
                mat_dct[mname]["image"] = os.path.basename(mat.image.filepath)

            if mat.layer:
                mat_dct[mname]["layer"] = mat.layer

            bnames = set(mat.get_brushes_names())
            mat_dct[mname]["brushes"] = {b:{} for b in bnames}
            brush_names = brush_names.union(bnames)
                
    # Materials
    default_mat = bpy.data.materials.new(name="__DefaultMat__")
    bpy.data.materials.create_gpencil_data(default_mat)
    pal_dct["__materials__"] = {}
    mat_dct = pal_dct["__materials__"]
    for mname in mat_names:
        mdat = bpy.data.materials[mname].grease_pencil
        mat_dct[mname] = get_material_data(mdat, filedir)
    bpy.data.materials.remove(default_mat)

    # Brushes
    default_bsh = bpy.data.brushes.new(name="__DefaultBrush__", mode='PAINT_GPENCIL')
    bpy.data.brushes.create_gpencil_data(default_bsh)
    pal_dct["__brushes__"] = {}
    bsh_dct = pal_dct["__brushes__"]
    for bname in brush_names:
        bdat = bpy.data.brushes[bname]
        bsh_dct[bname] = get_brush_data(bdat, filedir)
    bpy.data.brushes.remove(default_bsh)

    return pal_dct
