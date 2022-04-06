# Appearance settings for the picker
from math import ceil

class GPCOLORPICKER_settings():
    def __init__(self, addon_prefs = None, theme = None):
        # Const values
        self.switch_key = 'TAB'
        self.mat_line_width = 5.
        self.mc_line_width = 1.
        self.pickline_width = 1.
        self.anti_aliasing_eps = 0.5
        self.mark_color = (0.5,0.5,0.5,1)
        self.selection_ratio = 1.2

        # From user preferences
        if addon_prefs:
            self.mat_from_active = (addon_prefs.mat_mode == "from_active")
            self.mat_assign = addon_prefs.assign_mat
            self.mc_fill_color = addon_prefs.theme.pie_color
            self.mc_line_color = addon_prefs.theme.line_color
            self.text_color = addon_prefs.theme.text_color
            self.set_icon_scale(addon_prefs.icon_scale)
            self.use_default_brushes = addon_prefs.use_default_brushes
        else:
            self.mat_from_active = True
            self.mat_assign = False
            self.mc_fill_color = (0.4,0.4,0.4,1.)
            self.mc_line_color = (0.96,0.96,0.96,1.)
            self.text_color = (0.,0.,0.,1.)
            self.set_icon_scale(250)
            self.use_default_brushes = True

        if theme:
            self.active_color = theme.view_3d.object_active
            self.active_color = [c for c in self.active_color] + [1.]

            self.select_color = theme.view_3d.object_selected
            self.select_color = [c for c in self.select_color] + [1.]
        
        else:
            self.active_color = (0.4,0.4,0.4,1.)
            self.select_color = (0.4,0.4,0.4,1.)

    def set_icon_scale(self,scale):
        self.icon_scale = scale
        self.mat_centers_radius = self.icon_scale/(2*(1.2))
        self.mc_outer_radius = 0.9*self.mat_centers_radius
        self.mc_inner_radius = 0.6*self.mc_outer_radius
        self.interaction_radius = 0.5*self.mc_outer_radius

        self.mat_radius = 0.1*self.mat_centers_radius
        self.brush_radius = 0.8*self.mat_radius
        self.brush_interrad = 0.5*self.brush_radius
        self.overall_brush_radius = self.mat_centers_radius + 0.5*self.brush_interrad
        # offset due to mat selection ratio
        self.overall_brush_radius += -(1.-2*self.selection_ratio)*self.mat_radius 

        self.text_size = ceil(0.04*self.icon_scale)
        self.tex_radius = self.mat_centers_radius-self.mat_radius
