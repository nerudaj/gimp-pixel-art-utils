#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject

class Playback:
    def __init__(self, frame_count):
        self.fps = 1
        self.playing = False
        self.dirty = True
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
        self.dirty = True

    def prev_frame(self):
        self.frame_index -= 1
        if self.frame_index < 0:
            self.frame_index = self.frame_count - 1
        self.dirty = True

    def update_fps(self, fps):
        self.fps = fps

    def update(self):
        if self.playing:
            self.next_frame()
        self.dirty = False

# global state
window = None
display_box = None
preview_box = None
layers_list = None
active_layer = None
current_frame = None
frame_index = 0
fps = 16
playback = None

def update_layers_info(image):
    global layers_list
    
    layers_list = []
    for layer in image_ref.layers:
        # Is layer group (= has children)
        if len(layer.children) > 0:
            # pdb.gimp_message("Adding layer '{}'".format(layer.name))
            layers_list.append(layer)

def create_button(label, box, spacing):
    btn = gtk.Button()
    btn.set_label(label)
    box.pack_start(btn, True, True, spacing)
    return btn

def update_fps(widget, entry):
    global fps
    global playback

    fps_text = entry.get_text()
    fps = int(fps_text)
    playback.update_fps(fps)

def start_playback(widget):
    global playback
    playback.start()

def stop_playback(widget):
    global playback
    playback.stop()

def prev_frame(widget):
    global playback
    playback.prev_frame()

def next_frame(widget):
    global playback
    playback.next_frame()

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

    display_box = gtk.HBox()
    window_box.pack_start(display_box, True, True, vertical_spacing)

    # Playback controls
    playback_box = gtk.HBox();
    window_box.pack_start(playback_box, False, True, vertical_spacing)
    
    play_btn = create_button("Play", playback_box, horizontal_spacing)
    play_btn.connect("clicked", start_playback)
    
    stop_btn = create_button("Stop", playback_box, horizontal_spacing)  
    stop_btn.connect("clicked", stop_playback)

    prev_btn = create_button("Prev", playback_box, horizontal_spacing)
    prev_btn.connect("clicked", prev_frame)

    next_btn = create_button("Next", playback_box, horizontal_spacing)
    prev_btn.connect("clicked", next_frame)

    # FPS controls
    fps_controls_box = gtk.HBox()
    window_box.pack_start(fps_controls_box, False, True, vertical_spacing)

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
    window_box.pack_start(layer_select_box, False, True, vertical_spacing)

    layer_combo_label = gtk.Label("Group to play")
    layer_select_box.pack_start(layer_combo_label, True, True, horizontal_spacing)

    combox = gtk.combo_box_new_text()
    combox.connect("changed", active_layer_changed, fps_entry)
    for layer in layers_list:
        # pdb.gimp_message(layer.name)
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
    
    pdb.gimp_message("Is playback none: {}".format(playback is None))

def get_scaled_layer(layer, scale):
    global image_ref
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

def update_preview():
    pdb.gimp_message("update_preview")
    
    global playback
    global current_frame
    global active_layer

    if not (playback.playing or playback.dirty):
        gobject.timeout_add(1000 / playback.fps, update_preview)
        return

    playback.update()
    
    active_layer_len = len(active_layer.children)
    current_frame = active_layer.children[active_layer_len - playback.frame_index - 1]
    
    global display_box
    global preview_box
    global window
    
    if preview_box is not None:
        display_box.remove(preview_box)

    preview_box = gimpui.DrawablePreview(
        get_scaled_layer(current_frame, 10))
    display_box.pack_start(preview_box, True, True, 0)
    window.show_all()
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
          "Layer Group Animation Preview",
          "*",
          [
              (PF_IMAGE, "image", "Input image", None),
              (PF_DRAWABLE, "drawable", "Input drawable", None),
          ],
          [],
          run_plugin_function, menu="<Image>/Tools/Pixel Art")
main()

