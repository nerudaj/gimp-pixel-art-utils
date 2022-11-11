#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject
import atk
import math
import json

# GUI HELPERS
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
    combo.set_active(0)
    
    box.pack_start(combo, True, True, spacing)
    return combo

# GENERIC HELPERS
def write_obj_to_file_as_json(obj, filename):
    #pdb.gimp_message("write_obj_to_file_as_json({}, {})".format(obj, filename))
    fp = open(filename, "wt")
    json.dump(obj, fp, indent=4)
    fp.close()

# Tilesetize
def export_tileset_annotations(filename, offset, spacing, tile_width, tile_height, count, items_per_row, nrows):
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
    write_obj_to_file_as_json(annotation, filename + ".json")

def export_tileset(filename, _image, offset, spacing, invert_order):
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

        if len(layer.children) == 0: # Cannot add alpha for layer group
            pdb.gimp_layer_add_alpha(temp_layer)

        pdb.gimp_drawable_set_visible(temp_layer, True)
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
    export_tileset_annotations(
        filename,
        offset,
        spacing,
        _image.width,
        _image.height,
        n_layers,
        n_tiles_per_row,
        n_rows)

## Spritesheetize
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
        if frame_count == 0:
            continue

        layer_refs.append((layer, frame_count))
        frame_sum += frame_count

    return pack_layers(layer_refs, frame_sum)

def export_spritesheet_annotations(filename, offset, spacing, frame_width, frame_height, packed_layers):
    pdb.gimp_message("export_annotations({}, {}, {})".format(filename, offset, spacing))

    annotation = {
        "defaults": {
            "frame": {
                "width": frame_width,
                "height": frame_height
            },
            "spacing": {
                "horizontal": spacing,
                "vertical": spacing
            }
        },
        "states": []
    }

    row = 0
    col = 0
    for packed_row in packed_layers:
        for state in packed_row:
            pdb.gimp_message(state)
            annotation["states"].append({
                "name": state[0].name,
                "bounds": {
                    "left": offset + (frame_width + spacing) * col,
                    "top": offset + (frame_height + spacing) * row,
                    "width": frame_width * state[1] + spacing * (state[1] - 1),
                    "height": frame_height
                },
                "nframes": state[1]
            })
            col += state[1]
        col = 0
        row += 1

    write_obj_to_file_as_json(annotation, filename + ".json")

def export_spritesheet(filename, image, offset, spacing):
    pdb.gimp_message("export_spritesheet({}, {}, {})".format(filename, offset, spacing))
    packed_layers = compute_packed_layers(image)
    
    max_frames_per_row = 0
    for lt in packed_layers[0]:
        max_frames_per_row += tuple_second_elem(lt)
    row_count = len(packed_layers)

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
    for packed_row in packed_layers:
        for clip in packed_row:
            left = offset + (image.width + spacing) * col
            top = offset + (image.height + spacing) * row

            clip_len = clip[1]
            col += clip_len

            frames = clip[0].children
            frame_index = 0

            for frame in frames:
                pdb.gimp_drawable_set_visible(frame, True)
                temp_layer = pdb.gimp_layer_new_from_drawable(
                    frame, export_img)
                
                if len(frame.children) == 0: # Cannot add alpha for layer group
                    pdb.gimp_layer_add_alpha(temp_layer)

                pdb.gimp_drawable_set_visible(temp_layer, True)
                export_img.insert_layer(temp_layer)
                temp_layer.translate(
                    left + (clip_len - frame_index - 1) * (image.width + spacing),
                    top)
                frame_index += 1

        col = 0
        row += 1

    result = pdb.gimp_image_merge_visible_layers(export_img, 0)
    pdb.gimp_file_save(export_img, result, filename, filename)

    export_spritesheet_annotations(
        filename,
        offset,
        spacing,
        image.width,
        image.height,
        packed_layers)

# Gui code
def pick_file():
    save_dlg = gtk.FileChooserDialog(
        "Filename", 
        None, 
        gtk.FILE_CHOOSER_ACTION_SAVE,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        
    response = save_dlg.run()    
    save_filename = save_dlg.get_filename() # null if cancelled
    save_dlg.destroy()
    return save_filename

def export_clicked(widget, offset_input, spacing_input, mode_combo, order_combo, image):
    output_filename = pick_file()
    if output_filename is None:
        return

    offset = int(offset_input.get_text())
    spacing = int(spacing_input.get_text())

    spritesheetize = mode_combo.get_active_text() == "Spritesheetize"
    if spritesheetize:
        export_spritesheet(
            output_filename,
            image,
            offset,
            spacing)
    else:
        invert_order = order_combo.get_active_text() == "Bottom to up"
        export_tileset(
            output_filename,
            image,
            offset,
            spacing,
            invert_order)

    close_plugin_window(0)

def build_gui(_image):
    pdb.gimp_message("build_gui")

    horizontal_spacing = 10
    vertical_spacing = 0

    window = gtk.Window()
    window.set_title("Spritesheetize / Tilesetize")
    window.connect('destroy',  close_plugin_window)
    window_box = gtk.VBox()
    window.add(window_box)

    # Some boxes
    main_box = create_hbox(window_box, False)
    labels_box = create_vbox(main_box, True)
    controls_box = create_vbox(main_box, True)
    help_box = create_vbox(window_box, False)

    # Labels
    create_label("Offset", labels_box)
    create_label("Spacing", labels_box)
    create_label("Mode", labels_box)
    create_label("Layer order (tilesize only)", labels_box)

    # Controls
    offset_input = create_value_input(
        0,
        controls_box)
    spacing_input = create_value_input(
        0,
        controls_box)
    mode_combo = create_combo(
        ["Spritesheetize", "Tilesetize"],
        controls_box)
    order_combo = create_combo(
        ["Top to bottom", "Bottom to up"],
        controls_box)

    # Help
    create_label("If your project is a set of individual images, set the mode to Tilesetize.", help_box, 5)
    create_label("If your project is a set of animation clips, leave it on Spritesheetize.", help_box, 5)

    # Submit
    pick_file_btn = create_button("Export", window_box)
    pick_file_btn.connect(
        'clicked',
        export_clicked,
        offset_input,
        spacing_input,
        mode_combo,
        order_combo,
        _image)

    window.show_all()

def close_plugin_window(ret):
    #pdb.gimp_message("Plugin exit point")
    gtk.main_quit()

def spritetilesetize_plugin_entry(_image, _drawable):
    pdb.gimp_message("Plugin entry point")

    build_gui(_image)
    
    gtk.main()

######################
##### Run script #####
######################

register(
          "spritetilesetize_plugin_entry",
          "Plugin for exporting tilesets",
          "Plugin for exporting tilesets",
          "doomista",
          "Apache 2 license",
          "2022",
          "Spritesheetize / Tilesetize",
          "*",
          [
              (PF_IMAGE, "image", "Input image", None),
              (PF_DRAWABLE, "drawable", "Input drawable", None),
          ],
          [],
          spritetilesetize_plugin_entry, menu="<Image>/Tools/Pixel Art")
main()

