#! /usr/bin/python

from gimpfu import *
import gtk
import gimpui
import gobject

def build_gui():
    pdb.gimp_message("build_gui")

    horizontal_spacing = 10
    vertical_spacing = 0

    window = gtk.Window()
    window.set_title("Plugin template")
    window.connect('destroy',  close_plugin_window)
    window_box = gtk.VBox()
    window.add(window_box)
    window.set_keep_above(True)

#    display_box = gtk.HBox()
#    window_box.pack_start(display_box, True, True, vertical_spacing)

    window.show_all()


def close_plugin_window(ret):
    pdb.gimp_message("Plugin exit point")
    gtk.main_quit()

def template_plugin_entry(_image, _drawable):
    pdb.gimp_message("Plugin entry point")

    build_gui()
    
    gtk.main()

######################
##### Run script #####
######################

register(
          "template_plugin_entry",
          "Description",
          "Description",
          "doomista",
          "Apache 2 license",
          "2022",
          "Template",
          "*",
          [
              (PF_IMAGE, "image", "Input image", None),
              (PF_DRAWABLE, "drawable", "Input drawable", None),
          ],
          [],
          template_plugin_entry, menu="<Image>/Tools/Pixel Art")
main()

