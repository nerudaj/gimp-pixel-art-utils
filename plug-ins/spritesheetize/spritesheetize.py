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
import json

from typing import Self

plug_in_proc = "plug-in-nerudaj-spritesheetize"
plug_in_binary = "py3-spritesheetize"
plug_in_author = "nerudaj"
plug_in_org = "Pixel Art Utils"
plug_in_year = "2025"
plug_in_docs = "Export layers as spritesheet / tilesheet"
plug_in_name = "Spritesheetize"
plug_in_path = "<Image>/Pixel Art"

class Vector2d:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
    
    def get_scaled(self, factor: int) -> Self:
        return Vector2d(self.x * factor, self.y * factor)
    
    def to_json_dim(self) -> dict[str, int]:
        return {
            "width": int(self.x),
            "height": int(self.y)
        }

    def to_json_dist(self)-> dict[str, int]:
        return {
            "horizontal": int(self.x),
            "vertical": int(self.y)
        }

class Box:
    def __init__(self, position: Vector2d, size: Vector2d):
        self.position = position
        self.size = size

    def to_json(self) -> dict[str, int]:
        return {
            "left": int(self.position.x),
            "top": int(self.position.y),
            "width": int(self.size.x),
            "height": int(self.size.y)
        }

class ExportOptions:
    def __init__(self,
                 offset: Vector2d,
                 spacing: Vector2d,
                 upscale_factor: int,
                 invert_clips: bool,
                 enforce_tiles_per_row: bool,
                 enforced_column_count: int):
        self.offset = offset
        self.spacing = spacing
        self.scaling_factor = upscale_factor
        self.invert_clips = invert_clips
        self.enforce_tiles_per_row = enforce_tiles_per_row
        self.enforced_column_count = enforced_column_count

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

    if not temp_layer.is_group():
        temp_layer.add_alpha()

    target_image.insert_layer(temp_layer, None, 0)
    temp_layer.transform_translate(x, y)

def write_obj_to_file_as_json(obj, filename: str):
    fp = open(filename, "wt")
    json.dump(obj, fp, indent=4)
    fp.close()

def export_tileset_annotations(filename: str,
                               frame_size: Vector2d,
                               options: ExportOptions,
                               items_per_row: int,
                               nrows: int):
    bounds_width = int((items_per_row * frame_size.x + (items_per_row - 1) * options.spacing.x) * options.scaling_factor)
    bounds_height = int((nrows * frame_size.y + (nrows - 1) * options.spacing.y) * options.scaling_factor)

    annotation = {
        "frame": frame_size.get_scaled(options.scaling_factor).to_json_dim(),
        "spacing": options.spacing.get_scaled(options.scaling_factor).to_json_dist(),
        "bounds": Box(options.offset.get_scaled(options.scaling_factor),
                      Vector2d(bounds_width, bounds_height)).to_json()
    }

    write_obj_to_file_as_json(annotation, filename + ".clip")

def export_spritesheet_annotations(filename: str,
                                   frame_size: Vector2d,
                                   options: ExportOptions,
                                   fitted_groups: list[list[Gimp.GroupLayer]]):
    annotation = {
        "defaults": {
            "frame": frame_size.get_scaled(options.scaling_factor).to_json_dim(),
            "spacing": frame_size.get_scaled(options.scaling_factor).to_json_dist(),
        },
        "states": []
    }

    for rowIdx in range(len(fitted_groups)):
        startColumnIdx = 0
        for group in fitted_groups[rowIdx]:
            group_len = len(group.get_children())
            annotation["states"].append({
                "name": group.get_name(),
                "bounds": Box(Vector2d(options.offset.x + startColumnIdx * (options.spacing.x + frame_size.x),
                                       options.offset.y + rowIdx * (options.spacing.y + frame_size.y)).get_scaled(options.scaling_factor),
                              Vector2d(group_len * frame_size.x + (group_len - 1) * options.spacing.x,
                                       frame_size.y).get_scaled(options.scaling_factor)).to_json(),
                "nframes": len(group.get_children())
            })

            startColumnIdx += group_len
    
    write_obj_to_file_as_json(annotation, filename + ".anim")

def get_tileset_row_count(layer_count: int) -> tuple[int, int]:
    n_tiles_per_row = int(round(math.sqrt(layer_count)))
    n_rows = int(layer_count / n_tiles_per_row)
    if (n_tiles_per_row * n_rows) % layer_count != 0:
        n_rows += 1 # There are some extra tiles
    return (n_tiles_per_row, n_rows)

def create_out_image(in_image: Gimp.Image, options: ExportOptions, tiles_per_row: int, row_count: int) -> Gimp.Image:
    return Gimp.Image.new(tiles_per_row * in_image.get_width() + 2 * options.offset.x + (tiles_per_row - 1) * options.spacing.x,
                          row_count * in_image.get_height() + 2 * options.offset.y + (row_count - 1) * options.spacing.y,
                          in_image.get_base_type())

def tilesetize(image: Gimp.Image,
               options: ExportOptions) -> tuple[Gimp.Image, int, int]:
    layers = image.get_layers()

    (tiles_per_row, row_count) = get_tileset_row_count(len(layers))
    
    out_image = create_out_image(image, options, tiles_per_row, row_count)
    
    for idx in range(0, len(layers)):
        columnIdx = idx % tiles_per_row
        rowIdx = math.floor(idx / tiles_per_row)
        copy_layer_to_image(layers[idx],
                            out_image,
                            options.offset.x + columnIdx * (image.get_width() + options.spacing.x),
                            options.offset.y + rowIdx * (image.get_height() + options.spacing.y))
    
    Gimp.context_set_interpolation(Gimp.InterpolationType.NONE)
    out_image.scale(out_image.get_width() * options.scaling_factor,
                    out_image.get_height() * options.scaling_factor)

    return (out_image, tiles_per_row, row_count)

def get_next_best_fitting_group(groups: list[Gimp.GroupLayer],
                                max_tiles_per_row: int,
                                currently_used_tiles: int) -> Gimp.GroupLayer | None:
    target_score = max_tiles_per_row - currently_used_tiles
    score = -1
    best_idx = -1
    for idx in range(len(groups)):
        current_score = len(groups[idx].get_children())
        if current_score > target_score:
            continue

        if score == -1 or score < current_score:
            score = current_score
            best_idx = idx
    
    if best_idx != -1:
        result = groups.pop(best_idx)
        return result
    
    return None

def fit_groups(groups: list[Gimp.GroupLayer]) -> list[list[Gimp.GroupLayer]]:
    group_lens = list(len(g.get_children()) for g in groups)
    max_group_len = max(group_lens)

    rows: list[list[Gimp.GroupLayer]] = [[]]
    current_row_idx = 0
    current_row_usage = 0
    while len(groups) > 0:
        group = get_next_best_fitting_group(groups, max_group_len, current_row_usage)
        if group is None:
            rows.append(list())
            current_row_idx += 1
            current_row_usage = 0
            continue

        rows[current_row_idx].append(group)
        current_row_usage += len(group.get_children())

    return rows

def spritesheetize(image: Gimp.Image,
                   options: ExportOptions) -> tuple[Gimp.Image, list[list[Gimp.GroupLayer]]]:
    groups: list[Gimp.GroupLayer] = list(filter(lambda x: x.is_group_layer(), image.get_layers()))

    if len(groups) == 0:
        log("No groups to export!")
        return (None, [])

    fitted_groups = fit_groups(groups)
    tiles_per_row = len(fitted_groups[0][0].get_children()) # First row always contains the longest animation
    row_count = len(fitted_groups)

    out_image = create_out_image(image, options, tiles_per_row, row_count)

    for rowIdx in range(len(fitted_groups)):
        columnIdx = 0
        for group in fitted_groups[rowIdx]:
            for layer in group.get_children():
                copy_layer_to_image(layer,
                                    out_image,
                                    options.offset.x + columnIdx * (image.get_width() + options.spacing.x),
                                    options.offset.y + rowIdx * (image.get_height() + options.spacing.y))
                columnIdx += 1
    
    Gimp.context_set_interpolation(Gimp.InterpolationType.NONE)
    out_image.scale(out_image.get_width() * options.scaling_factor,
                    out_image.get_height() * options.scaling_factor)

    return (out_image, fitted_groups)


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

    options = ExportOptions(Vector2d(config.get_property("xoffset"),
                                     config.get_property("yoffset")),
                            Vector2d(config.get_property("xspacing"),
                                     config.get_property("yspacing")),
                            config.get_property("upscale-factor"),
                            False)


    if do_spritesheetize:
        (out_image, fitted_groups) = spritesheetize(image, options)

        if out_image is None:
            return procedure.new_return_values(Gimp.PDBStatusType.EXECUTION_ERROR, None)
        
        export_spritesheet_annotations(outfile.get_path(),
                                       Vector2d(image.get_width(), image.get_height()),
                                       options,
                                       fitted_groups)

    else:
        (out_image, tiles_per_row, row_count) = tilesetize(image, options)
        export_tileset_annotations(outfile.get_path(),
                                   Vector2d(image.get_width(), image.get_height()),
                                   options,
                                   tiles_per_row, row_count)

    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE,
                   out_image,
                   outfile,
                   None)
    
    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

class Spritify (Gimp.PlugIn):
    def do_query_procedures(self):
        return [ plug_in_proc ]

    def do_create_procedure(self, name: str):
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

        procedure.add_file_argument("outfile",
                                    "Choose output file",
                                    None,
                                    Gimp.FileChooserAction.SAVE,
                                    False,
                                    None,
                                    GObject.ParamFlags.READWRITE)
        
        procedure.add_boolean_argument("groups-are-animations",
                                       "Export layer groups as animation clips",
                                       None,
                                       False,
                                       GObject.ParamFlags.READWRITE)
        
        procedure.add_int_argument("upscale-factor",
                                    "Upscale factor",
                                    None,
                                    1,
                                    16,
                                    1,
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
