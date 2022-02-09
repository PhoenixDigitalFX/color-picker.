import json
import bpy



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

def import_mat_from_json(json_fpath):    
    ifl = open(json_fpath, 'r')
    ctn = json.load(ifl)
    ifl.close()

    for name,mat in ctn.items():
        print(f"Material {name}")
        upload_material(name, mat)

