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

    global FPS
    if FPS == 0:
        update_preview()

def zoom_out(widget):
    # pdb.gimp_message("zoom_out")
    global zoom_level
    zoom_level = zoom_level / 2.0
    
    global FPS
    if FPS == 0:
        update_preview()

def update_preview_wrapper(widget):
    update_preview()

def update_preview():
    # pdb.gimp_message("update_preview")

    global image_ref
    global zoom_level

    active_layer = image_ref.active_layer
    
    # Compute base image size
    new_image_width = int(active_layer.width * 3.0)
    new_image_height = int(active_layer.height * 3.0)

    # Create temp image that will accomodate new layers
    temp_img = pdb.gimp_image_new(
        new_image_width,
        new_image_height,
        image_ref.base_type)
    temp_img.disable_undo()

    # Copy source layer 9 times to new image in tiled way
    for y in range(0, 3):
        for x in range(0, 3):
            temp_layer = pdb.gimp_layer_new_from_drawable(active_layer, temp_img)
            temp_img.insert_layer(temp_layer)
            temp_layer.translate(
                x * active_layer.width,
                y * active_layer.height)

    # Disable interpolation and zoom the image by scaling    
    pdb.gimp_context_set_interpolation(0)
    final_layer = temp_img.flatten()
    pdb.gimp_layer_scale(
        final_layer,
        new_image_width * zoom_level,
        new_image_height * zoom_level,
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

    # Restart timer for update
    global FPS
    if FPS != 0:
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
    display_box = gtk.HBox()
    window_box.pack_start(display_box, True, True, horizontal_spacing)

    button_box = gtk.HBox()
    window_box.pack_start(button_box, False, False, vertical_spacing)
    
    zoom_button = gtk.Button()
    zoom_button.set_label("+")
    zoom_button.connect("clicked", zoom_in)
    button_box.pack_start(zoom_button, True, True, horizontal_spacing)

    unzoom_button = gtk.Button()
    unzoom_button.set_label("-")
    unzoom_button.connect("clicked", zoom_out)
    button_box.pack_start(unzoom_button, True, True, horizontal_spacing)
    
    global FPS
    if FPS == 0:
        update_btn = gtk.Button()
        update_btn.set_label("Update")
        update_btn.connect("clicked", update_preview_wrapper)
        button_box.pack_start(update_btn, True, True, horizontal_spacing)

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
    zoom_level = 128 / image_ref.active_layer.width 
    
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

