#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gegl
import sys

plug_in_proc = "plug-in-nerudaj-load-as-tiles"
plug_in_binary = "py3-load-as-tiles"
plug_in_author = "nerudaj"
plug_in_org = "Pixel Art Utils"
plug_in_year = "2025"
plug_in_docs = "Load an image and break it into tiles"
plug_in_name = "Load as tiles"
plug_in_path = "<Image>/Pixel Art"

def log(message: str):
    proc = Gimp.get_pdb().lookup_procedure("gimp-message")
    config = proc.create_config()
    config.set_property("message", message)
    proc.run(config)

def create_dialog_with_all_procedure_params(procedure, config):
    # Render UI
    GimpUi.init(plug_in_binary)

    dialog = GimpUi.ProcedureDialog.new(procedure, config, plug_in_name)
    frame_box = dialog.fill_box("frame-box", ["frame-width", "frame-height"])
    frame_box.set_orientation (Gtk.Orientation.HORIZONTAL)
    offset_box = dialog.fill_box("offset-box", ["xoffset", "yoffset"])
    offset_box.set_orientation (Gtk.Orientation.HORIZONTAL)
    spacing_box = dialog.fill_box("spacing-box", ["xspacing", "yspacing"])
    spacing_box.set_orientation (Gtk.Orientation.HORIZONTAL)
    dialog.fill_frame("dimensions-frame", "frame-width", False, "frame-box")
    dialog.fill_frame("dimensions-offset", "xoffset", False, "offset-box")
    dialog.fill_frame("dimensions-spacing", "xspacing", False, "spacing-box")
    dialog.fill(["infile", "dimensions-frame", "dimensions-offset", "dimensions-spacing"])

    if not dialog.run():
        dialog.destroy()
        return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, None)
    else:
        dialog.destroy()

def copy_area_between_images(source_image: Gimp.Image, destination_image: Gimp.Image, rect: Gegl.Rectangle, layer_name: str):
    layer = Gimp.Layer.new(destination_image,
                           layer_name,
                           rect.width,
                           rect.height,
                           destination_image.get_base_type(),
                           100,
                           Gimp.LayerMode.NORMAL)
    layer.add_alpha()
    destination_image.insert_layer(layer, None, 0)

    source_image.select_rectangle(Gimp.ChannelOps.REPLACE,
                                 rect.x,
                                 rect.y,
                                 rect.width,
                                 rect.height)

    Gimp.edit_copy([source_image.get_layers()[0]])
    sel = Gimp.edit_paste(layer, True)
    for sl in sel:
        Gimp.floating_sel_attach(sl, layer)
        Gimp.floating_sel_remove(sl)

def load_as_tiles_run(procedure, run_mode, image, drawables, config, data):
    if run_mode == Gimp.RunMode.INTERACTIVE:
        create_dialog_with_all_procedure_params(procedure, config)

    infile = config.get_property("infile")
    framew = config.get_property("frame-width")
    frameh = config.get_property("frame-height")
    xoffset = config.get_property("xoffset")
    yoffset = config.get_property("yoffset")
    xspacing = config.get_property("xspacing")
    yspacing = config.get_property("yspacing")

    input_image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, infile)

    if input_image is None:
        return procedure.new_return_values (Gimp.PDBStatusType.CALLING_ERROR,
                                            GLib.Error(f"Could not load image {infile}"))

    in_w = input_image.get_width()
    in_h = input_image.get_height()
    y = yoffset
    idx = 0
    while y < in_h:
        x = xoffset
        while x < in_w:
            copy_area_between_images(input_image,
                                     image,
                                     Gegl.Rectangle.new(x, y, framew, frameh),
                                     f"layer_{idx}")

            idx = idx + 1
            x = x + framew + xspacing
        
        y = y + frameh + yspacing

    Gimp.displays_flush()
    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

class LoadAsTiles (Gimp.PlugIn):
    def do_query_procedures(self):
        return [ plug_in_proc ]

    def do_create_procedure(self, name):
        if name != plug_in_proc:
            return None

        procedure = Gimp.ImageProcedure.new(self,
                                            name,
                                            Gimp.PDBProcType.PLUGIN,
                                            load_as_tiles_run,
                                            None)

        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE |
                                       Gimp.ProcedureSensitivityMask.NO_DRAWABLES)
        procedure.set_menu_label(plug_in_name)
        procedure.set_attribution(plug_in_author, plug_in_org, plug_in_year)
        procedure.add_menu_path(plug_in_path)
        procedure.set_documentation(plug_in_docs, None)

        procedure.add_file_argument("infile",
                                    "Input file",
                                    None,
                                    Gimp.FileChooserAction.OPEN,
                                    False,
                                    None,
                                    GObject.ParamFlags.READWRITE)

        procedure.add_int_argument("frame-width",
                                    "Frame width",
                                    None,
                                    0,
                                    1024,
                                    32,
                                    GObject.ParamFlags.READWRITE)

        procedure.add_int_argument("frame-height",
                                    "Frame height",
                                    None,
                                    0,
                                    1024,
                                    32,
                                    GObject.ParamFlags.READWRITE)

        procedure.add_int_argument("xoffset",
                                    "X offset",
                                    None,
                                    0,
                                    1024,
                                    0,
                                    GObject.ParamFlags.READWRITE)

        procedure.add_int_argument("yoffset",
                                    "Y offset",
                                    None,
                                    0,
                                    1024,
                                    0,
                                    GObject.ParamFlags.READWRITE)

        procedure.add_int_argument("xspacing",
                                    "X spacing",
                                    None,
                                    0,
                                    1024,
                                    0,
                                    GObject.ParamFlags.READWRITE)

        procedure.add_int_argument("yspacing",
                                    "X spacing",
                                    None,
                                    0,
                                    1024,
                                    0,
                                    GObject.ParamFlags.READWRITE)


        return procedure

Gimp.main(LoadAsTiles.__gtype__, sys.argv)
