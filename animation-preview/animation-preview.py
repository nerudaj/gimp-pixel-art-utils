#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject

class Playback:
    def __init__(self, frame_count):
        self.fps = 1
        self.playing = False
        self.frame_index = 0
        self.frame_count = frame_count

    def start(self):
        self.playing = True

    def stop(self):
        self.playing = False

    def next_frame(self):
        self.frame_index += 1
        if self.frame_index == self.frame_count:
            self.frame_index = 0

    def prev_frame(self):
        self.frame_index -= 1
        if self.frame_index < 0:
            self.frame_index = self.frame_count - 1

    def update_fps(self, fps):
        self.fps = fps

# GUI HELPERS
def create_label(text, parent, spacing):
    label = gtk.Label(text)
    parent.pack_start(label, True, True, spacing)
    return label

def create_button(label, box, spacing):
    btn = gtk.Button()
    btn.set_label(label)
    box.pack_start(btn, True, True, spacing)
    return btn

def create_vbox(parent, grow_horizontally, spacing):
    box = gtk.VBox()
    parent.pack_start(box, grow_horizontally, True, spacing)
    return box

def create_hbox(parent, grow_vertically, spacing):
    box = gtk.HBox()
    parent.pack_start(box, grow_vertically, True, spacing)
    return box

# global state
window = None
display_box = None
preview_box = None
layers_list = None
active_layer = None
current_frame = None
current_frame_label = None
frame_index = 0
playback = None
zoom_level = -1.0

def update_layers_info(image):
    global layers_list
    
    layers_list = []
    for layer in image_ref.layers:
        # Is layer group (= has children)
        if len(layer.children) > 0:
            # pdb.gimp_message("Adding layer '{}'".format(layer.name))
            layers_list.append(layer)

def update_fps(widget, entry):
    global playback

    fps_text = entry.get_text()
    fps = int(fps_text)
    playback.update_fps(fps)

def start_playback(widget):
    global playback
    playback.start()
    update_preview()

def stop_playback(widget):
    global playback
    playback.stop()

def prev_frame(widget):
    global playback
    playback.prev_frame()
    update_preview(force=True)

def next_frame(widget):
    global playback
    playback.next_frame()
    update_preview(force=True)

def zoom_in(widget):
    global zoom_level
    zoom_level *= 2.0
    update_preview(force=True)

def zoom_out(widget):
    global zoom_level
    zoom_level /= 2.0
    update_preview(force=True)

def create_preview_window():
    pdb.gimp_message("create_preview_window start")

    global window
    global current_frame
    global layers_list
    global display_box

    horizontal_spacing = 10
    vertical_spacing = 0

    window = gtk.Window()
    window.set_title("Animation preview")
    window.connect('destroy',  close_preview_window)
    window_box = gtk.VBox()
    window.add(window_box)
    window.set_keep_above(True)

    # Display current frame name
    current_layer_show_box = create_hbox(window_box, False, vertical_spacing)
    create_label("Current frame:", current_layer_show_box, horizontal_spacing)
    
    global current_frame_label
    current_frame_label = create_label("", current_layer_show_box, horizontal_spacing)
    
    # Playback & zoom controls
    playback_box = create_hbox(window_box, False, vertical_spacing)
    
    play_btn = create_button("Play", playback_box, horizontal_spacing)
    play_btn.connect("clicked", start_playback)
    
    stop_btn = create_button("Stop", playback_box, horizontal_spacing)
    stop_btn.connect("clicked", stop_playback)

    prev_btn = create_button("Prev", playback_box, horizontal_spacing)
    prev_btn.connect("clicked", prev_frame)

    next_btn = create_button("Next", playback_box, horizontal_spacing)
    next_btn.connect("clicked", next_frame)

    # Target for image preview
    display_box = create_hbox(window_box, True, vertical_spacing)

    # Bottom controls are organized in following box model:
    # LL CC CC
    # LL CC CC
    # LL CC CC

    # Main Vboxes
    bottom_controls_hbox = create_hbox(window_box, False, horizontal_spacing)
    labels_vbox = create_vbox(bottom_controls_hbox, True, horizontal_spacing)
    controls_vbox = create_vbox(bottom_controls_hbox, True, horizontal_spacing)

    # Zoom controls
    zoom_label_box = create_hbox(labels_vbox, True, vertical_spacing)
    zoom_box = create_hbox(controls_vbox, False, vertical_spacing)
    
    create_label("Zoom", zoom_label_box, horizontal_spacing)

    zoom_out_btn = create_button("-", zoom_box, horizontal_spacing)
    zoom_out_btn.connect("clicked", zoom_out)
    
    zoom_in_btn = create_button("+", zoom_box, horizontal_spacing)
    zoom_in_btn.connect("clicked", zoom_in)

    # FPS controls
    fps_label_box = create_hbox(labels_vbox, True, vertical_spacing)
    fps_controls_box = create_hbox(controls_vbox, False, vertical_spacing)
    create_label("FPS", fps_label_box, horizontal_spacing)

    DEFAULT_FPS = 16
    fps_entry = gtk.Entry()
    fps_entry.set_text("{}".format(DEFAULT_FPS))
    fps_controls_box.pack_start(fps_entry, True, True, horizontal_spacing)

    btn = gtk.Button()
    btn.set_label("Update")
    btn.connect("clicked", update_fps, fps_entry)
    fps_controls_box.pack_start(btn, True, True, horizontal_spacing)

    # Layer group selection
    layer_label_box = create_hbox(labels_vbox, True, vertical_spacing)
    layer_select_box = create_hbox(controls_vbox, False, vertical_spacing)
    create_label("Group to play", layer_label_box, horizontal_spacing)

    combox = gtk.combo_box_new_text()
    combox.connect("changed", active_layer_changed, fps_entry)
    for layer in layers_list:
        combox.append_text(layer.name)
    combox.set_active(0)
    layer_select_box.pack_start(combox, True, True, horizontal_spacing)

    window.show_all()
    update_preview()

def active_layer_changed(combo, fps_entry):
    pdb.gimp_message("active_layer_changed({})"
        .format(combo.get_active_text()))

    global layers_list
    global active_layer
    global playback

    for layer in layers_list:
        if layer.name == combo.get_active_text():
            pdb.gimp_message("Found matching layer, setting active_layer")
            active_layer = layer
            playback = Playback(len(active_layer.children))
            update_fps(None, fps_entry)

    # First time around, initialize zoom_level, then don't touch it
    global zoom_level
    if zoom_level == -1.0:
        zoom_level = 128.0 / active_layer.width

    update_preview(force=True)

def get_scaled_layer(layer, image_ref, scale):
    temp_img = pdb.gimp_image_new(
        layer.width,
        layer.height,
        image_ref.base_type)
    temp_img.disable_undo()
    
    temp_layer = pdb.gimp_layer_new_from_drawable(
        layer, temp_img)
    temp_img.insert_layer(temp_layer)
    pdb.gimp_context_set_interpolation(0)
    pdb.gimp_layer_scale(
        temp_layer,
        layer.width * scale,
        layer.height * scale,
        False)
    
    return temp_layer

def update_preview(force=False):
    # pdb.gimp_message("update_preview")
    
    global playback
    global current_frame
    global active_layer

    # If force == True & playback.playing == True then forced update can be skipped
    # because there is one scheduled
    # If both are false then there is nothing to update
    if force == playback.playing:
        return

    if playback.playing:
        playback.next_frame()

    active_layer_len = len(active_layer.children)
    current_frame = active_layer.children[active_layer_len - playback.frame_index - 1]

    global current_frame_label
    current_frame_label.set_text(current_frame.name)

    global display_box
    global preview_box
    global window

    if preview_box is not None:
        display_box.remove(preview_box)

    global zoom_level
    global image_ref

    preview_box = gimpui.DrawablePreview(
        get_scaled_layer(current_frame, image_ref, zoom_level))
    display_box.pack_start(preview_box, True, True, 0)
    window.show_all()

    if playback.playing:
        gobject.timeout_add(1000 / playback.fps, update_preview)

def close_preview_window(ret):
    pdb.gimp_message("quitting Animation preview plugin")
    gtk.main_quit()

def run_plugin_function(_image, _drawable):
    pdb.gimp_message("Running Animation Preview plugin")

    global image_ref
    image_ref = _image

    pdb.gimp_message("Image has {} layers".format(len(image_ref.layers)))
    update_layers_info(image_ref)

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
          "Animation Preview",
          "*",
          [
              (PF_IMAGE, "image", "Input image", None),
              (PF_DRAWABLE, "drawable", "Input drawable", None),
          ],
          [],
          run_plugin_function, menu="<Image>/Tools/Pixel Art")
main()

