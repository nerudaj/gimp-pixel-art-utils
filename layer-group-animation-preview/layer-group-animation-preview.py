#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject

# global state
window = None
display_box = None
preview_box = None
layers_list = None
active_layer = None
current_frame = None
frame_index = 0
fps = 16

def null_callback():
    print("null_callback called")

def update_fps(widget, entry):
    pdb.gimp_message("got here")
    global fps
    fps_text = entry.get_text()
    fps = int(fps_text)
    pdb.gimp_message("New fps: {}".format(fps))

def create_preview_window():
    pdb.gimp_message("create_preview_window start")

    global window
    global current_frame
    global layers_list
    global display_box
    global fps

    horizontal_spacing = 10
    vertical_spacing = 0

    window = gtk.Window()
    window.set_title("Animation preview")
    window.connect('destroy',  close_preview_window)
    window_box = gtk.VBox()
    window.add(window_box)
    window.set_keep_above(True)

    display_box = gtk.HBox()
    window_box.pack_start(display_box, True, True, vertical_spacing)

    # FPS controls
    fps_controls_box = gtk.HBox()
    window_box.pack_start(fps_controls_box, True, True, vertical_spacing)

    fps_entry_label = gtk.Label("FPS")
    fps_controls_box.pack_start(fps_entry_label, True, True, horizontal_spacing)

    fps_entry = gtk.Entry()
    fps_entry.set_text("{}".format(fps))
    fps_controls_box.pack_start(fps_entry, True, True, horizontal_spacing)

    btn = gtk.Button()
    btn.set_label("Update")
    btn.connect("clicked", update_fps, fps_entry)
    fps_controls_box.pack_start(btn, True, True, horizontal_spacing)

    # Layer group selection
    layer_select_box = gtk.HBox()
    window_box.pack_start(layer_select_box, True, True, vertical_spacing)

    layer_combo_label = gtk.Label("Select layer group")
    layer_select_box.pack_start(layer_combo_label, True, True, horizontal_spacing)

    combox = gtk.combo_box_new_text()
    combox.connect("changed", active_layer_changed)
    for layer in layers_list:
        pdb.gimp_message(layer.name)
        combox.append_text(layer.name)
    combox.set_active(0)
    layer_select_box.pack_start(combox, True, True, horizontal_spacing)

    window.show_all()
    update_preview()

def active_layer_changed(combo):
    pdb.gimp_message("active_layer_changed to {}".format(combo.get_active_text()))

    global layers_list
    global active_layer
    global frame_index

    for layer in layers_list:
        if layer.name == combo.get_active_text():
            pdb.gimp_message("Found matching layer, setting active_layer")
            active_layer = layer
            frame_index = 0

def update_preview():
    #pdb.gimp_message("update_preview")

    global window
    global active_layer
    global current_frame
    global display_box
    global preview_box
    global frame_index
    global fps

    active_layer_len = len(active_layer.children)
    current_frame = active_layer.children[active_layer_len - frame_index - 1]
    frame_index += 1
    if frame_index == len(active_layer.children):
        frame_index = 0

    # Remove anything that might have been rendered before and add new drawable
    if preview_box is not None:
        display_box.remove(preview_box)
    preview_box = gimpui.DrawablePreview(current_frame)
    display_box.pack_start(preview_box, True, True, 0)

    window.show_all()
    gobject.timeout_add(1000 / fps, update_preview)

def close_preview_window(ret):
    pdb.gimp_message("quitting Animation preview plugin")
    gtk.main_quit()

def is_layer_group(layer):
    return len(layer.children) > 0

def run_plugin_function(_image, _drawable):
    pdb.gimp_message("Running Animation Preview plugin")

    global image_ref
    global layers_list
    global active_layer
    global current_frame

    image_ref = _image
    layers_list = []

    pdb.gimp_message("Image has {} layers".format(len(image_ref.layers)))
    for layer in image_ref.layers:
        if is_layer_group(layer):
            pdb.gimp_message("Adding layer '{}'".format(layer.name))
            layers_list.append(layer)

    create_preview_window()
    gtk.main()

######################
##### Run script #####
######################

register(
          "run_plugin_function",
          "Previews animations stored in distinct layer groups",
          "Previews animations stored in distinct layer groups",
          "doomista",
          "Apache 2 license",
          "2022",
          "Layer Group Animation Preview",
          "*",
          [
              (PF_IMAGE, "image", "Input image", None),
              (PF_DRAWABLE, "drawable", "Input drawable", None),
          ],
          [],
          run_plugin_function, menu="<Image>/Tools/Pixel Art")
main()

