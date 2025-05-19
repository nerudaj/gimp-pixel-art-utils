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
import math

plug_in_proc = "plug-in-nerudaj-spritesheetize"
plug_in_binary = "py3-spritesheetize"
plug_in_author = "nerudaj"
plug_in_org = "Pixel Art Utils"
plug_in_year = "2025"
plug_in_docs = "Export layers as spritesheet / tilesheet"
plug_in_name = "Spritesheetize"
plug_in_path = "<Image>/Pixel Art"

def log(message: str):
    proc = Gimp.get_pdb().lookup_procedure("gimp-message")
    config = proc.create_config()
    config.set_property("message", message)
    proc.run(config)

def create_dialog_with_all_procedure_params(procedure: Gimp.Procedure, config):
    # Render UI
    GimpUi.init(plug_in_binary)

    dialog = GimpUi.ProcedureDialog.new(procedure, config, plug_in_name)
    dialog.fill()

    if not dialog.run():
        dialog.destroy()
        return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, None)
    else:
        dialog.destroy()

def copy_layer_to_image(layer: Gimp.Layer,
                        target_image: Gimp.Image,
                        x: int, y: int):
    temp_layer = Gimp.Layer.new_from_drawable(layer, target_image)
    temp_layer.set_visible(True)
    temp_layer.add_alpha()

    target_image.insert_layer(temp_layer, None, 0)
    temp_layer.transform_translate(x, y)

def get_tileset_row_count(layer_count: int) -> tuple[int, int]:
    n_tiles_per_row = int(round(math.sqrt(layer_count)))
    n_rows = int(layer_count / n_tiles_per_row)
    if (n_tiles_per_row * n_rows) % layer_count != 0:
        n_rows += 1 # There are some extra tiles
    return (n_tiles_per_row, n_rows)

def tilesetize(image: Gimp.Image,
               xoffset: int, yoffset: int,
               xspacing: int, yspacing: int):
    layers = image.get_layers()

    (tiles_per_row, row_count) = get_tileset_row_count(len(layers))
    
    framew = image.get_width()
    frameh = image.get_height()
    
    out_image = Gimp.Image.new(
        tiles_per_row * framew + 2 * xoffset + (tiles_per_row - 1) * xspacing,
        row_count * frameh + 2 * yoffset + (row_count - 1) * yspacing,
        image.get_base_type())
    
    for idx in range(0, len(layers)):
        copy_layer_to_image(layers[idx],
                            out_image,
                            xoffset + (idx % tiles_per_row) * (framew + xspacing),
                            yoffset + math.floor(idx / tiles_per_row) * (frameh + yspacing))
        
    return out_image

def spritify_run(procedure: Gimp.Procedure,
                 run_mode: Gimp.RunMode,
                 image: Gimp.Image,
                 drawables,
                 config,
                 data):
    if run_mode == Gimp.RunMode.INTERACTIVE:
        create_dialog_with_all_procedure_params(procedure, config)

    outfile = config.get_property("outfile")
    do_spritesheetize = config.get_property("groups-are-animations")
    xoffset = config.get_property("xoffset")
    yoffset = config.get_property("yoffset")
    xspacing = config.get_property("xspacing")
    yspacing = config.get_property("yspacing")

    out_image = None
    if do_spritesheetize:
        a = 1
    else:
        out_image = tilesetize(image,
                               xoffset, yoffset,
                               xspacing, yspacing)

    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE,
                   out_image,
                   outfile,
                   None)

    # TODO: export annotations

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

class Spritify (Gimp.PlugIn):
    def do_query_procedures(self):
        return [ plug_in_proc ]

    def do_create_procedure(self, name: str):
        print("test")
        if name != plug_in_proc:
            return None

        procedure = Gimp.ImageProcedure.new(self,
                                            name,
                                            Gimp.PDBProcType.PLUGIN,
                                            spritify_run,
                                            None)

        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE |
                                       Gimp.ProcedureSensitivityMask.NO_DRAWABLES)
        procedure.set_menu_label(plug_in_name)
        procedure.set_attribution(plug_in_author, plug_in_org, plug_in_year)
        procedure.add_menu_path(plug_in_path)
        procedure.set_documentation(plug_in_docs, None)

        # Add arguments
        # TODO: detect whether current image has layer groups
        procedure.add_file_argument("outfile",
                                    "Choose output file",
                                    None,
                                    Gimp.FileChooserAction.SAVE,
                                    False,
                                    None,
                                    GObject.ParamFlags.READWRITE)
        
        procedure.add_boolean_argument("groups-are-animations",
                                       "Layer groups are animation clips",
                                       None,
                                       False,
                                       GObject.ParamFlags.READWRITE)

        procedure.add_int_argument("xoffset",
                                    "Horizontal padding",
                                    None,
                                    0,
                                    1024,
                                    0,
                                    GObject.ParamFlags.READWRITE)

        procedure.add_int_argument("yoffset",
                                    "Vertical padding",
                                    None,
                                    0,
                                    1024,
                                    0,
                                    GObject.ParamFlags.READWRITE)

        procedure.add_int_argument("xspacing",
                                    "Horizontal spacing",
                                    None,
                                    0,
                                    1024,
                                    0,
                                    GObject.ParamFlags.READWRITE)

        procedure.add_int_argument("yspacing",
                                    "Vertical spacing",
                                    None,
                                    0,
                                    1024,
                                    0,
                                    GObject.ParamFlags.READWRITE)

        return procedure

Gimp.main(Spritify.__gtype__, sys.argv)
