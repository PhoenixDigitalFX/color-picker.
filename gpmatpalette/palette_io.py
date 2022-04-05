# Import/Export Palette useful functions
import json, os, bpy, gpu, math
from . palette_maths import hex2rgba, rgba2hex
import datetime as dt

readonly_excepts = {'gpencil_settings','curves', 'curve_sensitivity', 'curve_strength', 'curve_jitter', 'curve_random_pressure', 'curve_random_strength', 'curve_random_uv', 'curve_random_hue', 'curve_random_saturation', 'curve_random_value'}
prop_exempt = {'unprojected_radius', 'grad_spacing', 'cloth_constraint_softbody_strength', 'cloth_damping', 'cloth_deform_type', 'cloth_force_falloff_type', 'cloth_mass', 'cloth_sim_falloff', 'cloth_sim_limit', 'cloth_simulation_area_type', 'surface_smooth_iterations'}

''' ---------- IMPORT PALETTES ---------- '''
''' Load an image in Blender database and pack it '''
def load_image(imname, path_prefix, check_existing=True):
    fullpath = os.path.join(path_prefix, imname)
    im = bpy.data.images.load(filepath=fullpath, check_existing=check_existing)
    if im:
        im.pack()
    return im

def load_curves(item, val):
    for curve_id, curve_dat in enumerate(val):
        if curve_id >= len(item.curves):
            print("ERROR : Loading too many curves")
            return

        curve = item.curves[curve_id]

        if len(curve_dat) < 2:
            print("ERROR : Trying to load a curve with less than 2 points")
            continue

        while(len(curve.points) > 2):
            curve.points.remove(curve.points[1])
        
        curve.points[0].location[0] = curve_dat[0][0]
        curve.points[0].location[1] = curve_dat[0][1]
        curve.points[1].location[0] = curve_dat[-1][0]
        curve.points[1].location[1] = curve_dat[-1][1]

        for point_id, point_dat in enumerate(curve_dat):
            if (point_id == 0) or (point_id == len(curve_dat)-1):
                continue
            curve.points.new(point_dat[0],point_dat[1])

def set_props(item, data, fdir, rec_level=0):   
    if rec_level > 6:
        return

    def set_default(item, pname, prop):
        ptype = prop.type
        if (ptype in {'INT','FLOAT', 'BOOLEAN'}) and prop.is_array:
            setattr(item,pname,prop.default_array)

        elif ptype in {'INT','FLOAT', 'BOOLEAN','STRING','ENUM'}:
            setattr(item,pname,prop.default)

        elif ptype == 'POINTER':
            pass
        
    def set_prop(item, pname, prop, val):
        ptype = prop.type

        if (ptype in {'INT','FLOAT', 'BOOLEAN'}) and prop.is_array:
            if (prop.subtype in {'COLOR', 'COLOR_GAMMA'}) \
                and (isinstance(val,str)):
                setattr(item,pname,hex2rgba(val))
                return
            setattr(item,pname,val)

        elif (ptype in {'ENUM'}) and (val == ""):
            pass
        #     set_default(item,pname,prop)
        
        elif (ptype == 'STRING') and pname.endswith('filepath'):
            abspath = os.path.join(fdir,val)
            setattr(item,pname,abspath)

        elif (ptype == 'BOOLEAN') and pname == 'use_material_pin':
            mat = item.material
            setattr(item,pname,val)
            item.material = mat

        elif ptype in {'INT','FLOAT', 'BOOLEAN','STRING','ENUM'}:
            setattr(item,pname,val)

        elif ptype == 'POINTER':
            if pname.endswith("image") \
                and (not val is None):
                im = load_image(val, fdir)
                setattr(item, pname, im)

            if pname.endswith("material") \
                and (not val is None):
                if val in bpy.data.materials:
                    setattr(item, pname, bpy.data.materials[val])
            else:
                set_props(getattr(item,pname), val, fdir, rec_level+1)
        elif ptype == 'COLLECTION':
            if pname == "curves":
                load_curves(item, val)
        else:
            print(f"Unknown property type {pname} : {ptype}")

    if item is None : 
        return

    props = item.bl_rna.properties
    for pname, prop in props.items():
        if (pname in prop_exempt) \
            or ((prop.is_readonly) and (not pname in readonly_excepts)):
            continue
        if not pname in data:
            set_default(item, pname, prop)
        else:
            set_prop(item, pname, prop, data[pname])

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

    set_props(mat.grease_pencil, mdat, fdir)

    mat.asset_generate_preview()

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
    
    set_props(bsh, bdat, fdir)

    return True

''' Reads and loads a palette content in Blender data'''
def upload_palette(pname, data, fpt, palette, old_mat_sys=False):
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
        if old_mat_sys and (not upload_material(name, mat_data, fdir)):
            continue
        
        # Material position in picker
        gpmatit = None        
        mat_fields = mat_data.keys()
        if "position" in mat_fields:
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
        if "origin" in mat_fields:
            gpmatit.set_origins([mat_data["origin"]])

        if "origins" in mat_fields:
            gpmatit.set_origins(mat_data["origins"])
        
        # Material Image
        if palette.image and ("image" in mat_fields):
            gpmatit.image = load_image(mat_data["image"], fdir)

        # Material layer
        if "layer" in mat_fields:
            gpmatit.layer = mat_data["layer"]

        # Material brushes
        if "brushes" in mat_fields:
            for bname in mat_data["brushes"].keys():
                gpmatit.add_brush_by_name(bname)   

        if "default_brush" in mat_fields:
            gpmatit.set_default_brush(mat_data["default_brush"])
    
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
    old_mat_sys = True
    if "__materials__" in data:
        old_mat_sys = False
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
        upload_palette(pname, pdata, json_file, palette, old_mat_sys)

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
def write_image(image, filedir, ext, subdir=""):
    import os
    imdir = os.path.join(filedir,subdir)
    if not os.path.isdir(imdir):
        os.mkdir(imdir)

    impath = os.path.join(imdir, image.name)
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
    
    return os.path.relpath(impath,start=filedir)

def get_props_dict(item, fdir, imdir, rec_level=0): 
    if rec_level > 6:
        return {}

    def equals_default(item, pname, prop):
        ptype = prop.type
        val = getattr(item,pname)
        if (ptype in {'INT','FLOAT', 'BOOLEAN'}) and prop.is_array:
            varr, darr = [v for v in val], [d for d in prop.default_array]
            is_equal = all([ (v==d) for v,d in zip(varr,darr) ])  
            # if not is_equal:
            #     print(f"PROP {pname} : val ({varr}), default ({darr})")
            return is_equal

        elif ptype in {'INT','FLOAT', 'BOOLEAN','STRING','ENUM'}:
            return (val == prop.default)

        elif ptype == 'POINTER':
            return val is None
            
        elif ptype == 'COLLECTION':
            if pname in {'nodes', 'links'}:
                return True

        return False

    def parse_prop(item, pname, pval):
        ptype = pval.type
        val = getattr(item,pname)
        if (ptype in {'INT','FLOAT', 'BOOLEAN'}) and pval.is_array:
            if pval.subtype in {'COLOR', 'COLOR_GAMMA'}:
                return rgba2hex(val)
            return [v for v in val]

        elif (ptype == 'STRING') and (pname.endswith("filepath")):
            # filepath to image that needs to be saved during export
            vpath = bpy.path.abspath(val)
            fname = bpy.path.basename(val)
            fpath = os.path.join(fdir,imdir,fname)
            from shutil import copy
            if vpath != fpath:
                copy(vpath,fpath)
            return os.path.relpath(fpath,start=fdir)

        # elif (ptype == 'ENUM') and (pname.endswith("icon")) and  (not val):
        #     print(f"Prop {pname} is empty (default is {pval.default})")
        #     return pval.default

        elif ptype in {'INT','FLOAT', 'BOOLEAN','STRING','ENUM'}:
            return val

        elif ptype == 'POINTER':
            if isinstance(val, bpy.types.Image):
                return write_image(val, fdir, ".png", imdir)
            if isinstance(val, bpy.types.Material):
                return val.name
            return get_props_dict(val, fdir, imdir,rec_level+1)

        elif ptype == 'COLLECTION':
            if (len(val) > 0) and isinstance(val[0], bpy.types.CurveMap):
                return [[ [x.location[0],x.location[1]] for x in curve.points] for curve in val]
            return [get_props_dict(v,fdir,imdir,rec_level+1) for v in val.values()]
        else:
            print(f"Unknown property type {pname} : {ptype}")
        return None
     
    props_dict = { k:parse_prop(item, k, v) for k,v in item.bl_rna.properties.items() \
                    if (not k in prop_exempt) and ((not v.is_readonly) or (k in readonly_excepts)) and (not equals_default(item, k, v))}
    return props_dict


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

    im_folder = ""
    tex_folder = "tex"

    # Palettes
    mat_names, brush_names = set(), set()
    for pname,pdata in gpmp.items():
        pal_dct[pname] = {}

        if pdata.image:
            impath = write_image(pdata.image, filedir, ext, im_folder)
            relpath = True
            pal_dct[pname]["image"] = {"path":impath, "relative":relpath} 

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
                mat_dct[mname]["image"] = write_image(mat.image, filedir, ext, im_folder)

            if mat.layer:
                mat_dct[mname]["layer"] = mat.layer

            bnames = set(mat.get_brushes_names())
            mat_dct[mname]["brushes"] = {b:{} for b in bnames}
            brush_names = brush_names.union(bnames)

            if mat.has_default_brush():
                mat_dct[mname]["default_brush"] = mat.default_brush.name
                
    # Materials
    pal_dct["__materials__"] = {}
    mat_dct = pal_dct["__materials__"]
    for mname in mat_names:
        mdat = bpy.data.materials[mname].grease_pencil
        mat_dct[mname] = get_props_dict(mdat,filedir,tex_folder)

    # Brushes
    pal_dct["__brushes__"] = {}
    bsh_dct = pal_dct["__brushes__"]
    for bname in brush_names:
        bdat = bpy.data.brushes[bname]
        bsh_dct[bname] = get_props_dict(bdat, filedir, tex_folder)
        # bsh_dct[bname]['size'] = bpy.data.brushes[bname].size
    return pal_dct
