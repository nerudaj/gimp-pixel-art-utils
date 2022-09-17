#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject

# Image globals
image_ref = None
temp_img = None

# Gtk globals
window = None
display_box = None
preview_box = None

# Other globals
zoom_level = 1.0
FPS = 1

def zoom_in(widget):
    # pdb.gimp_message("zoom_in")
    global zoom_level
    zoom_level = 2.0 * zoom_level

def zoom_out(widget):
    # pdb.gimp_message("zoom_out")
    global zoom_level
    zoom_level = zoom_level / 2.0

def update_preview():
    # pdb.gimp_message("update_preview")

    global image_ref
    global temp_img
    global zoom_level

    active_layer = image_ref.active_layer

    new_image_width = int(active_layer.width * 3.0 * zoom_level)
    new_image_height = int(active_layer.height * 3.0 * zoom_level)
    
    # If image does not exists, create it
    if temp_img is None:
        temp_img = pdb.gimp_image_new(
            new_image_width,
            new_image_height,
            image_ref.base_type)
        temp_img.disable_undo()

    # Check whether image needs resizing
    width_mismatches = new_image_width != temp_img.width
    height_mismatches = new_image_height != temp_img.height
    if width_mismatches or height_mismatches:
        temp_img.resize(new_image_width, new_image_height, 0, 0)

    # Copy source layer 9 times to new image in tiled, scaled way
    scaled_layer_width = int(active_layer.width * zoom_level)
    scaled_layer_height = int(active_layer.height * zoom_level)
    for y in range(0, 3):
        for x in range(0, 3):
            temp_layer = pdb.gimp_layer_new_from_drawable(active_layer, temp_img)
            temp_img.insert_layer(temp_layer)
            pdb.gimp_layer_scale_full(
                temp_layer,
                scaled_layer_width,
                scaled_layer_height,
                False,
                0) # no interpolation
            temp_layer.translate(
                x * scaled_layer_width,
                y * scaled_layer_height)

    # Redraw newly created image
    global window
    global display_box
    global preview_box
    
    if preview_box is not None:
        display_box.remove(preview_box)
    
    preview_box = gimpui.DrawablePreview(temp_img.flatten())
    display_box.pack_start(preview_box, True, True)
    
    window.show_all()

    # Restart timer for update
    global FPS
    gobject.timeout_add(1000 / FPS, update_preview)

def build_gui():
    pdb.gimp_message("build_gui")

    horizontal_spacing = 10
    vertical_spacing = 0

    global window
    window = gtk.Window()
    window.set_title("Tile preview")
    window.connect('destroy',  close_preview_window)
    window_box = gtk.VBox()
    window.add(window_box)
    window.set_keep_above(True)

    global display_box
    display_box = gtk.HBox();
    window_box.pack_start(display_box, True, True, vertical_spacing)

    button_box = gtk.HBox()
    window_box.pack_start(button_box, True, False, vertical_spacing)
    
    zoom_button = gtk.Button()
    zoom_button.set_label("+")
    zoom_button.connect("clicked", zoom_in)
    button_box.pack_start(zoom_button, True, True, horizontal_spacing)

    unzoom_button = gtk.Button()
    unzoom_button.set_label("-")
    unzoom_button.connect("clicked", zoom_out)
    button_box.pack_start(unzoom_button, True, True, horizontal_spacing)

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
    
    build_gui()
    update_preview()
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

