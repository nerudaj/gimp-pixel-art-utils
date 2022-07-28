# gimp-layer-group-animation-preview

Plugin for previewing animations stored in a layer group. This plugin is meant for pixel artists who create spritesheets (or tileset) for the game and works well in conjunction with [tilemancer](https://github.com/nerudaj/tilemancer)

## How to install

Open Gimp, go to Edit->Preferences->Folders->Plug-Ins and open one of the listed folders. Copy the folder containing the .py file to the opened `plug-ins` folder and restart Gimp. Now, under the `Windows` menu you should see Layer Group Animation Preview.

## How to use

This plugin is aimed at the users of tilemancer. This guide expects you have installed tilemancer into Gimp before. Expected workflow is such that you have any number of layer groups, some of those groups containing animations, others might only contain some tiles/one shot textures.

You can preview any animation just by launching this plugin and selecting name of appropriate group from the dropdown menu. Animation is played automatically in an endless cycle, showing you live preview, so you can let it play in a corner of the screen and keep working on your animation, even adding new frames etc. You can also change FPS of the animation just by editing appropriate box and clicking `Update`.

![Layers and preview](docs/screen.png)

When you are done with your spritesheet, use Filters->Animations->Tilemancer plugin, choose "One row per group" shape and confirm. Finished spritesheet will be created into separate image.

![Exported spritesheet](docs/screen2.png)

> NOTE: Tilemancer exports everything in reverse, so first item in the group will be the first item on a row. For this reason, animation preview also plays first item as the last one. This is consistent with Gimp's behaviour when exporting GIFs.
