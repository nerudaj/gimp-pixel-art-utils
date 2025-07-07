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

plug_in_proc = "plug-in-nerudaj-tile-preview"
plug_in_binary = "py3-tile-preview"
plug_in_author = "nerudaj"
plug_in_org = "Pixel Art Utils"
plug_in_year = "2025"
plug_in_docs = "Plugin for previewing how layers appear when tiled."
plug_in_name = "Tile Preview"
plug_in_path = "<Image>/Pixel Art"

class GtkBuilder:
    @staticmethod
    def create_window(title: str) -> Gtk.Window:
        window = Gtk.Window.new(Gtk.WindowType.TOPLEVEL)
        window.set_title(title)
        window.set_keep_above(True)
        return window

    @staticmethod
    def create_vbox(parent: Gtk.Container, padding: int = 0) -> Gtk.Box:
        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        if isinstance(parent, Gtk.Window):
            parent.add(box)
        else:
            parent.pack_start(box, True, False, padding)
        return box

    @staticmethod
    def create_hbox(parent: Gtk.Container, fill: bool = False) -> Gtk.Box:
        box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
        parent.pack_start(box, fill, fill, 0)
        return box

    @staticmethod
    def create_label(text: str, parent: Gtk.Container) -> Gtk.Label:
        label = Gtk.Label.new(text)
        parent.pack_start(label, True, False, 0)
        return label

    @staticmethod
    def create_button(label: str, parent: Gtk.Container) -> Gtk.Button:
        btn = Gtk.Button.new_with_label(label)
        parent.pack_start(btn, True, True, 0)
        return btn

    @staticmethod
    def create_value_input(value: int, parent: Gtk.Container) -> Gtk.Entry:
        input_entry = Gtk.Entry.new()
        input_entry.set_text(f"{value}")
        parent.pack_start(input_entry, False, False, 0)
        return input_entry

    @staticmethod
    def create_combo(values: list, parent: Gtk.Container) -> Gtk.ComboBoxText:
        combo = Gtk.ComboBoxText.new()
        for value in values:
            combo.append_text(value)
        parent.pack_start(combo, True, True, 0)
        return combo

class Dim:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

class RenderMode:
    BLOCK = "Block"
    FLOOR = "Floor"
    COLUMNS = "Columns"
    V_ADJ = "V. Adjacent"

    @staticmethod
    def get_string_annotations():
        return [RenderMode.BLOCK, RenderMode.FLOOR, RenderMode.COLUMNS, RenderMode.V_ADJ]

class GtkContext:
    def __init__(self):
        self.window = None
        self.display_box = None
        self.preview_box = None
        self.temp_img = None
        self.bottom_control_vbox = None
        self.layer_select_combos = [ None, None ]

class PluginContext:
    def __init__(self, image: Gimp.Image):
        self.mode = RenderMode.BLOCK
        self.layer_names = ["", ""]
        self.zoom_level = 1.0
        self.skip_next_update = False
        self.gtk_ctx = GtkContext()
        self.image_ref = image

    def __str__(self):
        return "PreviewContext(mode = {}, zoom = {}, names = {})".format(self.mode, self.zoom_level, self.layer_names)

    def __repr__(self):
        return self.__str__()

class RenderStrategyInterface:
    def copy_layer_to(self, source: Gimp.Layer, destination: Gimp.Image, x: int, y: int):
        def make_layer_visible_with_alpha(layer):
            if len(layer.get_children()) == 0: # Cannot add alpha for layer group
                layer.add_alpha()
            layer.set_visible(True)

        temp_layer = Gimp.Layer.new_from_drawable(source, destination)
        make_layer_visible_with_alpha(temp_layer)
        destination.insert_layer(temp_layer, None, 0)
        temp_layer.transform_translate(x, y)

    def construct_preview(self, target, dim: Dim, layer1, layer2):
        pass

    def get_image_dim(self, dim: Dim, second_layer_is_valid: bool) -> Dim:
        pass

class RenderStrategyBlock(RenderStrategyInterface):
    def construct_preview(self, target, dim: Dim, layer1, layer2):
        for y in range(0, 3):
            for x in range(0, 3):
                use_layer2 = (y != 1 or x != 1) and layer2
                self.copy_layer_to(
                    layer2 if use_layer2 else layer1,
                    target,
                    x * dim.width,
                    y * dim.height)

    def get_image_dim(self, dim: Dim, second_layer_is_valid: bool):
        return Dim(
            int(dim.width * 3.0),
            int(dim.height * 3.0))

class RenderStrategyFloor(RenderStrategyInterface):
    def construct_preview(self, target, dim: Dim, layer1, layer2):
        for x in range(0, 3):
            use_layer2 = (x != 1) and layer2
            self.copy_layer_to(
                layer2 if use_layer2 else layer1,
                target,
                x * dim.width, 0)

    def get_image_dim(self, dim: Dim, second_layer_is_valid: bool):
        return Dim(
            int(dim.width * 3.0),
            int(dim.height))

class RenderStrategyVadj(RenderStrategyInterface):
    def construct_preview(self, target, dim: Dim, layer1, layer2):
        self.copy_layer_to(
            layer1,
            target,
            0, 0)
        if layer2:
            self.copy_layer_to(
                layer2,
                target,
                0, dim.height)

    def get_image_dim(self, dim: Dim, second_layer_is_valid: bool) -> Dim:
        return Dim(
            int(dim.width),
            int(dim.height * 2.0))

class RenderStrategyColumns(RenderStrategyInterface):
    def construct_preview(self, target, dim: Dim, layer1: Gimp.Layer, layer2: Gimp.Layer):
        for y in range(0, 3):
            for x in range(0, 3):
                use_layer2 = (x != 1) and layer2
                self.copy_layer_to(
                    layer2 if use_layer2 else layer1,
                    target,
                    x * dim.width,
                    y * dim.height)

    def get_image_dim(self, dim: Dim, second_layer_is_valid: bool) -> Dim:
        return Dim(
            int(dim.width * (3.0 if second_layer_is_valid else 1.0)),
            int(dim.height * 3.0))

class RenderStrategyFactory():
    @staticmethod
    def get_strategy(mode):
        if mode == RenderMode.BLOCK:
            return RenderStrategyBlock()
        elif mode == RenderMode.V_ADJ:
            return RenderStrategyVadj()
        elif mode == RenderMode.FLOOR:
            return RenderStrategyFloor()
        elif mode == RenderMode.COLUMNS:
            return RenderStrategyColumns()
        else:
            return RenderStrategyInterface()

class ProcedureHelper:
    @staticmethod
    def call_pdb_procedure(name, properties: list[tuple[str, any]]):
        proc = Gimp.get_pdb().lookup_procedure(name)
        config = proc.create_config()
        for prop_name, prop_value in properties:
            config.set_property(prop_name, prop_value)
        proc.run(config)

def log(message: str):
    ProcedureHelper.call_pdb_procedure("gimp-message", [("message", message)])

class ZoomHandler:
    @staticmethod
    def zoom_in(_: Gtk.Widget, context: PluginContext):
        context.zoom_level += 0.1
        update_preview(context, force=True)

    @staticmethod
    def zoom_out(_: Gtk.Widget, context: PluginContext):
        context.zoom_level = max(0.1, context.zoom_level - 0.1)
        update_preview(context, force=True)

    @staticmethod
    def reset_zoom(_: Gtk.Widget, context: PluginContext):
        context.zoom_level = 1.0
        update_preview(context, force=True)

    @staticmethod
    def zoom_to_fit(_: Gtk.Widget, context: PluginContext):
        if not context.gtk_ctx.display_box or not context.image_ref:
            log("DEBUG: Zoom to fit called but display box or image reference is not set.")
            return
        
        img_w = context.image_ref.get_width() * 3
        img_h = context.image_ref.get_height() * 3
        if img_w == 0 or img_h == 0:
            return

        alloc = context.gtk_ctx.display_box.get_allocation()
        margin = 2
        context.zoom_level = min((alloc.width - margin) / img_w,
                                 (alloc.height - margin) / img_h)

        # Prevent zoom from being too small
        context.zoom_level = max(0.1, context.zoom_level)
        update_preview(context, force=True)

def get_preview_image(image_type,
                      dim: Dim,
                      zoom: int,
                      mode: RenderMode,
                      layer1: Gimp.Layer,
                      layer2: Gimp.Layer,
                      gtk_ctx: GtkContext,
                      render_strategy):

    # Compute base image size
    new_image_dim = render_strategy.get_image_dim(dim, layer2)

    # Create temp image that will accomodate new layers
    if gtk_ctx.temp_img:
        #gimp.delete(gtk_ctx.temp_img)
        pass

    gtk_ctx.temp_img = Gimp.Image.new(
        new_image_dim.width,
        new_image_dim.height,
        image_type)
    gtk_ctx.temp_img.undo_disable()

    render_strategy.construct_preview(gtk_ctx.temp_img, dim, layer1, layer2)

    # Disable interpolation and zoom the image by scaling
    Gimp.context_set_interpolation(Gimp.InterpolationType.NONE)
    final_layer = gtk_ctx.temp_img.flatten()
    gtk_ctx.temp_img.scale(new_image_dim.width * zoom,
                           new_image_dim.height * zoom)

    return final_layer

def update_preview(context: PluginContext, force: bool = False):

    def get_layer_from_image(image: Gimp.Image, name: str) -> Gimp.Layer | None:
        for layer in image.get_layers():
            if layer.get_name() == name:
                return layer
        return None

    def redraw_preview(gtk_ctx: GtkContext, drawable: Gimp.Drawable):
        if gtk_ctx.preview_box:
            gtk_ctx.display_box.remove(gtk_ctx.preview_box)

        gtk_ctx.preview_box = GimpUi.DrawablePreview.new_from_drawable(drawable)
        gtk_ctx.display_box.pack_start(gtk_ctx.preview_box, False, True, 0)

        gtk_ctx.window.show_all()

    if context.skip_next_update:
        context.skip_next_update = False
        return

    layer1 = get_layer_from_image(context.image_ref, context.layer_names[0])
    layer2 = get_layer_from_image(context.image_ref, context.layer_names[1])

    if not layer1 and not layer2:
        log("No layers to render!")
        return

    layer_to_draw = get_preview_image(
        context.image_ref.get_base_type(),
        Dim(context.image_ref.get_width(),
            context.image_ref.get_height()),
        context.zoom_level,
        context.mode,
        layer1,
        layer2,
        context.gtk_ctx,
        RenderStrategyFactory.get_strategy(context.mode))

    redraw_preview(context.gtk_ctx, layer_to_draw)

def create_layer_select_combo(context: PluginContext, index: int, name_to_select=None):

    def get_image_layer_names(image: Gimp.Image, add_empty: bool = False) -> list[str]:
        layer_names = []

        if add_empty:
            layer_names.append("- none -")

        for layer in image.get_layers():
            layer_names.append(layer.get_name())
        return layer_names

    def update_layer_names(combo: Gtk.ComboBoxText, context: PluginContext, index: int):
        context.layer_names[index] = combo.get_active_text()
        update_preview(context)

    def try_to_select_option(option_to_select, option_list: list, combo: Gtk.ComboBoxText) -> bool:
        if not option_to_select:
            return False

        for index, option in enumerate(option_list):
            if option == option_to_select:
                combo.set_active(index)
                return True
        return False

    gtk_ctx = context.gtk_ctx
    layer_names = get_image_layer_names(context.image_ref, add_empty=index)

    combo = GtkBuilder.create_combo(
        layer_names,
        gtk_ctx.bottom_control_vbox)
    combo.connect(
        "changed",
        update_layer_names,
        context,
        index)

    if not try_to_select_option(name_to_select, layer_names, combo):
        combo.set_active(0)

    gtk_ctx.layer_select_combos[index] = combo

def change_display_mode(widget: Gtk.Widget, context: PluginContext):
    context.mode = widget.get_active_text()
    update_preview(context)

def refresh_combos(_: Gtk.Widget, context: PluginContext, count: int):
    names_to_select = ["", ""]
    for index in range(count):
        names_to_select[index] = context.gtk_ctx.layer_select_combos[index].get_active_text()
        context.gtk_ctx.bottom_control_vbox.remove(
            context.gtk_ctx.layer_select_combos[index])

    context.skip_next_update = True
    for index in range(count):
        create_layer_select_combo(context, index, name_to_select=names_to_select[index])

def tile_preview_run(procedure, run_mode: Gimp.RunMode, image: Gimp.Image, drawables: list, config, data):
    if run_mode != Gimp.RunMode.INTERACTIVE:
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

    GimpUi.init(plug_in_binary)
    context = PluginContext(image)

    context.gtk_ctx.window = GtkBuilder.create_window(plug_in_name)
    context.gtk_ctx.window.connect("destroy", lambda w: Gtk.main_quit())
    context.gtk_ctx.window.set_default_size(400, 660)

    window_box = GtkBuilder.create_vbox(context.gtk_ctx.window)
    upper_wrap_hbox = GtkBuilder.create_hbox(window_box)
    upper_label_vbox = GtkBuilder.create_vbox(upper_wrap_hbox)
    upper_control_vbox = GtkBuilder.create_vbox(upper_wrap_hbox)

    GtkBuilder.create_label("Zoom", upper_label_vbox)
    zoom_btn_box = GtkBuilder.create_hbox(upper_control_vbox)
    unzoom_btn = GtkBuilder.create_button("-", zoom_btn_box)
    unzoom_btn.connect("clicked", ZoomHandler.zoom_out, context)
    zoom_btn = GtkBuilder.create_button("+", zoom_btn_box)
    zoom_btn.connect("clicked", ZoomHandler.zoom_in, context)

    reset_zoom_btn = GtkBuilder.create_button("Reset Zoom", zoom_btn_box)
    reset_zoom_btn.connect("clicked", ZoomHandler.reset_zoom, context)

    zoom_to_fit_btn = GtkBuilder.create_button("Zoom to Fit", zoom_btn_box)
    zoom_to_fit_btn.connect("clicked", ZoomHandler.zoom_to_fit, context)

    context.gtk_ctx.display_box = GtkBuilder.create_hbox(window_box, fill=True)
    bottom_wrap_hbox = GtkBuilder.create_hbox(window_box)
    bottom_label_vbox = GtkBuilder.create_vbox(bottom_wrap_hbox)
    context.gtk_ctx.bottom_control_vbox = GtkBuilder.create_vbox(bottom_wrap_hbox)

    ### Mode select
    GtkBuilder.create_label("Preview mode", bottom_label_vbox)
    combo = GtkBuilder.create_combo(RenderMode.get_string_annotations(), context.gtk_ctx.bottom_control_vbox)
    combo.connect(
        "changed",
        change_display_mode,
        context)

    context.skip_next_update = True
    combo.set_active(0)

    ### Layers selection
    labels = [ "Primary layer", "Secondary layer" ]
    for label in labels:
        GtkBuilder.create_label(label, bottom_label_vbox)

    context.skip_next_update = True
    for index in range(len(labels)):
        create_layer_select_combo(context, index)

    ## Refresh button
    refresh_btn_hbox = GtkBuilder.create_hbox(window_box)
    refresh_btn = GtkBuilder.create_button("Refresh", refresh_btn_hbox)
    refresh_btn.connect(
        "clicked",
        refresh_combos,
        context,
        len(labels))

    window_box.show_all()
    context.gtk_ctx.window.show()
    Gtk.main()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

class TilePreview (Gimp.PlugIn):
    def do_query_procedures(self):
        return [ plug_in_proc ]

    def do_create_procedure(self, name):
        if name != plug_in_proc:
            return None

        procedure = Gimp.ImageProcedure.new(self,
                                            name,
                                            Gimp.PDBProcType.PLUGIN,
                                            tile_preview_run,
                                            None)

        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE |
                                       Gimp.ProcedureSensitivityMask.NO_DRAWABLES)
        procedure.set_menu_label(plug_in_name)
        procedure.set_attribution(plug_in_author, plug_in_org, plug_in_year)
        procedure.add_menu_path(plug_in_path)
        procedure.set_documentation(plug_in_docs, None)

        return procedure

Gimp.main(TilePreview.__gtype__, sys.argv)
