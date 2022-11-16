#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject

# GUI Helpers
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
    DEFAULT = "Block"
    TWO_ROWS = "Rows"
    TWO_COLS = "Columns"

    @staticmethod
    def get_string_annotations():
        return [RenderMode.DEFAULT, RenderMode.TWO_ROWS]

class PreviewContext:
    def __init__(self):
        self.mode = RenderMode.DEFAULT
        self.layer_names = [ "", "" ]
        self.zoom_level = 1.0
        self.image_ref = None
        self.gtk_window = None
        self.gtk_display_box = None
        self.gtk_preview_box = None
        self.temp_img = None

    def __del__(self):
        gimp.delete(self.temp_img)

    def __str__(self):
        return "PreviewContext(mode = {}, zoom = {}, names = {})".format(self.mode, self.zoom_level, self.layer_names)

    def __repr__(self):
        return self.__str__()

def update_preview_internal(image_type, width, height, zoom, mode, layer1, layer2, preview_context):
    pdb.gimp_message("update_preview_internal({}, {}, {}, {}, {}, {})".format(width, height, zoom, mode, layer1, layer2))

    def get_image_dim_by_mode(width, height, mode, layer2):
        if mode == RenderMode.DEFAULT:
            return Dim(
                int(width * 3.0),
                int(height * 3.0))
        elif mode == RenderMode.TWO_ROWS:
            return Dim(
                int(width * 3.0),
                int(height * (2.0 if layer2 else 1.0)))


    def copy_layer_to(source, destination, x, y):
        def make_layer_visible_with_alpha(layer):
            if len(layer.children) == 0: # Cannot add alpha for layer group
                pdb.gimp_layer_add_alpha(layer)
            pdb.gimp_drawable_set_visible(layer, True)

        temp_layer = pdb.gimp_layer_new_from_drawable(source, destination)
        make_layer_visible_with_alpha(temp_layer)
        destination.insert_layer(temp_layer)
        temp_layer.translate(x, y)

    def redraw_preview(preview_ctx, drawable):
        if preview_ctx.gtk_preview_box:
            preview_ctx.gtk_display_box.remove(preview_ctx.gtk_preview_box)

        preview_ctx.gtk_preview_box = gimpui.DrawablePreview(drawable)
        preview_ctx.gtk_display_box.pack_start(preview_ctx.gtk_preview_box, True, True, 0)

        preview_ctx.gtk_window.show_all()

    # Compute base image size
    new_image_dim = get_image_dim_by_mode(width, height, mode, layer2)

    # Create temp image that will accomodate new layers
    if preview_context.temp_img:
        gimp.delete(preview_context.temp_img)
    
    preview_context.temp_img = pdb.gimp_image_new(
        new_image_dim.width,
        new_image_dim.height,
        image_type)
    preview_context.temp_img.disable_undo()

    if mode == RenderMode.DEFAULT:
        # Copy source layer 9 times to new image in tiled way
        for y in range(0, 3):
            for x in range(0, 3):
                use_layer2 = (y != 1 or x != 1) and layer2
                copy_layer_to(
                    layer2 if use_layer2 else layer1,
                    preview_context.temp_img,
                    x * width,
                    y * height)
    elif mode == RenderMode.TWO_ROWS:
        # Copy source layer 9 times to new image in tiled way
        for x in range(0, 3):
            copy_layer_to(layer1, preview_context.temp_img, x * width, 0)

        if layer2 is not None:
            for x in range(0, 3):
                copy_layer_to(layer2, preview_context.temp_img, x * width, height)

    # Disable interpolation and zoom the image by scaling
    pdb.gimp_context_set_interpolation(0)
    final_layer = preview_context.temp_img.flatten()
    pdb.gimp_layer_scale(
        final_layer,
        new_image_dim.width * zoom,
        new_image_dim.height * zoom,
        False)

    redraw_preview(preview_context, final_layer)

def update_preview(widget, preview_context):
    pdb.gimp_message("update_preview({})".format(preview_context))

    def get_layer_from_image(image, name):
        for layer in image.layers:
            if layer.name == name:
                return layer
        return None

    layer1 = get_layer_from_image(preview_context.image_ref, preview_context.layer_names[0])
    layer2 = get_layer_from_image(preview_context.image_ref, preview_context.layer_names[1])

    update_preview_internal(
        preview_context.image_ref.base_type,
        preview_context.image_ref.width,
        preview_context.image_ref.width,
        preview_context.zoom_level,
        preview_context.mode,
        layer1,
        layer2,
        preview_context)

def build_gui(preview_context):
    pdb.gimp_message("build_gui({})".format(preview_context))

    def get_image_layer_names(image, add_empty=False):
        layer_names = []

        if add_empty:
            layer_names.append("- none -")

        for layer in image.layers:
            layer_names.append(layer.name)
        return layer_names

    def zoom_in(widget, preview_context):
        pdb.gimp_message("zoom_in")
        preview_context.zoom_level *= 2.0
        update_preview(None, preview_context)

    def zoom_out(widget, preview_context):
        pdb.gimp_message("zoom_out")
        preview_context.zoom_level /= 2.0
        update_preview(None, preview_context)

    def update_layer_names(combo, preview_context, index):
        pdb.gimp_message("update_layer_names({}, {})".format(index, combo.get_active_text()))
        preview_context.layer_names[index] = combo.get_active_text()
        update_preview(None, preview_context)

    def change_display_mode(widget, preview_context):
        pdb.gimp_message("change_display_mode({})".format(preview_context))
        preview_context.mode = widget.get_active_text()
        update_preview(None, preview_context)

    # Window
    preview_context.gtk_window = gtk.Window()
    preview_context.gtk_window.set_title("Tile Preview")
    preview_context.gtk_window.connect('destroy',  close_preview_window)

    window_box = gtk.VBox()
    preview_context.gtk_window.add(window_box)
    preview_context.gtk_window.set_keep_above(True)

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
    preview_context.gtk_display_box = create_hbox(window_box, True)

    ## Bottom box model
    bottom_wrap_hbox = create_hbox(window_box, False)
    bottom_label_vbox = create_vbox(bottom_wrap_hbox, True)
    bottom_control_vbox = create_vbox(bottom_wrap_hbox, True)

    ### Mode select
    create_label("Preview mode", bottom_label_vbox)
    combo = create_combo(RenderMode.get_string_annotations(), bottom_control_vbox)
    combo.connect(
        "changed",
        change_display_mode,
        preview_context)
    combo.set_active(0) # Trigger on change

    ### Layers selection
    labels = [ "Primary layer", "Secondary layer" ]
    for label in labels:
        create_label(label, bottom_label_vbox)

    for index in range(len(labels)):
        combo = create_combo(
            get_image_layer_names(preview_context.image_ref, add_empty=index),
            bottom_control_vbox)
        combo.connect(
            "changed",
            update_layer_names,
            preview_context,
            index)
        combo.set_active(0)

    ## Refresh button
    refresh_btn = create_button("Refresh", window_box)
    refresh_btn.connect(
        "clicked",
        update_preview,
        preview_context)

    preview_context.gtk_window.show_all()

def close_preview_window(ret):
    pdb.gimp_message("quitting Animation preview plugin")
    gtk.main_quit()

def run_tile_preview_plugin_function(_image, _drawable):
    pdb.gimp_message("Running Tile Preview plugin")

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

