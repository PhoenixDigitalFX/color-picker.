from math import ceil

class GPCOLORPICKER_settings():
    def __init__(self, prefs = None):
        # Const values
        self.switch_key = 'TAB'
        self.active_color =  (0.01,0.01,0.01,1)
        self.mat_line_width = 5.
        self.mc_line_width = 1.
        self.pickline_width = 1.
        self.anti_aliasing_eps = 0.5
        self.mark_color = (0.5,0.5,0.5,1)

        # From user preferences
        if prefs:
            self.mat_from_active = (prefs.mat_mode == "from_active")
            self.mat_assign = prefs.assign_mat
            self.mc_fill_color = prefs.theme.pie_color
            self.mc_line_color = prefs.theme.line_color
            self.text_color = prefs.theme.text_color
            self.set_icon_scale(prefs.icon_scale)
        else:
            self.mat_from_active = True
            self.mat_assign = False
            self.mc_fill_color = (0.4,0.4,0.4,1.)
            self.mc_line_color = (0.96,0.96,0.96,1.)
            self.text_color = (0.,0.,0.,1.)
            self.set_icon_scale(250)

    def set_icon_scale(self,scale):
        self.icon_scale = scale
        self.mat_centers_radius = self.icon_scale/(2*(1.2))
        self.mc_outer_radius = 0.9*self.mat_centers_radius
        self.mc_inner_radius = 0.6*self.mc_outer_radius
        self.interaction_radius = 0.5*self.mc_outer_radius

        self.mat_radius = 0.1*self.mat_centers_radius

        self.selected_radius = 1.2*self.mat_radius
        self.text_size = ceil(0.05*self.icon_scale)
        self.tex_radius = self.mat_centers_radius-self.mat_radius
