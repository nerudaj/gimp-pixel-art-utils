#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject
import atk
import math
import json

def export_annotations(filename, offset, spacing, tile_width, tile_height, count, items_per_row, nrows):
    pdb.gimp_message("Exporting annotations")
    
    annotation = {
        "offset": offset,
        "spacing": spacing,
        "tile_size": {
            "width": tile_width, 
            "height": tile_height
        },
        "ntiles": count,
        "tiles_per_row": items_per_row,
        "bounds": {
            "left": offset,
            "top": offset,
            "width": items_per_row * tile_width + (items_per_row - 1) * spacing,
            "height": nrows * tile_height + (nrows - 1) * spacing
        }
    }
    
    filename = filename + ".json"
    fp = open(filename, "wt")
    json.dump(annotation, fp)
    fp.close()

def export_tileset(filename, offset, spacing, _image, invert_order):
    pdb.gimp_message("Exporting tileset to {}".format(filename))

    n_layers = len(_image.layers)
    n_tiles_per_row = int(math.sqrt(n_layers))
    n_rows = n_layers / n_tiles_per_row
    if n_tiles_per_row % n_layers != 0:
        n_rows += 1 # There are some extra tiles

    output_width = n_tiles_per_row * _image.width + spacing * (n_tiles_per_row - 1) + offset * 2
    output_height = n_rows * _image.height + spacing * (n_rows - 1) + offset * 2

    img = pdb.gimp_image_new(
        output_width,
        output_height,
        _image.base_type);
        
    pdb.gimp_message("num of layers {}".format(len(img.layers)))
    
    layers = _image.layers[::-1] if invert_order else _image.layers
    x = 0
    y = 0
    for layer in layers:
        temp_layer = pdb.gimp_layer_new_from_drawable(
            layer, img)
        pdb.gimp_layer_add_alpha(temp_layer)
        img.insert_layer(temp_layer)
        temp_layer.translate(
            offset + x * (_image.width + spacing),
            offset + y * (_image.height + spacing))

        x += 1
        if x == n_tiles_per_row:
            x = 0
            y += 1

    result = pdb.gimp_image_merge_visible_layers(img, 0)
    pdb.gimp_file_save(img, result, filename, filename)
    export_annotations(
        filename,
        offset,
        spacing,
        _image.width,
        _image.height,
        n_layers,
        n_tiles_per_row,
        n_rows)

    close_plugin_window(0)

def pick_file(widget, offset_input, spacing_input, order_combo, _image):
    save_dlg = gtk.FileChooserDialog(
        "Filename", 
        None, 
        gtk.FILE_CHOOSER_ACTION_SAVE,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        
    response = save_dlg.run()    
    save_filename = save_dlg.get_filename() # null if cancelled
    save_dlg.destroy()
    
    invert_order = order_combo.get_active_text() == "Bottom to up"
    
    if save_filename is not None:
        export_tileset(
            save_filename,
            int(offset_input.get_text()),
            int(spacing_input.get_text()),
            _image,
            invert_order)

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
    window.set_title("Tilesetize")
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
    
    # Order selection
    order_box = gtk.HBox()
    window_box.pack_start(order_box, True, True, vertical_spacing)
    
    order_combo_label = gtk.Label("Layer order")
    order_box.pack_start(order_combo_label, True, True, horizontal_spacing)
    
    order_combo = gtk.combo_box_new_text()
    for order in [ "Top to bottom", "Bottom to up" ]:
        order_combo.append_text(order)
    order_combo.set_active(0)
    order_box.pack_start(order_combo, True, True, horizontal_spacing)
    
    pick_file_btn = gtk.Button("Export tileset");
    pick_file_btn.connect('clicked', pick_file, offset_input, spacing_input, order_combo, _image)
    window_box.pack_start(pick_file_btn, True, True, vertical_spacing)

    window.show_all()

def close_plugin_window(ret):
    pdb.gimp_message("Plugin exit point")
    gtk.main_quit()

def tilesetize_plugin_entry(_image, _drawable):
    pdb.gimp_message("Plugin entry point")

    build_gui(_image)
    
    gtk.main()

######################
##### Run script #####
######################

register(
          "tilesetize_plugin_entry",
          "Plugin for exporting tilesets",
          "Plugin for exporting tilesets",
          "doomista",
          "Apache 2 license",
          "2022",
          "Tilesetize",
          "*",
          [
              (PF_IMAGE, "image", "Input image", None),
              (PF_DRAWABLE, "drawable", "Input drawable", None),
          ],
          [],
          tilesetize_plugin_entry, menu="<Image>/Tools/Pixel Art")
main()

