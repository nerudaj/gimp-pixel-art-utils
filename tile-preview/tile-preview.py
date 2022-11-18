#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject

# GUI Helpers
def log(str):
    enabled = False
    if enabled:
        pdb.gimp_message(str)

def create_vbox(parent, grow_horizontally, spacing = 0):
    box = gtk.VBox()
    parent.pack_start(box, grow_horizontally, True, spacing)
    return box

def create_hbox(parent, grow_vertically, spacing = 0):
    box = gtk.HBox()
    parent.pack_start(box, grow_vertically, True, spacing)
    return box

def create_label(text, box, spacing = 0):
    label = gtk.Label(text)
    box.pack_start(label, True, True, spacing)
    return label

def create_button(label, box, spacing = 0):
    btn = gtk.Button()
    btn.set_label(label)
    box.pack_start(btn, True, True, spacing)
    return btn

def create_value_input(value, box, spacing = 0):
    input_entry = gtk.Entry()
    input_entry.set_text("{}".format(value))
    box.pack_start(input_entry, True, True, spacing)
    return input_entry

def create_combo(values, box, spacing = 0):
    combo = gtk.combo_box_new_text()

    for value in values:
        combo.append_text(value)

    box.pack_start(combo, True, True, spacing)
    return combo

class Dim:
    def __init__(self, width, height):
        self.width = width
        self.height = height

class RenderMode:
    BLOCK = "Block"
    FLOOR = "Floor"
    COLUMNS = "Columns"
    V_ADJ = "V. Adjacent"

    @staticmethod
    def get_string_annotations():
        return [RenderMode.BLOCK, RenderMode.FLOOR, RenderMode.COLUMNS, RenderMode.V_ADJ]

class GtkContext:
    def __init__(self):
        self.window = None
        self.display_box = None
        self.preview_box = None
        self.temp_img = None
        self.bottom_control_vbox = None
        self.layer_select_combos = [ None, None ]

class PreviewContext:
    def __init__(self):
        self.mode = RenderMode.BLOCK
        self.layer_names = [ "", "" ]
        self.zoom_level = 1.0
        self.image_ref = None
        self.gtk_window = None
        self.gtk_display_box = None
        self.gtk_preview_box = None
        self.temp_img = None
        self.gtk_ctx = GtkContext()
        self.skip_next_update = False

    def __del__(self):
        gimp.delete(self.temp_img)

    def __str__(self):
        return "PreviewContext(mode = {}, zoom = {}, names = {})".format(self.mode, self.zoom_level, self.layer_names)

    def __repr__(self):
        return self.__str__()

class RenderStrategyInterface:
    def copy_layer_to(self, source, destination, x, y):
        def make_layer_visible_with_alpha(layer):
            if len(layer.children) == 0: # Cannot add alpha for layer group
                pdb.gimp_layer_add_alpha(layer)
            pdb.gimp_drawable_set_visible(layer, True)

        temp_layer = pdb.gimp_layer_new_from_drawable(source, destination)
        make_layer_visible_with_alpha(temp_layer)
        destination.insert_layer(temp_layer)
        temp_layer.translate(x, y)

    def construct_preview(self, target, width, height, layer1, layer2):
        pass

    def get_image_dim(self, width, height, second_layer_is_valid):
        pass

class RenderStrategyBlock(RenderStrategyInterface):
    def construct_preview(self, target, width, height, layer1, layer2):
        log("construct_preview")
        for y in range(0, 3):
            for x in range(0, 3):
                use_layer2 = (y != 1 or x != 1) and layer2
                self.copy_layer_to(
                    layer2 if use_layer2 else layer1,
                    target,
                    x * width,
                    y * height)

    def get_image_dim(self, width, height, second_layer_is_valid):
        return Dim(
            int(width * 3.0),
            int(height * 3.0))

class RenderStrategyFloor(RenderStrategyInterface):
    def construct_preview(self, target, width, height, layer1, layer2):
        for x in range(0, 3):
            use_layer2 = (x != 1) and layer2
            self.copy_layer_to(
                layer2 if use_layer2 else layer1,
                target,
                x * width, 0)

    def get_image_dim(self, width, height, second_layer_is_valid):
        return Dim(
            int(width * 3.0),
            int(height))

class RenderStrategyVadj(RenderStrategyInterface):
    def construct_preview(self, target, width, height, layer1, layer2):
        self.copy_layer_to(
            layer1,
            target,
            0, 0)
        if layer2:
            self.copy_layer_to(
                layer2,
                target,
                0, height)

    def get_image_dim(self, width, height, second_layer_is_valid):
        return Dim(
            int(width),
            int(height * 2.0))

class RenderStrategyColumns(RenderStrategyInterface):
    def construct_preview(self, target, width, height, layer1, layer2):
        for y in range(0, 3):
            for x in range(0, 3):
                use_layer2 = (x != 1) and layer2
                self.copy_layer_to(
                    layer2 if use_layer2 else layer1,
                    target,
                    x * width,
                    y * height)

    def get_image_dim(self, width, height, second_layer_is_valid):
        return Dim(
            int(width * (3.0 if second_layer_is_valid else 1.0)),
            int(height * 3.0))

class RenderStrategyFactory():
    @staticmethod
    def get_strategy(mode):
        if mode == RenderMode.BLOCK:
            return RenderStrategyBlock()
        elif mode == RenderMode.V_ADJ:
            return RenderStrategyVadj()
        elif mode == RenderMode.FLOOR:
            return RenderStrategyFloor()
        elif mode == RenderMode.COLUMNS:
            return RenderStrategyColumns()
        else:
            return RenderStrategyInterface()

def get_preview_image(image_type, width, height, zoom, mode, layer1, layer2, gtk_ctx, render_strategy):
    log("get_preview_image({}, {}, {}, {}, {}, {})".format(width, height, zoom, mode, layer1, layer2))

    # Compute base image size
    new_image_dim = render_strategy.get_image_dim(width, height, layer2)

    # Create temp image that will accomodate new layers
    if gtk_ctx.temp_img:
        gimp.delete(gtk_ctx.temp_img)

    gtk_ctx.temp_img = pdb.gimp_image_new(
        new_image_dim.width,
        new_image_dim.height,
        image_type)
    gtk_ctx.temp_img.disable_undo()

    render_strategy.construct_preview(gtk_ctx.temp_img, width, height, layer1, layer2)

    # Disable interpolation and zoom the image by scaling
    pdb.gimp_context_set_interpolation(0)
    final_layer = gtk_ctx.temp_img.flatten()
    pdb.gimp_layer_scale(
        final_layer,
        new_image_dim.width * zoom,
        new_image_dim.height * zoom,
        False)

    return final_layer

def update_preview(widget, preview_context):
    log("update_preview({})".format(preview_context))

    def get_layer_from_image(image, name):
        for layer in image.layers:
            if layer.name == name:
                return layer
        return None

    def redraw_preview(gtk_ctx, drawable):
        if gtk_ctx.preview_box:
            gtk_ctx.display_box.remove(gtk_ctx.preview_box)

        gtk_ctx.preview_box = gimpui.DrawablePreview(drawable)
        gtk_ctx.display_box.pack_start(gtk_ctx.preview_box, True, True, 0)

        gtk_ctx.window.show_all()

    if preview_context.skip_next_update:
        preview_context.skip_next_update = False
        return

    layer1 = get_layer_from_image(preview_context.image_ref, preview_context.layer_names[0])
    layer2 = get_layer_from_image(preview_context.image_ref, preview_context.layer_names[1])

    if not layer1 and not layer2:
        return

    layer_to_draw = get_preview_image(
        preview_context.image_ref.base_type,
        preview_context.image_ref.width,
        preview_context.image_ref.width,
        preview_context.zoom_level,
        preview_context.mode,
        layer1,
        layer2,
        preview_context.gtk_ctx,
        RenderStrategyFactory.get_strategy(preview_context.mode))

    redraw_preview(preview_context.gtk_ctx, layer_to_draw)

def create_layer_select_combo(preview_context, index, name_to_select=None):
    log("create_layer_select_combo(index = {})".format(index))

    def get_image_layer_names(image, add_empty=False):
        layer_names = []

        if add_empty:
            layer_names.append("- none -")

        for layer in image.layers:
            layer_names.append(layer.name)
        return layer_names

    def update_layer_names(combo, preview_context, index):
        log("update_layer_names({}, {})".format(index, combo.get_active_text()))
        preview_context.layer_names[index] = combo.get_active_text()
        update_preview(None, preview_context)

    def try_to_select_option(option_to_select, option_list, combo):
        if not option_to_select:
            return False

        for index, option in enumerate(option_list):
            if option == option_to_select:
                combo.set_active(index)
                return True
        return False

    gtk_ctx = preview_context.gtk_ctx
    layer_names = get_image_layer_names(preview_context.image_ref, add_empty=index)

    combo = create_combo(
        layer_names,
        gtk_ctx.bottom_control_vbox)
    combo.connect(
        "changed",
        update_layer_names,
        preview_context,
        index)

    if not try_to_select_option(name_to_select, layer_names, combo):
        combo.set_active(0)

    gtk_ctx.layer_select_combos[index] = combo

def build_gui(preview_context):
    log("build_gui({})".format(preview_context))

    def zoom_in(widget, preview_context):
        log("zoom_in")
        preview_context.zoom_level *= 2.0
        update_preview(None, preview_context)

    def zoom_out(widget, preview_context):
        log("zoom_out")
        preview_context.zoom_level /= 2.0
        update_preview(None, preview_context)

    def change_display_mode(widget, preview_context):
        log("change_display_mode({})".format(preview_context))
        preview_context.mode = widget.get_active_text()
        update_preview(None, preview_context)

    def refresh_combos(widget, preview_context, count):
        log("refresh_combos({}, {})".format(preview_context, count))

        names_to_select = ["", ""]
        for index in range(count):
            names_to_select[index] = preview_context.gtk_ctx.layer_select_combos[index].get_active_text()
            preview_context.gtk_ctx.bottom_control_vbox.remove(
                preview_context.gtk_ctx.layer_select_combos[index])

        preview_context.skip_next_update = True
        for index in range(count):
            create_layer_select_combo(preview_context, index, name_to_select=names_to_select[index])

    # Window
    preview_context.gtk_ctx.window = gtk.Window()
    preview_context.gtk_ctx.window.set_title("Tile Preview")
    preview_context.gtk_ctx.window.connect('destroy',  close_preview_window)

    window_box = gtk.VBox()
    preview_context.gtk_ctx.window.add(window_box)
    preview_context.gtk_ctx.window.set_keep_above(True)

    ## Upper box model
    upper_wrap_hbox = create_hbox(window_box, False)
    upper_label_vbox = create_vbox(upper_wrap_hbox, True)
    upper_control_vbox = create_vbox(upper_wrap_hbox, True)

    ### Zoom controls
    create_label("Zoom", upper_label_vbox)
    
    zoom_btn_box = create_hbox(upper_control_vbox, False)
    unzoom_btn = create_button("-", zoom_btn_box)
    unzoom_btn.connect("clicked", zoom_out, preview_context)
    zoom_btn = create_button("+", zoom_btn_box)
    zoom_btn.connect("clicked", zoom_in, preview_context)

    ## Display box
    preview_context.gtk_ctx.display_box = create_hbox(window_box, True)

    ## Bottom box model
    bottom_wrap_hbox = create_hbox(window_box, False)
    bottom_label_vbox = create_vbox(bottom_wrap_hbox, True)
    preview_context.gtk_ctx.bottom_control_vbox = create_vbox(bottom_wrap_hbox, True)

    ### Mode select
    create_label("Preview mode", bottom_label_vbox)
    combo = create_combo(RenderMode.get_string_annotations(), preview_context.gtk_ctx.bottom_control_vbox)
    combo.connect(
        "changed",
        change_display_mode,
        preview_context)

    preview_context.skip_next_update = True
    combo.set_active(0)

    ### Layers selection
    labels = [ "Primary layer", "Secondary layer" ]
    for label in labels:
        create_label(label, bottom_label_vbox)

    preview_context.skip_next_update = True
    for index in range(len(labels)):
        create_layer_select_combo(preview_context, index)

    ## Refresh button
    refresh_btn_hbox = create_hbox(window_box, False)
    refresh_btn = create_button("Refresh", refresh_btn_hbox)
    refresh_btn.connect(
        "clicked",
        refresh_combos,
        preview_context,
        len(labels))

    preview_context.gtk_ctx.window.show_all()

def close_preview_window(ret):
    log("quitting Animation preview plugin")
    gtk.main_quit()

def run_tile_preview_plugin_function(_image, _drawable):
    log("Running Tile Preview plugin")

    preview_context = PreviewContext()
    preview_context.image_ref = _image
    preview_context.zoom_level = 64.0 / _image.width

    build_gui(preview_context)
    gtk.main()

######################
##### Run script #####
######################

register(
          "run_tile_preview_plugin_function",
          "Previews how layer would look like when tiled",
          "Previews how layer would look like when tiled",
          "doomista",
          "Apache 2 license",
          "2022",
          "Tile Preview",
          "*",
          [
              (PF_IMAGE, "image", "Input image", None),
              (PF_DRAWABLE, "drawable", "Input drawable", None),
          ],
          [],
          run_tile_preview_plugin_function, menu="<Image>/Tools/Pixel Art")
main()

