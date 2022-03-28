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
bsh_gp_attr = ["active_smooth_factor","angle","angle_factor","aspect","brush_draw_mode","caps_type",\
    # "curve_jitter","curve_random_hue","curve_random_pressure","curve_random_saturation",\
    # "curve_random_strength","curve_random_uv","curve_random_value","curve_sensitivity","curve_strength",\
    "dilate","direction","eraser_mode","eraser_strength_factor","eraser_thickness_factor",\
    "extend_stroke_factor","fill_direction","fill_draw_mode","fill_factor","fill_layer_mode",\
    "fill_leak","fill_simplify_level","fill_threshold","gpencil_paint_icon","gpencil_sculpt_icon",\
    "gpencil_vertex_icon","gpencil_weight_icon","hardness","input_samples","material","pen_jitter",\
    "pen_smooth_factor","pen_smooth_steps","pen_strength","pen_subdivision_steps","pin_draw_mode",\
    "random_hue_factor","random_pressure","random_saturation_factor","random_strength","random_value_factor",\
    "show_fill","show_fill_boundary","show_fill_extend","show_lasso","simplify_factor","use_default_eraser",\
    "use_edit_position","use_edit_strength","use_edit_thickness","use_edit_uv","use_fill_limit","use_jitter_pressure",\
    "use_material_pin","use_occlude_eraser","use_pressure","use_random_press_hue","use_random_press_radius",\
    "use_random_press_sat","use_random_press_strength","use_random_press_uv","use_random_press_val",\
    "use_settings_postprocess","use_settings_random","use_settings_stabilizer","use_strength_pressure",\
    "use_stroke_random_hue","use_stroke_random_radius","use_stroke_random_sat","use_stroke_random_strength",\
    "use_stroke_random_uv","use_stroke_random_val","use_trim","uv_random","vertex_color_factor","vertex_mode"]

bsh_attr = ["area_radius_factor","auto_smooth_factor","automasking_boundary_edges_propagation_steps",\
    "blend","blur_kernel_radius","blur_mode","boundary_deform_type","boundary_falloff_type","boundary_offset",\
    "clone_alpha","clone_image","clone_offset","color","color_type","crease_pinch_factor","cursor_color_add",\
    "cursor_color_subtract","cursor_overlay_alpha","curve_preset","dash_ratio","dash_samples","deform_target",\
    "density","direction","disconnected_distance_max","elastic_deform_type","elastic_deform_volume_preservation",\
    "falloff_angle","falloff_shape","fill_threshold","flow","gpencil_sculpt_tool","gpencil_tool",\
    "gpencil_vertex_tool","gpencil_weight_tool","grad_spacing","gradient_fill_mode","gradient_stroke_mode",\
    "hardness","height","icon_filepath","image_tool","invert_density_pressure","invert_flow_pressure",\
    "invert_hardness_pressure","invert_to_scrape_fill","invert_wet_mix_pressure","invert_wet_persistence_pressure",\
    "jitter","jitter_absolute","jitter_unit","mask_overlay_alpha","mask_stencil_dimension","mask_stencil_pos",\
    "mask_tool","multiplane_scrape_angle","normal_radius_factor","normal_weight","plane_offset","plane_trim",\
    "pose_deform_type","pose_ik_segments","pose_offset","pose_origin_type","pose_smooth_iterations","rake_factor",\
    "rate","sculpt_plane","sculpt_tool","secondary_color","sharp_threshold","show_multiplane_scrape_planes_preview",\
    "size","slide_deform_type","smear_deform_type","smooth_deform_type","smooth_stroke_factor","smooth_stroke_radius",\
    "snake_hook_deform_type","spacing","stencil_dimension","stencil_pos","strength","stroke_method",\
    "surface_smooth_current_vertex","surface_smooth_iterations","surface_smooth_shape_preservation","texture_overlay_alpha",\
    "texture_sample_bias","tilt_strength_factor","tip_roundness","tip_scale_x","topology_rake_factor","unprojected_radius",\
    "use_accumulate","use_adaptive_space","use_airbrush","use_alpha","use_anchor","use_automasking_boundary_edges",\
    "use_automasking_boundary_face_sets","use_automasking_face_sets","use_automasking_topology","use_cloth_collision",\
    "use_cloth_pin_simulation_boundary","use_connected_only","use_cursor_overlay","use_cursor_overlay_override","use_curve",\
    "use_custom_icon","use_density_pressure","use_edge_to_edge","use_fake_user","use_flow_pressure","use_frontface",\
    "use_frontface_falloff","use_grab_active_vertex","use_grab_silhouette","use_hardness_pressure",\
    "use_inverse_smooth_pressure","use_line","use_locked_size","use_multiplane_scrape_dynamic","use_offset_pressure",\
    "use_original_normal","use_original_plane","use_paint_antialiasing","use_paint_grease_pencil","use_paint_image",\
    "use_paint_sculpt","use_paint_uv_sculpt","use_paint_vertex","use_paint_weight","use_persistent","use_plane_trim",\
    "use_pose_ik_anchored","use_pose_lock_rotation","use_pressure_area_radius","use_pressure_jitter","use_pressure_masking",\
    "use_pressure_size","use_pressure_spacing","use_pressure_strength","use_primary_overlay","use_primary_overlay_override",\
    "use_restore_mesh","use_scene_spacing","use_secondary_overlay","use_secondary_overlay_override","use_smooth_stroke",\
    "use_space","use_space_attenuation","use_vertex_grease_pencil","use_wet_mix_pressure","use_wet_persistence_pressure",\
    "uv_sculpt_tool","vertex_tool","weight","weight_tool","wet_mix","wet_paint_radius_factor","wet_persistence"]

''' Reads all brush attributes from the Blender file data
    returns a dictionnary containing all the attributes
    side effect : writes image files if the brush contains texture attributes
'''
def get_brush_data(bsh, fdir):
    default_bsh = bpy.data.brushes["__DefaultBrush__"]
    def parse_attr(attr):
        dtp = [int, float, bool, str]
        if (attr is None) or any([isinstance(attr, t) for t in dtp]):
            return attr
        if (isinstance(attr, bpy.types.Image)):
            impath = write_image(attr, fdir, ".png")
            return os.path.basename(impath)
        if (isinstance(attr, bpy.types.CurveMapping)):
            print("Curve output not yet implemented")
            return None
        return [attr[k] for k in range(len(attr))]

    bdat = { v:parse_attr(getattr(bsh,v)) for v in bsh_attr \
            if (getattr(bsh,v) != getattr(default_bsh, v))}

    bshgp = bsh.gpencil_settings
    bdat["gpencil_settings"] = { v:parse_attr(getattr(bshgp,v)) for v in bsh_gp_attr \
                    if (getattr(bshgp,v) != getattr(default_bsh.gpencil_settings, v))}
    bdat["gpencil_settings"] = { k:v for k,v in bdat["gpencil_settings"].items() \
                    if not (isinstance(v,str) and (len(v) == 0)) }

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
