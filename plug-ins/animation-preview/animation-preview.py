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
from gi.repository import Gio
import sys

plug_in_proc = "plug-in-nerudaj-animation-preview"
plug_in_binary = "py3-animation-preview"
plug_in_author = "nerudaj"
plug_in_org = "Pixel Art Utils"
plug_in_year = "2025"
plug_in_docs = "Plug-in for playing layer groups as animations."
plug_in_name = "Animation Preview"
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

class GtkContext:
    def __init__(self):
        self.window = None
        self.display_box = None
        self.preview_box = None
        self.current_frame_label = None

class Playback:
    def __init__(self, frame_count):
        self.fps = 1
        self.playing = False
        self.frame_index = 0
        self.frame_count = frame_count

    def start(self):
        self.playing = True

    def stop(self):
        self.playing = False

    def next_frame(self):
        self.frame_index += 1
        if self.frame_index == self.frame_count:
            self.frame_index = 0

    def prev_frame(self):
        self.frame_index -= 1
        if self.frame_index < 0:
            self.frame_index = self.frame_count - 1

    def update_fps(self, fps):
        self.fps = fps

class PluginContext:
    def __init__(self, image: Gimp.Image):
        self.zoom_level = -1.0
        self.gtk_ctx = GtkContext()
        self.image_ref = image
        self.layer_groups = [
            layer for layer in image.get_layers()
            if hasattr(layer, "get_children") and len(layer.get_children()) > 0
        ]
        self.layer_group_names = [ layer.get_name() for layer in self.layer_groups]
        self.playback = Playback(0)
        self.active_layer_group = None
        self.temp_img = None
        self.interval_event_id = -1

    def __str__(self):
        return f"PreviewContext(zoom = {self.zoom_level})"

    def __repr__(self):
        return self.__str__()

class ProcedureHelper:
    @staticmethod
    def call_pdb_procedure(name, properties: list[tuple[str, any]]):
        proc = Gimp.get_pdb().lookup_procedure(name)
        config = proc.create_config()
        for prop_name, prop_value in properties:
            config.set_property(prop_name, prop_value)
        proc.run(config)

def log(message):
    ProcedureHelper.call_pdb_procedure("gimp-message", [("message", message)])

def update_fps(_: Gtk.Widget, fps_entry, context: PluginContext):
    context.playback.update_fps(int(fps_entry.get_text()))

def start_playback(_: Gtk.Widget, context: PluginContext):
    context.playback.start()
    update_preview(context)

def stop_playback(_: Gtk.Widget, context: PluginContext):
    context.playback.stop()
    update_preview(context)

def prev_frame(_: Gtk.Widget, context: PluginContext):
    context.playback.prev_frame()
    update_preview(context, force=True)

def next_frame(_: Gtk.Widget, context: PluginContext):
    context.playback.next_frame()
    update_preview(context, force=True)

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
        
        img_w = context.image_ref.get_width()
        img_h = context.image_ref.get_height()
        if img_w == 0 or img_h == 0:
            return

        alloc = context.gtk_ctx.display_box.get_allocation()
        margin = 2
        context.zoom_level = min((alloc.width - margin) / img_w,
                                 (alloc.height - margin) / img_h)

        # Prevent zoom from being too small
        context.zoom_level = max(0.1, context.zoom_level)
        update_preview(context, force=True)

def update_preview(context: PluginContext, force: bool = False):
    if (force == context.playback.playing):
        return
    
    if (context.playback.playing):
        context.playback.next_frame()
    
    active_group_len = len(context.active_layer_group.get_children())
    frames = context.active_layer_group.get_children()
    current_frame = frames[active_group_len - 1 - context.playback.frame_index]

    context.gtk_ctx.current_frame_label.set_text(current_frame.get_name())

    if context.gtk_ctx.preview_box:
        context.gtk_ctx.display_box.remove(context.gtk_ctx.preview_box)
    
    context.gtk_ctx.preview_box = GimpUi.DrawablePreview.new_from_drawable(get_scaled_layer(current_frame, context))
    context.gtk_ctx.display_box.pack_start(context.gtk_ctx.preview_box, True, True, 0)
    context.gtk_ctx.window.show_all()

    if context.playback.playing:
        GLib.timeout_add(1000 / context.playback.fps, update_preview, context)
    
    return False # clear previous timeout if any

def get_scaled_layer(layer: Gimp.Layer, context: PluginContext) -> Gimp.Image:
    context.temp_img = Gimp.Image.new(
        context.image_ref.get_width(),
        context.image_ref.get_height(),
        context.image_ref.get_base_type())
    context.temp_img.undo_disable()

    temp_layer = Gimp.Layer.new_from_drawable(layer, context.temp_img)
    if len(temp_layer.get_children()) == 0:
        temp_layer.add_alpha()
    temp_layer.set_visible(True)
    context.temp_img.insert_layer(temp_layer, None, 0)
    Gimp.context_set_interpolation(Gimp.InterpolationType.NONE)
    context.temp_img.scale(context.temp_img.get_width() * context.zoom_level,
                           context.temp_img.get_height() * context.zoom_level)
    
    return temp_layer

def active_layer_changed(widget, fps_entry, context: PluginContext):
    active_layer_name = widget.get_active_text()
    if active_layer_name:
        for layer in context.layer_groups:
            if layer.get_name() == active_layer_name:
                context.active_layer_group = layer
                context.playback = Playback(len(layer.get_children()))
                update_fps(None, fps_entry, context)
    
    if context.zoom_level == -1.0:
        context.zoom_level = 128.0 / context.active_layer_group.get_width()

    update_preview(context, force=True)

def pick_file():
    log("DEBUG: Opening file chooser dialog for export.")
    dialog = Gtk.FileChooserDialog(
        title="Save As",
        parent=None,
        action=Gtk.FileChooserAction.SAVE,
        buttons=(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
    )
    dialog.set_do_overwrite_confirmation(True)
    response = dialog.run()
    filename = dialog.get_filename() if response == Gtk.ResponseType.OK else None
    dialog.destroy()
    log(f"DEBUG: File chooser dialog closed. Selected filename: {filename}")
    return filename

def export_clip_to_webp(widget, context: PluginContext):
    log("DEBUG: Starting export_clip_to_webp.")
    out_filename = pick_file()
    if out_filename is None:
        log("DEBUG: No filename selected, aborting export.")
        return

    if not out_filename.lower().endswith(".webp"):
        out_filename += ".webp"
        log(f"DEBUG: Appended .webp extension. New filename: {out_filename}")

    active_layer = context.active_layer_group
    playback = context.playback
    zoom_level = context.zoom_level
    image = context.image_ref

    log(f"DEBUG: Creating output image with size ({int(image.get_width() * zoom_level)}, {int(image.get_height() * zoom_level)})")
    out_img = Gimp.Image.new(
        int(image.get_width() * zoom_level),
        int(image.get_height() * zoom_level),
        image.get_base_type()
    )
    out_img.undo_disable()

    for i, frame in enumerate(reversed(active_layer.get_children())):
        log(f"DEBUG: Processing frame {i}: {frame.get_name()}")
        temp_layer = Gimp.Layer.new_from_drawable(frame, out_img)
        if len(temp_layer.get_children()) == 0:
            temp_layer.add_alpha()
        temp_layer.set_visible(True)
        out_img.insert_layer(temp_layer, None, 0)
        temp_layer.scale(
            int(image.get_width() * zoom_level),
            int(image.get_height() * zoom_level),
            False
        )

    log(f"DEBUG: Calling file-webp-save procedure. {out_filename}")
    ProcedureHelper.call_pdb_procedure(
        "file-webp-export",
        [
            ("image", out_img),
            ("file", Gio.File.new_for_path(out_filename)),
            ("options", None),
            ("preset", "default"),
            ("lossless", True),
            ("quality", 90),
            ("alpha-quality", 50),
            ("use-sharp-yuv", False),
            ("animation", True),
            ("animation-loop", True),
            ("minimize-size", False),
            ("keyframe-distance", 0),
            ("include-exif", False),
            ("include-iptc", False),
            ("include-xmp", False),
            ("include-thumbnail", True),
            ("default-delay", int(1000.0 / playback.fps)),
            ("force-delay", True)
        ])
    log("DEBUG: Export to WEBP completed.")

def animation_preview_run(procedure, run_mode, image, drawables, config, data):
    if run_mode != Gimp.RunMode.INTERACTIVE:
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

    GimpUi.init(plug_in_binary)
    context = PluginContext(image)
    
    context.gtk_ctx.window = GtkBuilder.create_window(plug_in_name)
    context.gtk_ctx.window.connect("destroy", lambda w: Gtk.main_quit())
    context.gtk_ctx.window.set_default_size(400, 660)
    window_box = GtkBuilder.create_vbox(context.gtk_ctx.window)
    current_layer_show_box = GtkBuilder.create_hbox(window_box, False)
    GtkBuilder.create_label("Current Layer:", current_layer_show_box)

    context.gtk_ctx.current_frame_label = GtkBuilder.create_label("", current_layer_show_box)

    playback_box = GtkBuilder.create_hbox(window_box, False)

    play_btn = GtkBuilder.create_button("Play", playback_box)
    play_btn.connect("clicked", start_playback, context)

    stop_btn = GtkBuilder.create_button("Stop", playback_box)
    stop_btn.connect("clicked", stop_playback, context)

    prev_btn = GtkBuilder.create_button("Previous", playback_box)
    prev_btn.connect("clicked", prev_frame, context)

    next_btn = GtkBuilder.create_button("Next", playback_box)
    next_btn.connect("clicked", next_frame, context)

    context.gtk_ctx.display_box = GtkBuilder.create_hbox(window_box, True)

    bottom_controls_box = GtkBuilder.create_hbox(window_box, False)
    labels_vbox = GtkBuilder.create_vbox(bottom_controls_box, 10)
    controls_vbox = GtkBuilder.create_vbox(bottom_controls_box)

    zoom_label_box = GtkBuilder.create_hbox(labels_vbox, True)
    zoom_box = GtkBuilder.create_hbox(controls_vbox, False)

    GtkBuilder.create_label("Zoom:", zoom_label_box)

    zoom_out_btn = GtkBuilder.create_button("-", zoom_box)
    zoom_out_btn.connect("clicked", ZoomHandler.zoom_out, context)

    zoom_in_btn = GtkBuilder.create_button("+", zoom_box)
    zoom_in_btn.connect("clicked", ZoomHandler.zoom_in, context)

    reset_zoom_btn = GtkBuilder.create_button("Reset Zoom", zoom_box)
    reset_zoom_btn.connect("clicked", ZoomHandler.reset_zoom, context)

    zoom_to_fit_btn = GtkBuilder.create_button("Zoom to Fit", zoom_box)
    zoom_to_fit_btn.connect("clicked", ZoomHandler.zoom_to_fit, context)

    fps_label_box = GtkBuilder.create_hbox(labels_vbox, True)
    fps_controls_box = GtkBuilder.create_hbox(controls_vbox, False)
    GtkBuilder.create_label("FPS:", fps_label_box)

    DEFAULT_FPS = 16
    fps_entry = GtkBuilder.create_value_input(DEFAULT_FPS, fps_controls_box)

    update_fps_btn = GtkBuilder.create_button("Update FPS", fps_controls_box)
    update_fps_btn.connect("clicked", update_fps, fps_entry, context)

    layer_label_box = GtkBuilder.create_hbox(labels_vbox, True)
    layer_select_box = GtkBuilder.create_hbox(controls_vbox, False)
    GtkBuilder.create_label("Group to play:", layer_label_box)

    layer_combo = GtkBuilder.create_combo(context.layer_group_names, layer_select_box)
    layer_combo.connect("changed", active_layer_changed, fps_entry, context)

    export_btn_box = GtkBuilder.create_hbox(window_box, False)
    export_btn = GtkBuilder.create_button("Export WEBP", export_btn_box)
    export_btn.connect("clicked", export_clip_to_webp, context)

    context.gtk_ctx.window.show_all()
    Gtk.main()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

class AnimationPreview (Gimp.PlugIn):
    def do_query_procedures(self):
        return [ plug_in_proc ]

    def do_create_procedure(self, name):
        if name != plug_in_proc:
            return None

        procedure = Gimp.ImageProcedure.new(self,
                                            name,
                                            Gimp.PDBProcType.PLUGIN,
                                            animation_preview_run,
                                            None)

        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE |
                                       Gimp.ProcedureSensitivityMask.NO_DRAWABLES)
        procedure.set_menu_label(plug_in_name)
        procedure.set_attribution(plug_in_author, plug_in_org, plug_in_year)
        procedure.add_menu_path(plug_in_path)
        procedure.set_documentation(plug_in_docs, None)

        return procedure

Gimp.main(AnimationPreview.__gtype__, sys.argv)
