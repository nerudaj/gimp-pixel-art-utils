#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject
import atk
import math
import json

def export_annotations(filename, offset, spacing, tile_width, tile_height, count, items_per_row, nrows):
    pdb.gimp_message("export_annotations({}, {}, {})".format(filename, offset, spacing))

def export_spritesheet(filename, offset, spacing, image):
    pdb.gimp_message("export_spritesheet({}, {}, {})".format(filename, offset, spacing))

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

