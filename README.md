# Blender addon generate rigid for skirt or hair

## Notice

#### code is not be optimized, please save before using

#### Blender rigid body simulation is unstable, it will crash in an indeterminate way when undo(ctrl+z) or animation playback(shift+space), please save the file before doing these two operations

this script is written and tested in blender 3.2.2

## How to use

* 1.click the "Generate Guide Mesh"(do not add or delete vertex in this mesh)
* 2.adjust the guide mesh to fit the skirt mesh
* 3.select the guide mesh and click the "Generate Rigid Body"
* 4.add "Child of" constraint to the root bone to follow the character

the rigid body object and joint object is available in "rigid&joint" collection

DEMO VIDEO:https://www.bilibili.com/video/BV1Mc411T7mC
