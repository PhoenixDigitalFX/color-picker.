import bpy

def register():
    from . palette_props import register as register_props
    register_props()

    from . palette_ops import register as register_ops
    register_ops()

    from . palette_panel import register as register_panel
    register_panel()

def unregister():        
    from . palette_props import unregister as unregister_props
    unregister_props()

    from . palette_ops import unregister as unregister_ops
    unregister_ops()

    from . palette_panel import unregister as unregister_panel
    unregister_panel()