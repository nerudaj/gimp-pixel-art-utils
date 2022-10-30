#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject
import atk
import math
import json

def tuple_second_elem(lt):
    return lt[1];

def pack_layers(layers, frame_sum):
    pdb.gimp_message("pack_layers({}, {})"
        .format(layers, frame_sum))
    layers = sorted(layers, key=tuple_second_elem, reverse=True)

    wrap_count = math.sqrt(frame_sum)
    if tuple_second_elem(layers[0]) > wrap_count:
        wrap_count = tuple_second_elem(layers[0])

    rows = [ [] ]
    current_row_frame_sum = 0
    for lt in layers:
        if current_row_frame_sum + tuple_second_elem(lt) > wrap_count:
            current_row_frame_sum = tuple_second_elem(lt)
            rows.append([lt])
        else:
            current_row_frame_sum += tuple_second_elem(lt)
            rows[-1].append(lt)

    return rows

def compute_packed_layers(image):
    pdb.gimp_message("compute_packed_layers({})"
        .format(image))
    frame_sum = 0 # total number of frames that will be in spritesheet
    layer_refs = []
    for layer in image.layers:
        frame_count = len(layer.children)
        if frame_count = 0:
            continue

        layer_refs.append((layer, frame_count))
        frame_sum += frame_count

    return pack_layers(layer_refs, frame_sum)

def export_annotations(filename, offset, spacing, tile_width, tile_height, count, items_per_row, nrows):
    pdb.gimp_message("export_annotations({}, {}, {})".format(filename, offset, spacing))

def export_spritesheet(filename, offset, spacing, image):
    pdb.gimp_message("export_spritesheet({}, {}, {})".format(filename, offset, spacing))
    packed_layers = compute_packed_layers(image)
    pdb.gimp_message("has packed")
    
    max_frames_per_row = 0
    for lt in packed_layers[0]:
        max_frames_per_row += tuple_second_elem(lt)
    row_count = len(packed_layers)
    pdb.gimp_message("has max and count")

    output_width = image.width * max_frames_per_row + spacing * (1 - max_frames_per_row) + offset * 2
    output_height = image.height * row_count + spacing * (1 - row_count) + offset * 2
    pdb.gimp_message("Image output dimensions: {}x{}"
        .format(output_width, output_height))
    
    export_img = pdb.gimp_image_new(
        output_width,
        output_height,
        image.base_type)

    row = 0
    col = 0
    for row in packed_layers:
        for lt in row:
            for layer in lt[1].children:
                x 
            for x in range(col, col + lt[1]):
                temp_layer = pdb.gimp_layer_new_from_drawable(
                    lt[0], export_img)
                pdb.gimp_layer_add_alpha(temp_layer)
                img.insert_layer(temp_layer)
                temp_layer.translate(
                    offset + x *(image.width + spacing),
                    offset + row * (image.height + spacing))
            col += lt[1]
        row += 1
    
    result = pdb.gimp_iamge_merge_visible_layers(img, 0)
    pdb.gimp_file_save(img, result, filename, filename)
    # TODO: export annotations
    close_plugin_window(0)

def pick_file(widget, offset_input, spacing_input, _image):
    save_dlg = gtk.FileChooserDialog(
        "Filename", 
        None, 
        gtk.FILE_CHOOSER_ACTION_SAVE,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))

    response = save_dlg.run()
    save_filename = save_dlg.get_filename() # null if cancelled
    save_dlg.destroy()

    if save_filename is not None:
        export_spritesheet(
            save_filename,
            int(offset_input.get_text()),
            int(spacing_input.get_text()),
            _image)

def create_value_input(window_box, label, init_value, horizontal_spacing, vertical_spacing):
    pdb.gimp_message("create_value_input")
    input_hbox = gtk.HBox()
    window_box.pack_start(input_hbox, True, True, vertical_spacing)
    
    input_label = gtk.Label(label)
    input_hbox.pack_start(input_label, True, True, horizontal_spacing)
    
    input_entry = gtk.Entry()
    input_entry.set_text("{}".format(init_value))
    input_hbox.pack_start(input_entry, True, True, horizontal_spacing)
    return input_entry

def build_gui(_image):
    pdb.gimp_message("build_gui")

    horizontal_spacing = 10
    vertical_spacing = 0

    window = gtk.Window()
    window.set_title("Spritesheetize")
    window.connect('destroy',  close_plugin_window)
    window_box = gtk.VBox()
    window.add(window_box)

    offset_input = create_value_input(
        window_box,
        "Offset",
        0,
        horizontal_spacing,
        vertical_spacing)
    spacing_input = create_value_input(
        window_box,
        "Spacing",
        0,
        horizontal_spacing,
        vertical_spacing)

    pick_file_btn = gtk.Button("Export tileset");
    pick_file_btn.connect('clicked', pick_file, offset_input, spacing_input, _image)
    window_box.pack_start(pick_file_btn, True, True, vertical_spacing)

    window.show_all()

def close_plugin_window(ret):
    pdb.gimp_message("Plugin exit point")
    gtk.main_quit()

def spritesheetize_plugin_entry(_image, _drawable):
    pdb.gimp_message("Plugin entry point")

    build_gui(_image)
    
    gtk.main()

######################
##### Run script #####
######################

register(
          "spritesheetize_plugin_entry",
          "Plugin for exporting animation spritesheets",
          "Plugin for exporting animation spritesheets",
          "doomista",
          "Apache 2 license",
          "2022",
          "Spritesheetize",
          "*",
          [
              (PF_IMAGE, "image", "Input image", None),
              (PF_DRAWABLE, "drawable", "Input drawable", None),
          ],
          [],
          spritesheetize_plugin_entry, menu="<Image>/Tools/Pixel Art")
main()

