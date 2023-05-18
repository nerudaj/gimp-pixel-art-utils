#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject
import atk
import math
import json

def log(message):
    enable_logging = False
    if enable_logging:
        pdb.gimp_message(message)

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
    #log("write_obj_to_file_as_json({}, {})".format(obj, filename))
    fp = open(filename, "wt")
    json.dump(obj, fp, indent=4)
    fp.close()

def add_offsets_to_image(img):
    # Just having image to include offsets is not enough, there has to be
    # invisible layer as big as the image in order to get offsets in the
    # exported result
    offset_layer = pdb.gimp_layer_new(img, img.width, img.height, 0, "", 0, 0)
    img.insert_layer(offset_layer);

# Tilesetize
def export_tileset_annotations(filename, offset, spacing, upscale_factor, tile_width, tile_height, count, items_per_row, nrows):
    log("Exporting annotations")
    
    annotation = {
        "offset": int(offset * upscale_factor),
        "spacing": {
            "horizontal": int(spacing * upscale_factor),
            "vertical": int(spacing * upscale_factor)
        },
        "frame": {
            "width": int(tile_width * upscale_factor),
            "height": int(tile_height * upscale_factor)
        },
        "nframes": count,
        "tiles_per_row": items_per_row,
        "bounds": {
            "left": int(offset * upscale_factor),
            "top": int(offset * upscale_factor),
            "width": int((items_per_row * tile_width + (items_per_row - 1) * spacing) * upscale_factor),
            "height": int((nrows * tile_height + (nrows - 1) * spacing) * upscale_factor)
        }
    }
    write_obj_to_file_as_json(annotation, filename + ".clip")

def get_tileset_row_count(layer_count):
    n_tiles_per_row = int(round(math.sqrt(layer_count)))
    n_rows = int(layer_count / n_tiles_per_row)
    if (n_tiles_per_row * n_rows) % layer_count != 0:
        n_rows += 1 # There are some extra tiles
    return (n_tiles_per_row, n_rows)

def export_tileset(filename, _image, offset, spacing, upscale_factor, invert_order):
    log("export_tileset({}, {}, {}, {})".format(filename, offset, spacing, upscale_factor))

    n_layers = len(_image.layers)
    (n_tiles_per_row, n_rows) = get_tileset_row_count(n_layers)

    output_width = n_tiles_per_row * _image.width + spacing * (n_tiles_per_row - 1) + offset * 2
    output_height = n_rows * _image.height + spacing * (n_rows - 1) + offset * 2

    img = pdb.gimp_image_new(
        int(output_width * upscale_factor),
        int(output_height * upscale_factor),
        _image.base_type);
    
    pdb.gimp_context_set_interpolation(0)
    add_offsets_to_image(img)
    
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
        pdb.gimp_layer_scale(
            temp_layer,
            _image.width * upscale_factor,
            _image.height * upscale_factor,
            False)
        temp_layer.translate(
            int((offset + x * (_image.width + spacing)) * upscale_factor),
            int((offset + y * (_image.height + spacing)) * upscale_factor))

        x += 1
        if x == n_tiles_per_row:
            x = 0
            y += 1

    final_layer = pdb.gimp_image_merge_visible_layers(img, 0)
    pdb.gimp_file_save(img, final_layer, filename, filename)

    export_tileset_annotations(
        filename,
        offset,
        spacing,
        upscale_factor,
        _image.width,
        _image.height,
        n_layers,
        n_tiles_per_row,
        n_rows)

## Spritesheetize
def tuple_second_elem(lt):
    return lt[1];

def pack_layers(layers, frame_sum):
    log("pack_layers({}, {})"
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
    log("compute_packed_layers({})"
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

def export_spritesheet_annotations(filename, offset, spacing, upscale_factor, frame_width, frame_height, packed_layers):
    log("export_annotations({}, {}, {})".format(filename, offset, spacing))

    annotation = {
        "defaults": {
            "frame": {
                "width": int(frame_width * upscale_factor),
                "height": int(frame_height * upscale_factor)
            },
            "spacing": {
                "horizontal": int(spacing * upscale_factor),
                "vertical": int(spacing * upscale_factor)
            }
        },
        "states": []
    }

    row = 0
    col = 0
    for packed_row in packed_layers:
        for state in packed_row:
            log(state)
            annotation["states"].append({
                "name": state[0].name,
                "bounds": {
                    "left": int((offset + (frame_width + spacing) * col) * upscale_factor),
                    "top": int((offset + (frame_height + spacing) * row) * upscale_factor),
                    "width": int((frame_width * state[1] + spacing * (state[1] - 1)) * upscale_factor),
                    "height": int(frame_height * upscale_factor)
                },
                "nframes": state[1]
            })
            col += state[1]
        col = 0
        row += 1

    write_obj_to_file_as_json(annotation, filename + ".anim")

def export_spritesheet(filename, image, offset, spacing, upscale_factor):
    log("export_spritesheet({}, {}, {})".format(filename, offset, spacing))
    packed_layers = compute_packed_layers(image)
    
    max_frames_per_row = 0
    for lt in packed_layers[0]:
        max_frames_per_row += tuple_second_elem(lt)
    row_count = len(packed_layers)

    output_width = image.width * max_frames_per_row + spacing * (1 - max_frames_per_row) + offset * 2
    output_height = image.height * row_count + spacing * (1 - row_count) + offset * 2
    log("Image output dimensions: {}x{}"
        .format(output_width, output_height))
    
    export_img = pdb.gimp_image_new(
        int(output_width * upscale_factor),
        int(output_height * upscale_factor),
        image.base_type)

    pdb.gimp_context_set_interpolation(0)
    add_offsets_to_image(export_img)

    row = 0
    col = 0
    for packed_row in packed_layers:
        for clip in packed_row:
            left = int((offset + (image.width + spacing) * col) * upscale_factor)
            top = int((offset + (image.height + spacing) * row) * upscale_factor)

            clip_len = clip[1]
            col += clip_len

            frames = clip[0].children
            frame_index = 0

            for frame in frames:
                temp_layer = pdb.gimp_layer_new_from_drawable(
                    frame, export_img)
                
                if len(frame.children) == 0: # Cannot add alpha for layer group
                    pdb.gimp_layer_add_alpha(temp_layer)

                pdb.gimp_drawable_set_visible(temp_layer, True)

                export_img.insert_layer(temp_layer)
                pdb.gimp_layer_scale(
                    temp_layer,
                    int(image.width * upscale_factor),
                    int(image.height * upscale_factor),
                    False)
                temp_layer.translate(
                    left + int(((clip_len - frame_index - 1) * (image.width + spacing)) * upscale_factor),
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
        upscale_factor,
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

def export_clicked(widget, offset_input, spacing_input, upscale_input, mode_combo, order_combo, image):
    output_filename = pick_file()
    if output_filename is None:
        return

    offset = int(offset_input.get_text())
    spacing = int(spacing_input.get_text())
    upscale_factor = float(upscale_input.get_text())

    spritesheetize = mode_combo.get_active_text() == "Spritesheetize"
    if spritesheetize:
        export_spritesheet(
            output_filename,
            image,
            offset,
            spacing,
            upscale_factor)
    else:
        invert_order = order_combo.get_active_text() == "Bottom to up"
        export_tileset(
            output_filename,
            image,
            offset,
            spacing,
            upscale_factor,
            invert_order)

    close_plugin_window(0)

def build_gui(_image):
    log("build_gui")
    
    def predict_mode(image):
        """
        returns 0 for spritesheetize and 1 for tilesetize
        """
        layers_w_children_count = 0
        for layer in image.layers:
            if len(layer.children) > 0:
                layers_w_children_count += 1
        
        return 1 if layers_w_children_count < (len(image.layers) / 2) else 0

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
    create_label("Upscale factor", labels_box)

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
    mode_combo.set_active(predict_mode(_image))
    order_combo = create_combo(
        ["Top to bottom", "Bottom to up"],
        controls_box)
    upscale_input = create_value_input(
        1,
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
        upscale_input,
        mode_combo,
        order_combo,
        _image)

    window.show_all()

def close_plugin_window(ret):
    #log("Plugin exit point")
    gtk.main_quit()

def spritetilesetize_plugin_entry(_image, _drawable):
    log("Plugin entry point")

    test_tileset_dimension_computation()
    build_gui(_image)
    
    gtk.main()

def assert_eq(a, b, msg):
    if (a != b):
        log("{}: Not equal! {} {}".format(msg, a, b))

def test_tileset_dimension_computation():
    (cols1, rows1) = get_tileset_row_count(1)
    assert_eq(cols1, 1, "get_tileset_row_count(1)/cols")
    assert_eq(rows1, 1, "get_tileset_row_count(1)/rows")
    
    (cols2, rows2) = get_tileset_row_count(2)
    assert_eq(cols2, 1, "get_tileset_row_count(2)/cols")
    assert_eq(rows2, 2, "get_tileset_row_count(2)/rows")

    (cols3, rows3) = get_tileset_row_count(3)
    assert_eq(cols3, 2, "get_tileset_row_count(3)/cols")
    assert_eq(rows3, 2, "get_tileset_row_count(3)/rows")

    (cols4, rows4) = get_tileset_row_count(4)
    assert_eq(cols4, 2, "get_tileset_row_count(4)/cols")
    assert_eq(rows4, 2, "get_tileset_row_count(4)/rows")

    (cols5, rows5) = get_tileset_row_count(5)
    assert_eq(cols5, 2, "get_tileset_row_count(5)/cols")
    assert_eq(rows5, 3, "get_tileset_row_count(5)/rows")

    (cols6, rows6) = get_tileset_row_count(6)
    assert_eq(cols6, 2, "get_tileset_row_count(6)/cols")
    assert_eq(rows6, 3, "get_tileset_row_count(6)/rows")

    (cols7, rows7) = get_tileset_row_count(7)
    assert_eq(cols7, 3, "get_tileset_row_count(7)/cols")
    assert_eq(rows7, 3, "get_tileset_row_count(7)/rows")

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

