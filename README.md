# Blender addon generate rigid for skirt or hair

## Notice

#### code is not be optimized, please save before using

#### Blender rigid body simulation is unstable, it will crash in an indeterminate way when undo(ctrl+z) or animation playback(shift+space), please save the file before doing these two operations

this script is written and tested in blender 4.0.2(should be compatible with 3.x)

## How to use
* Got a armature with bone which you want to add physics, the physics bone should connected by parent relationship to become chains, and the root of the chain should be child of a controller or character torso。
* enter armature pose mode
* select the bone chains you want to add physics
* click "Generate Rigid Body"

the rigid body object and joint object is available in "rigid&joint" collection

DEMO VIDEO:https://www.bilibili.com/video/BV1yN4y1h7R3
