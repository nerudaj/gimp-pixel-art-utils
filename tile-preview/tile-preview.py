#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject

# Image globals
image_ref = None
temp_img = None

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
    DEFAULT = "3x3"
    TWO_ROWS = "Two rows"

    @staticmethod
    def get_string_annotations():
        return [RenderMode.DEFAULT, RenderMode.TWO_ROWS]

# Gtk globals
window = None
display_box = None
preview_box = None

# Other globals
zoom_level = 1.0
FPS = 1

def zoom_in(widget):
    pdb.gimp_message("zoom_in")
    global zoom_level
    zoom_level = 2.0 * zoom_level

    # global FPS
    # if FPS == 0:
        # update_preview()

def zoom_out(widget):
    pdb.gimp_message("zoom_out")
    global zoom_level
    zoom_level = zoom_level / 2.0
    
    # global FPS
    # if FPS == 0:
        # update_preview()

def get_image_layer_names(image):
    layer_names = []
    for layer in image.layers:
        layer_names.append(layer.name)
    return layer_names

def get_layer_from_image(image, name):
    for layer in image.layers:
        if layer.name == name:
            return layer
    return None

def get_image_dim_by_mode(width, height, mode):
    if mode == RenderMode.DEFAULT:
        return Dim(
            int(width * 3.0),
            int(height * 3.0))
    elif mode == RenderMode.TWO_ROWS:
        return Dim(
            int(width * 3.0),
            int(height * 2.0))

def make_layer_visible_with_alpha(layer):
    if len(layer.children) == 0: # Cannot add alpha for layer group
        pdb.gimp_layer_add_alpha(layer)
    pdb.gimp_drawable_set_visible(layer, True)

def update_preview_internal(image_type, width, height, zoom, mode, layer1, layer2):
    pdb.gimp_message("update_preview_internal({}, {}, {}, {}, {}, {})".format(width, height, zoom, mode, layer1, layer2))

    # Compute base image size
    new_image_dim = get_image_dim_by_mode(width, height, mode)

    # Create temp image that will accomodate new layers
    temp_img = pdb.gimp_image_new(
        new_image_dim.width,
        new_image_dim.height,
        image_type)
    temp_img.disable_undo()

    if mode == RenderMode.DEFAULT:
        # Copy source layer 9 times to new image in tiled way
        for y in range(0, 3):
            for x in range(0, 3):
                temp_layer = pdb.gimp_layer_new_from_drawable(layer1, temp_img)
                make_layer_visible_with_alpha(temp_layer)
                temp_img.insert_layer(temp_layer)
                temp_layer.translate(
                    x * width,
                    y * height)
    elif mode == RenderMode.TWO_ROWS:
        # Copy source layer 9 times to new image in tiled way
        for x in range(0, 3):
            temp_layer = pdb.gimp_layer_new_from_drawable(layer1, temp_img)
            make_layer_visible_with_alpha(temp_layer)
            temp_img.insert_layer(temp_layer)
            temp_layer.translate(
                x * width,
                0)
        for x in range(0, 3):
            temp_layer = pdb.gimp_layer_new_from_drawable(layer2, temp_img)
            make_layer_visible_with_alpha(temp_layer)
            temp_img.insert_layer(temp_layer)
            temp_layer.translate(
                x * width,
                height)

    # Disable interpolation and zoom the image by scaling    
    pdb.gimp_context_set_interpolation(0)
    final_layer = temp_img.flatten()
    pdb.gimp_layer_scale(
        final_layer,
        new_image_dim.width * zoom,
        new_image_dim.height * zoom,
        False)

    # Redraw newly created image
    global window
    global display_box
    global preview_box
    
    if preview_box is not None:
        display_box.remove(preview_box)
    
    preview_box = gimpui.DrawablePreview(final_layer)
    display_box.pack_start(preview_box, True, True, 10)
    
    window.show_all()

def update_preview2(widget, image, mode, combo1 = None, combo2 = None):
    pdb.gimp_message("update_preview2({}, {}, {})".format(mode, combo1, combo2))
    
    layer1 = get_layer_from_image(image, combo1.get_active_text()) if combo1 != None else None
    layer2 = get_layer_from_image(image, combo2.get_active_text()) if combo2 != None else None

    global zoom_level
    
    update_preview_internal(
        image.base_type,
        image.width,
        image.height,
        zoom_level,
        mode,
        layer1,
        layer2)

def change_display_mode(widget, wrap_hbox, image):
    pdb.gimp_message("change_display_mode")

    for child in wrap_hbox.get_children():
        wrap_hbox.remove(child)

    label_vbox = create_vbox(wrap_hbox, True)
    control_vbox = create_vbox(wrap_hbox, True)

    mode = widget.get_active_text()
    layer_names = get_image_layer_names(image)

    combo = None
    if mode == RenderMode.DEFAULT:
        create_label("Pick layer", label_vbox)
        combo = create_combo(layer_names, control_vbox)
        combo.connect(
            "changed",
            update_preview2,
            image,
            mode,
            combo)
    elif mode == RenderMode.TWO_ROWS:
        create_label("Pick upper layer", label_vbox)
        create_label("Pick bottom layer", label_vbox)

        combo = create_combo(layer_names, control_vbox)
        combo2 = create_combo(layer_names, control_vbox)

        combo.connect(
            "changed",
            update_preview2,
            image,
            mode,
            combo,
            combo2)
        combo2.connect(
            "changed",
            update_preview2,
            image,
            mode,
            combo,
            combo2)
    combo.set_active(0) # Trigger change

    global window
    window.show_all()

def build_gui(image):
    pdb.gimp_message("build_gui")

    horizontal_spacing = 10
    vertical_spacing = 0

    global window
    window = gtk.Window()
    window.set_title("Tile Preview")
    window.connect('destroy',  close_preview_window)
    window_box = gtk.VBox()
    window.add(window_box)
    window.set_keep_above(True)

    global display_box
    display_box = gtk.HBox()
    window_box.pack_start(display_box, True, True, horizontal_spacing)

    button_box = gtk.HBox()
    window_box.pack_start(button_box, False, False, vertical_spacing)
    
    zoom_button = gtk.Button()
    zoom_button.set_label("+")
    # TODO: send wrap box and image into zoom_in
    zoom_button.connect("clicked", zoom_in)
    button_box.pack_start(zoom_button, True, True, horizontal_spacing)

    unzoom_button = gtk.Button()
    unzoom_button.set_label("-")
    # TODO: send wrap box and image into zoom_out
    unzoom_button.connect("clicked", zoom_out)
    button_box.pack_start(unzoom_button, True, True, horizontal_spacing)

    wrap_hbox = create_hbox(window_box, False)
    label_vbox = create_vbox(wrap_hbox, True)
    control_vbox = create_vbox(wrap_hbox, True)
    optional_wrap_hbox = create_hbox(window_box, False)

    # Mode select
    create_label("Select mode", label_vbox)
    combo = create_combo(RenderMode.get_string_annotations(), control_vbox)
    combo.connect(
        "changed",
        change_display_mode,
        optional_wrap_hbox,
        image)
    combo.set_active(0) # Trigger on change

    window.show_all()

def close_preview_window(ret):
    pdb.gimp_message("quitting Animation preview plugin")
    global temp_img
    
    gimp.delete(temp_img)
    gtk.main_quit()

def run_tile_preview_plugin_function(_image, _drawable):
    pdb.gimp_message("Running Tile Preview plugin")

    global image_ref
    image_ref = _image
    
    global zoom_level
    zoom_level = 128.0 / image_ref.active_layer.width 
    
    build_gui(image_ref)
    #update_preview()
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

