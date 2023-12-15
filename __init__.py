import bpy
import math
from mathutils import Vector, Matrix
import bpy
from mathutils import Matrix
from math import radians
from mathutils import Matrix, Vector
import math
import re
import numpy as np
import mathutils
import random
import string
from collections import defaultdict
import colorsys
from itertools import combinations
import time

# TODO: do action with override context instead of using UI action

rigid_joint_collection_name = "OIMOYU_RIGID_JOINT"
main_collection_name = "OIMOYU_SKIRT_RIGID_GEN"
nc_num_limit = 256

def create_collection(collection_name):
    if collection_name in bpy.data.collections:
        collection = bpy.data.collections[collection_name]
    else:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
    return collection
    
def random_string(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def group_by_attr(objects, attr_name):
    grouped = defaultdict(list)
    for obj in objects:
        grouped[obj.get(attr_name)].append(obj)
    return grouped

def delete_armature_constraint(identity):
    for armature_obj in bpy.data.objects:
        if armature_obj.type != 'ARMATURE':
            continue
        for pose_bone in armature_obj.pose.bones:
            for existing_constraint in pose_bone.constraints:
                if identity in existing_constraint.name:
                    pose_bone.constraints.remove(existing_constraint)

def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)
    
def init_collection():
    main_collection = create_collection(main_collection_name)
    rigid_joint_collection = bpy.data.collections.get(rigid_joint_collection_name)
    if not rigid_joint_collection:
        rigid_joint_collection = bpy.data.collections.new(rigid_joint_collection_name)
        main_collection.children.link(rigid_joint_collection)
    return main_collection, rigid_joint_collection

def apply_scale(obj):
    override = {
        'active_object': obj,
        'object': obj,
        'selected_editable_objects': [obj]
    }
    with bpy.context.temp_override(**override):
        bpy.ops.object.transform_apply(scale=True, location=False, rotation=False)

    
def create_guide_mesh(context):
    settings = context.scene.skirt_rigid_gen_settings
    h_num = settings.h_num
    radius = 1.0
    height = 1
    v_num = settings.v_num
    guide_mesh_type = settings.guide_mesh_type
    vertex_num = h_num * (v_num+1)
    
    random_suffix = random_string(16)
    
    if guide_mesh_type == 'tube' and h_num<3:
        ShowMessageBox("Tube H num be less than 3.", "error message", 'ERROR')
        return
        
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except:
        pass
    bpy.ops.object.select_all(action='DESELECT')
    
    # create a new mesh object
    main_collection, rigid_joint_collection = init_collection()
    mesh = bpy.data.meshes.new(f"guide_mesh_{random_suffix}")
    obj = bpy.data.objects.new(f"guide_mesh_{random_suffix}", mesh)
    obj.location = (0, 0, 0)
    main_collection.objects.link(obj)
    
    obj['is_skirt_rigid_gen'] = True
    obj['skirt_rigid_gen_type'] = 'guide_mesh'
    
    if guide_mesh_type == 'face':
        vertices = [(i, 0, 0) for i in range(h_num)]
        # offset vertices
        bias = (h_num - 1) * 0.5
        vertices = [(x-bias, y, z) for x, y, z in vertices]
        
        edges = [(i, i+1) for i in range(h_num-1)]
        faces = []

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        mesh.from_pydata(vertices, edges, faces)
        mesh.update()

        bpy.ops.object.mode_set(mode='EDIT')
        
        # Extrude twice
        for _ in range(v_num):
            bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":(0, 0, -1)})

        bpy.ops.object.mode_set(mode='OBJECT')
    else:
        # create a new circle
        circle_vertices = []
        circle_edges = []
        circle_faces = []

        for i in range(h_num):
            theta = i / h_num * 2 * 3.14159
            x = radius * math.cos(theta)
            y = radius * math.sin(theta)
            circle_vertices.append((x, y, 0))

        for i in range(h_num):
            circle_edges.append((i, (i + 1) % h_num))

        # assign geometry to the mesh object
        mesh.from_pydata(circle_vertices, circle_edges, circle_faces)
        mesh.update()

        bpy.context.view_layer.objects.active = obj
        # extrude the circle
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')
        bpy.ops.mesh.select_all(action='SELECT')
        for i in range(v_num):
            height_temp = height / v_num
            bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":(0, 0, -height_temp), "orient_type":'GLOBAL'})
            scale_factor = 1.03
            bpy.ops.transform.resize(value=(scale_factor,scale_factor,scale_factor), orient_type='GLOBAL')
            
        # Flip the normals
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.flip_normals()
        
        # delete horizontal line for line guide mesh
        if guide_mesh_type == 'line':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type="EDGE")
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            edge_index_list = []
            threshold = 0.001
            for edge in mesh.edges:
                vert1 = mesh.vertices[edge.vertices[0]]
                vert2 = mesh.vertices[edge.vertices[1]]
                if abs(vert1.co.z - vert2.co.z) < threshold:
                    edge.select = True
            for edge_index in edge_index_list:
                obj.data.edges[edge_index].select = True
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.delete(type='EDGE')
            bpy.ops.mesh.select_mode(type="VERT")
            bpy.ops.object.mode_set(mode='OBJECT')


    bpy.ops.object.mode_set(mode='OBJECT')
    # assign vertex group
    line_vertex_list = []
    pin_vg = obj.vertex_groups.new(name='pin')
    for i in range(h_num):
        temp_list = []
        for j in range(v_num+1):
            vertex_id = j*h_num+i
            vertex = obj.data.vertices[vertex_id]
            
            vg = obj.vertex_groups.new(name=f"b_{i}_{j}")
            vg.add([vertex.index], 1.0, 'ADD')
            
            if j==0:
                pin_vg.add([vertex.index], 1.0, 'ADD')
                
            temp_list.append(vertex)
        line_vertex_list.append(temp_list)
    
    obj = bpy.context.object
    obj["is_guide_mesh"] = True
    obj["guide_mesh_type"] = guide_mesh_type
    
    obj.display_type = 'WIRE'
    obj.show_in_front = True
    
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(True)
    
    return obj


def create_bone_from_guide_mesh(context):
    random_suffix = random_string(16)
    basename = "rigid_body_armature"
    
    selected_objects = bpy.context.selected_objects
    if not selected_objects:
        ShowMessageBox("No object selected", "error message", 'ERROR')
        return 
    guide_mesh_obj = selected_objects[-1]
    
    if not guide_mesh_obj.get('is_guide_mesh'):
        ShowMessageBox("Not guidemesh selected", "error message", 'ERROR')
        return

    bpy.context.scene.frame_set(0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except:
        pass
    bpy.ops.object.select_all(action='DESELECT')

    
    # get horizontal count and vertical count
    vg_idx_name_dict = {vg.index: vg.name for vg in guide_mesh_obj.vertex_groups}
    vg_name_list = [temp for temp in vg_idx_name_dict.values()]
    circle_seg_num = max([int(re.search(r'b_(\d+)_(\d+)',temp).group(1)) for temp in vg_name_list if temp.startswith("b_")]) + 1
    verticle_seg_num = max([int(re.search(r'b_(\d+)_(\d+)',temp).group(2)) for temp in vg_name_list if temp.startswith("b_")])


    # get line_vertex_list
    line_vertex_list = []
    for i in range(circle_seg_num):
        temp_list = []
        for j in range(verticle_seg_num+1):
            vertex_id = j*circle_seg_num+i
            vertex = guide_mesh_obj.data.vertices[vertex_id]
            temp_list.append(vertex)
        line_vertex_list.append(temp_list)
    
    # create armature
    main_collection, rigid_joint_collection = init_collection()
    armature = bpy.data.armatures.new(name=f'{basename}_{random_suffix}')
    armature_obj = bpy.data.objects.new(f'Armature_{basename}_{random_suffix}', armature)
    # Add the armature object to the scene
    main_collection.objects.link(armature_obj)
    
    armature_obj['is_skirt_rigid_gen'] = True
    armature_obj['skirt_rigid_gen_type'] = 'armature'
    armature_obj.display_type = 'WIRE'
    armature_obj.show_in_front = True

    # add bone, and rotate
    # Set the armature object as the active object
    bpy.context.view_layer.objects.active = armature_obj
    # Enter edit mode for the armature object
    bpy.ops.object.mode_set(mode='EDIT')
    
    
    for i in range(len(line_vertex_list)):
        vertex_list = line_vertex_list[i]
        previous_bone = None
        for j in range(len(vertex_list)-1):
            # Create a new bone and set its position and size
            bone = armature.edit_bones.new(name=f'b_{i}_{j}_{random_suffix}')
            vertex = guide_mesh_obj.data.vertices[j*circle_seg_num+i]
            
            bone.head = vertex_list[j].co
            bone.tail = vertex_list[j+1].co
            
            if j != 0:
                bone.parent = previous_bone
                
            previous_bone = bone
            
            # rotate bone 
            vertex_normal_direction = vertex.normal
            x_axis_direction =- bone.x_axis

            # Define vectors
            x1 = bone.x_axis
            y1 = bone.z_axis
            v1 = vertex_normal_direction
            v2 = x_axis_direction

            # Find the normal of the x1 z1 plane
            normal = x1.cross(y1)
            # Project v1 onto the x1 z1 plane
            v1_proj = v1 - ((v1.dot(normal)) / normal.dot(normal)) * normal
            # Project v2 onto the x1 z1 plane
            v2_proj = v2 - ((v2.dot(normal)) / normal.dot(normal)) * normal
            
            
            # calculate signed angle
            dot_product = np.dot(v1_proj, v2_proj)
            cross_product = np.cross(v1_proj, v2_proj)
            # compute the angle between the two vectors with sign
            angle = math.atan2(np.linalg.norm(cross_product), dot_product)
            sign_direction = np.array(-bone.y_axis)
            sign = np.sign(np.dot(sign_direction, np.cross(v1_proj, v2_proj)))
            signed_angle = angle * sign
            
            bone.roll += signed_angle

    bpy.ops.object.mode_set(mode='OBJECT')
    
#    # create root bone
#    bone = armature.edit_bones.new(name=f'root')
#    bone.head = (0,0,0)
#    bone.tail = (0,0,1)
    
    # get root location
    root_vertex_list = []
    for i in range(len(line_vertex_list)):
        vertex_list = line_vertex_list[i]
        root_vertex_list.append(vertex_list[0])
    root_location = sum([temp.co for temp in root_vertex_list], Vector()) / len(root_vertex_list)

def can_create_rigid_from_bone(context):
    settings = context.scene.skirt_rigid_gen_settings
    basename = settings.basename

    chain_spring_stiffness = settings.chain_spring_stiffness
    chain_spring_damping = settings.chain_spring_damping
    disable_self_collision = settings.disable_self_collision

    random_suffix = random_string(16)
    selected_objects = bpy.context.selected_objects
    random_color = (*colorsys.hsv_to_rgb(random.random(), 1, 1), 0.5)
    
    selected_objects = bpy.context.selected_objects
    if not selected_objects:
        ShowMessageBox("No object selected", "error message", 'ERROR')
        return False
    armature_obj = selected_objects[-1]
    
    if armature_obj and armature_obj.type != 'ARMATURE':
        ShowMessageBox("This is not a armature", "error message", 'ERROR')
        return False
    
    if not basename:
        ShowMessageBox("Basename can not be empty", "error message", 'ERROR')
        return False
    return True
    
class SkirtRigidGenCreateRigidFromBoneOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.create_rigid_from_bone"
    bl_label = "create rigid from bone"
    def draw(self, context):
        if not can_create_rigid_from_bone(context):
            return
        armature_obj = bpy.context.selected_objects[-1]
        
        bone_list = [bone for bone in armature_obj.data.bones if bone.select]
        chain_list = []
        for bone in bone_list:
            if bone.parent not in bone_list:
                chain_list.append([bone.name])
        for bone in bone_list:
            for i in range(len(chain_list)):
                chain = chain_list[i]
                last_bone_name = chain[-1]
                if bone.parent and bone.parent.name == last_bone_name:
                    chain_list[i].append(bone.name)

        layout = self.layout
        for i, chain in enumerate(chain_list):
            parent_bone = armature_obj.data.bones.get(chain[0]).parent
            if parent_bone:
                layout.label(text=f"{i+1}.Parent:{parent_bone.name}    Chain length: {len(chain)}", icon="CHECKMARK")
            else:
                layout.label(text=f"{i+1}.Parent:None    Chain length: {len(chain)}", icon="CANCEL")
            layout.label(text=f"    Bone list: {' || '.join(chain)}", icon="FILE_PARENT")
        

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=720)

    def execute(self, context):
        create_rigid_from_bone(context)
        refresh_rigid_group(context)
        return {'FINISHED'}

def create_rigid_from_bone(context):
    settings = context.scene.skirt_rigid_gen_settings
    rigid_size_type = settings.rigid_size_type
    rigid_width = settings.rigid_width
    rigid_thickness = settings.rigid_thickness
    basename = settings.basename
    rigid_mass = settings.rigid_mass
    rigid_damping = settings.rigid_damping
    rigid_rad_angle_out = settings.rigid_rad_angle_out
    rigid_rad_angle_in = settings.rigid_rad_angle_in
    rigid_circ_angle = settings.rigid_circ_angle
    angle_limit_type = settings.angle_limit_type
    spring_setting_type = settings.spring_setting_type

    chain_spring_stiffness = settings.chain_spring_stiffness
    chain_spring_damping = settings.chain_spring_damping
    disable_self_collision = settings.disable_self_collision

    random_suffix = random_string(16)
    selected_objects = bpy.context.selected_objects
    random_color = (*colorsys.hsv_to_rgb(random.random(), 1, 1), 0.5)
    
    if not can_create_rigid_from_bone(context):
        return
    
    armature_obj = bpy.context.selected_objects[-1]
    
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    
    bpy.context.scene.frame_set(0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    
#    # get selected bone
#    bone_list = [bone for bone in armature_obj.data.bones if bone.select]
#    # find chain top bone
#    chain_list = []
#    for bone in bone_list:
#        if bone.parent not in bone_list:
#            chain_list.append([bone])
#        
#    # get chain child, append child one by one
#    for bone in bone_list:
#        for i in range(len(chain_list)):
#            chain = chain_list[i]
#            top_bone = chain[0]
#            last_bone = chain[-1]
#            if bone.parent == last_bone:
#                chain_list[i].append(bone)
    
    # Using list is reference assignment,after enter the edit mode, the whole list may change for unknow reason
    # get selected bone
    bone_list = [bone for bone in armature_obj.data.bones if bone.select]
    # find chain top bone
    chain_list = []
    for bone in bone_list:
        if bone.parent not in bone_list:
            chain_list.append([bone.name])
        
    # get chain child, append child one by one
    for bone in bone_list:
        for i in range(len(chain_list)):
            chain = chain_list[i]
            last_bone_name = chain[-1]
            if bone.parent and bone.parent.name == last_bone_name:
                chain_list[i].append(bone.name)

    # info for resize joint and root mesh
    avg_bone_length = sum([(temp.head_local - temp.tail_local).length for temp in armature_obj.data.bones]) / len(armature_obj.data.bones)
    scale_factor = avg_bone_length / 0.25
                
    main_collection, rigid_joint_collection = init_collection()
    master_collection = bpy.context.scene.collection

    # create joint and rigid
    joint_v_obj_list = []
    rigid_obj_list = []
    rigid_root_obj_list = []
    nc_joint_obj_list = []
    
    for i, chain in enumerate(chain_list):
        chain_len = len(chain)
        previous_rigid = None
        for j, bone_name in enumerate(chain):
            pose_bone = armature_obj.pose.bones[bone_name]
            start_coord = armature_obj.matrix_world @ pose_bone.head
            end_coord = armature_obj.matrix_world @ pose_bone.tail
            mid_coord = (start_coord + end_coord)/2 
            length = (start_coord - end_coord).length

            loc, rot, scale = armature_obj.matrix_world.decompose()
            rot_matrix = rot.to_matrix().to_4x4()
            bone_x_axis = (rot_matrix @ pose_bone.x_axis).normalized()
            bone_y_axis = (rot_matrix @ pose_bone.y_axis).normalized()
            bone_z_axis = (rot_matrix @ pose_bone.z_axis).normalized()

            if rigid_size_type == 'relative':
                width_factor = rigid_width
                thickness_factor = rigid_thickness
                width = width_factor * length
                thickness = thickness_factor * length
            elif rigid_size_type == 'absolute':
                width = rigid_width
                thickness = rigid_thickness
            else:
                raise Exception('unexpect type')

            # create joint
            joint_obj = bpy.data.objects.new(f"joint_{i}_{j}_{random_suffix}", None)
            joint_obj.show_in_front = True
            rigid_joint_collection.objects.link(joint_obj)
            joint_obj['skirt_rigid_gen_type'] = 'v_joint'
            joint_obj['is_skirt_rigid_gen'] = True
            joint_obj['skirt_rigid_gen_basename'] = basename
            joint_obj['skirt_rigid_gen_id'] = random_suffix
            joint_v_obj_list.append(joint_obj)
            
            joint_obj.empty_display_type = 'ARROWS'
            joint_obj.empty_display_size = 0.1
            joint_obj.scale = (scale_factor, scale_factor, scale_factor)
            
             # Define the original orthogonal axes
            X = Vector((1, 0, 0))  # x-axis
            Y = Vector((0, 1, 0))  # y-axis
            Z = Vector((0, 0, 1))  # z-axis

            rotation_matrix = mathutils.Matrix((bone_x_axis, bone_y_axis, bone_z_axis)).to_3x3().transposed() @ mathutils.Matrix((X, Y, Z)).to_3x3()
            joint_obj.matrix_world = rotation_matrix.to_4x4() @ joint_obj.matrix_world
            joint_obj.location = start_coord
            
            
            # create root rigid, should move to last layer in case interactive
            if j == 0:
                mesh = bpy.data.meshes.new(f"r_{i}_root_{random_suffix}")
                rigid_root_obj = bpy.data.objects.new(f"r_{i}_root_rigid_{random_suffix}", mesh)
                rigid_root_obj.display_type = 'TEXTURED'
                rigid_root_obj.hide_render = True
                rigid_root_obj.color = random_color
                rigid_root_obj.show_in_front = True
                rigid_joint_collection.objects.link(rigid_root_obj)
                rigid_root_obj['skirt_rigid_gen_type'] = 'root_rigid'
                rigid_root_obj['skirt_rigid_gen_basename'] = basename
                rigid_root_obj['skirt_rigid_gen_id'] = random_suffix
                rigid_root_obj['is_skirt_rigid_gen'] = True
                rigid_root_obj_list.append(rigid_root_obj)
                verts = [(thickness/2, width/2, length/2), (thickness/2, -width/2, length/2), (-thickness/2, -width/2, length/2), (-thickness/2, width/2, length/2),
                         (thickness/2, width/2, -length/2), (thickness/2, -width/2, -length/2), (-thickness/2, -width/2, -length/2), (-thickness/2, width/2, -length/2)]
                verts = [(x, y, z + length) for (x, y, z) in verts]
                edges = [(0,1), (1,2), (2,3), (3,0), (4,5), (5,6), (6,7), (7,4), (0,4), (1,5), (2,6), (3,7)]
                faces = [(3,2,1,0), (4,5,6,7), (0,4,7,3), (2,6,5,1), (0,1,5,4), (7,6,2,3)]
                mesh.from_pydata(verts, edges, faces)
                mesh.update()
                X = Vector((-1, 0, 0))
                Y = Vector((0, 0, -1))
                Z = Vector((0, -1, 0))
                rotation_matrix = mathutils.Matrix((bone_x_axis, bone_y_axis, bone_z_axis)).to_3x3().transposed() @ mathutils.Matrix((X, Y, Z)).to_3x3()
                rigid_root_obj.matrix_world = rotation_matrix.to_4x4() @ rigid_root_obj.matrix_world
                rigid_root_obj.location = mid_coord
                previous_rigid = rigid_root_obj
                

            
            # set bone property, must in edit mode when reading and writing edit_bone
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.view_layer.objects.active = armature_obj
            bpy.ops.object.mode_set(mode='EDIT')
            edit_bone = armature_obj.data.edit_bones[bone_name]
            if j != 0:
                edit_bone.use_connect = True
            edit_bone.use_inherit_rotation = False
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # create rigid
            mesh = bpy.data.meshes.new(f"r_{i}_{j}_{random_suffix}")
            rigid_obj = bpy.data.objects.new(f"r_{i}_{j}_{random_suffix}", mesh)
            rigid_obj.display_type = 'TEXTURED'
            rigid_obj.hide_render = True
            rigid_obj.color = random_color
            rigid_obj.show_in_front = True
            rigid_joint_collection.objects.link(rigid_obj)
            rigid_obj['skirt_rigid_gen_type'] = 'rigid_body'
            rigid_obj['skirt_rigid_gen_basename'] = basename
            rigid_obj['skirt_rigid_gen_id'] = random_suffix
            rigid_obj['is_skirt_rigid_gen'] = True
            rigid_obj_list.append(rigid_obj)
            verts = [(thickness/2, width/2, length/2), (thickness/2, -width/2, length/2), (-thickness/2, -width/2, length/2), (-thickness/2, width/2, length/2),
                     (thickness/2, width/2, -length/2), (thickness/2, -width/2, -length/2), (-thickness/2, -width/2, -length/2), (-thickness/2, width/2, -length/2)]
            edges = [(0,1), (1,2), (2,3), (3,0), (4,5), (5,6), (6,7), (7,4), (0,4), (1,5), (2,6), (3,7)]
            faces = [(3,2,1,0), (4,5,6,7), (0,4,7,3), (2,6,5,1), (0,1,5,4), (7,6,2,3)]
            mesh.from_pydata(verts, edges, faces)
            mesh.update()
            X = Vector((-1, 0, 0))
            Y = Vector((0, 0, -1))
            Z = Vector((0, -1, 0))
            rotation_matrix = mathutils.Matrix((bone_x_axis, bone_y_axis, bone_z_axis)).to_3x3().transposed() @ mathutils.Matrix((X, Y, Z)).to_3x3()
            rigid_obj.matrix_world = rotation_matrix.to_4x4() @ rigid_obj.matrix_world
            rigid_obj.location = mid_coord
            
            # add root rigid property
            if j==0:
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')
                rigid_root_obj.select_set(True)
                bpy.context.view_layer.objects.active = rigid_root_obj
                bpy.ops.rigidbody.objects_add(type='PASSIVE')
                rigid_root_obj.rigid_body.kinematic = True
                # place in last collision layer, setting this need to be a rigid body
                rigid_root_obj.rigid_body.collision_collections = tuple(False for _ in range(19))+ (True,)

            # add rigid property
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            rigid_obj.select_set(True)
            bpy.context.view_layer.objects.active = rigid_obj
            
            bpy.ops.rigidbody.objects_add(type='ACTIVE')
            rigid_obj.rigid_body.collision_shape = 'BOX'
            rigid_obj.rigid_body.mass = rigid_mass
            rigid_obj.rigid_body.linear_damping = rigid_damping
            rigid_obj.rigid_body.angular_damping = rigid_damping
            rigid_obj.rigid_body.use_margin = True
            rigid_obj.rigid_body.collision_margin = 0.001


            # bone track to rigid body, overwrite if exist
            constraint_name = f"skirt_rigid_gen_RIGID_TRACK_BONE_{random_suffix}"
            for existing_constraint in pose_bone.constraints:
                if existing_constraint.name == constraint_name:
                    pose_bone.constraints.remove(existing_constraint)
            constraint = pose_bone.constraints.new('COPY_TRANSFORMS')
            constraint.name = constraint_name
            constraint.target = joint_obj
            
            # root bone anchor must follow top movable rigid
            constraint = joint_obj.constraints.new('CHILD_OF')
            constraint.target = rigid_obj

            # root rigid track to parent bone
            if j == 0 and pose_bone.parent:
                constraint = rigid_root_obj.constraints.new('CHILD_OF')
                constraint.target = armature_obj
                constraint.subtarget = pose_bone.parent.name

                
            # add vertical rigid_constraint
            # for unknow reason, override not work for "constraint_add"
            if angle_limit_type == 'constant':
                rigid_rad_angle_out_single = rigid_rad_angle_out / (chain_len)
                rigid_rad_angle_in_single = rigid_rad_angle_in / (chain_len)
                rigid_circ_angle_single = rigid_circ_angle / (chain_len)
            elif angle_limit_type == 'linear':
                const_n = (chain_len)
                total_n = const_n + ( const_n * (const_n) ) / 2
                current_weight = j+1
                rigid_rad_angle_out_single = rigid_rad_angle_out * current_weight / total_n
                rigid_rad_angle_in_single = rigid_rad_angle_in * current_weight / total_n
                rigid_circ_angle_single = rigid_circ_angle * current_weight / total_n
            else:
                raise Exception("unknow type")
            

            if spring_setting_type == 'constant':
                chain_spring_stiffness = chain_spring_stiffness
                chain_spring_damping = chain_spring_damping
            elif spring_setting_type == 'linear':
                factor = (chain_len - j) / chain_len
                chain_spring_stiffness = chain_spring_stiffness * factor
                chain_spring_damping = chain_spring_damping * factor
            else:
                raise Exception("unknow type")
            
            
            
            bpy.context.view_layer.objects.active = joint_obj
            bpy.ops.rigidbody.constraint_add(type='GENERIC_SPRING')
            
            # always fixed twist
            bpy.context.object.rigid_body_constraint.use_limit_ang_y = True
            bpy.context.object.rigid_body_constraint.limit_ang_y_lower = 0
            bpy.context.object.rigid_body_constraint.limit_ang_y_upper = 0
            
            # angle limit
            bpy.context.object.rigid_body_constraint.use_limit_ang_x = True
            bpy.context.object.rigid_body_constraint.use_limit_ang_z = True
            bpy.context.object.rigid_body_constraint.limit_ang_x_lower = -rigid_circ_angle_single/180*math.pi
            bpy.context.object.rigid_body_constraint.limit_ang_x_upper = rigid_circ_angle_single/180*math.pi
            bpy.context.object.rigid_body_constraint.limit_ang_z_lower = -rigid_rad_angle_out_single/180*math.pi
            bpy.context.object.rigid_body_constraint.limit_ang_z_upper = rigid_rad_angle_in_single/180*math.pi

            # Hinge connect
            bpy.context.object.rigid_body_constraint.use_limit_lin_x = True
            bpy.context.object.rigid_body_constraint.use_limit_lin_y = True
            bpy.context.object.rigid_body_constraint.use_limit_lin_z = True
            bpy.context.object.rigid_body_constraint.limit_lin_x_lower = 0
            bpy.context.object.rigid_body_constraint.limit_lin_x_upper = 0
            bpy.context.object.rigid_body_constraint.limit_lin_y_lower = 0
            bpy.context.object.rigid_body_constraint.limit_lin_y_upper = 0
            bpy.context.object.rigid_body_constraint.limit_lin_z_lower = 0
            bpy.context.object.rigid_body_constraint.limit_lin_z_upper = 0
            
            # spring connect
            bpy.context.object.rigid_body_constraint.use_spring_ang_x = True
            bpy.context.object.rigid_body_constraint.use_spring_ang_y = True
            bpy.context.object.rigid_body_constraint.use_spring_ang_z = True
            bpy.context.object.rigid_body_constraint.spring_damping_ang_x = chain_spring_damping
            bpy.context.object.rigid_body_constraint.spring_damping_ang_y = chain_spring_damping
            bpy.context.object.rigid_body_constraint.spring_damping_ang_z = chain_spring_damping
            bpy.context.object.rigid_body_constraint.spring_stiffness_ang_x = chain_spring_stiffness
            bpy.context.object.rigid_body_constraint.spring_stiffness_ang_y = chain_spring_stiffness
            bpy.context.object.rigid_body_constraint.spring_stiffness_ang_z = chain_spring_stiffness
            
            bpy.context.object.rigid_body_constraint.object1 = previous_rigid
            bpy.context.object.rigid_body_constraint.object2 = rigid_obj
            
            previous_rigid = rigid_obj

            # create non collision joint
            if disable_self_collision:
                for rigid_obj_temp in rigid_obj_list:
                    i_temp = re.search(r'(\d+)_(\d+)',rigid_obj_temp.name).group(1)
                    j_temp = re.search(r'(\d+)_(\d+)',rigid_obj_temp.name).group(2)
                    if int(i_temp) != i:
                        # create joint
                        joint_obj = bpy.data.objects.new(f"nc_{i}_{j}&{i_temp}_{j_temp}_{random_suffix}", None)
                        joint_obj['skirt_rigid_type'] = 'nc_joint'
                        joint_obj['is_skirt_rigid_gen'] = True
                        joint_obj['skirt_rigid_gen_id'] = random_suffix
                        joint_obj['skirt_rigid_gen_basename'] = basename
                        joint_obj.location = armature_obj.location
                        nc_joint_obj_list.append(joint_obj)
                        rigid_joint_collection.objects.link(joint_obj)
                        
                        joint_obj.empty_display_type = 'ARROWS'
                        joint_obj.empty_display_size = 0.1
                        joint_obj.scale = (scale_factor, scale_factor, scale_factor)
                
                        # add non collision
                        bpy.context.view_layer.objects.active = joint_obj
                        bpy.ops.rigidbody.constraint_add(type='GENERIC')
                        bpy.context.object.rigid_body_constraint.object1 = rigid_obj
                        bpy.context.object.rigid_body_constraint.object2 = rigid_obj_temp



bl_info = {
    "name": "Skit Rigid Generator",
    "author": "Oimoyu",
    "version": (1, 4),
    "blender": (4, 0, 2),
    "location": "View3D > Sidebar > Skit Rigid Gen",
    "description": "generate rigid body for skirt",
    "category": "Object",
}

class SkirtRigidGenGeneratePanel(bpy.types.Panel):
    """Creates a panel in the 3D Viewport"""
    bl_label = "Generate"
    bl_idname = "VIEW3D_PT_OIMOYU_SKIRT_RIGID_GENERATE"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Skirt Rigid Gen"
    bl_order = 1
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.skirt_rigid_gen_settings
        
        
        guide_mesh_col = layout.column(align=True)
        guide_mesh_col.label(text="Guide Mesh")
        guide_mesh_box = guide_mesh_col.box()

        split = guide_mesh_box.split(factor=0.5)
        col = split.column()
        col.label(text="H num")
        col.prop(settings, "h_num", text="")
        
        col = split.column()
        col.label(text="V num")
        col.prop(settings, "v_num", text="")
        
        guide_mesh_box.row().label(text="Guide Mesh Type")
        guide_mesh_box.row().prop(settings, "guide_mesh_type",expand=True)
        
        row = guide_mesh_box.row()
        row.scale_y = 2.0
        row.operator("skirt_rigid_gen.create_guide_mesh", text="Generate Guide Mesh", icon="MOD_LATTICE")
        
        
        layout.separator()
        
        row = layout.row()
        row.scale_y = 2.0
        row.operator("skirt_rigid_gen.create_bone_from_guide_mesh", text="Create Bone From Guide Mesh", icon="BONE_DATA")
        row.enabled = len(bpy.context.selected_objects) != 0 and bpy.context.selected_objects[-1].get('is_guide_mesh') == True

        layout.separator()
        
        
        rigid_col = layout.column(align=True)
        rigid_col.label(text="Physics Rigid")
        rigid_box = rigid_col.box()
        
        col = rigid_box.column()
        split = col.split(factor=0.5)
        col = split.column()
        col.label(text="Basename")
        col = split.column()
        col.prop(settings, "basename", text="")
        
        rigid_box.label(text="Rigid Size", icon="SNAP_FACE_CENTER")
        rigid_size_box = rigid_box.box()
        rigid_size_box.row().label(text="Rigid Size Type")
        rigid_size_box.row().prop(settings, "rigid_size_type",expand=True)
        col = rigid_size_box.column()
        split = col.split(factor=0.5)
        col = split.column()
        col.label(text="Width")
        col.prop(settings, "rigid_width", text="")
        col = split.column()
        col.label(text="Thickness")
        col.prop(settings, "rigid_thickness", text="")
        
        rigid_box.label(text="Angle Limit", icon="RESTRICT_SELECT_ON")
        rigid_angle_limit_box = rigid_box.box()
        rigid_angle_limit_box.row().label(text="Angle Limit Type")
        rigid_angle_limit_box.row().prop(settings, "angle_limit_type",expand=True)
        
        rigid_angle_limit_box.row().label(text="Angle Limit (accumulated)")
        rigid_angle_limit_box.row().prop(settings, "rigid_circ_angle", text="Circ Angle")
        rigid_angle_limit_box.row().prop(settings, "rigid_rad_angle_in", text="Radial Angle In")
        rigid_angle_limit_box.row().prop(settings, "rigid_rad_angle_out", text="Radial Angle Out")

        rigid_box.label(text="Spring setting", icon="GP_SELECT_STROKES")
        rigid_spring_setting_box = rigid_box.box()
        
        rigid_spring_setting_box.row().label(text="Spring Setting Type")
        rigid_spring_setting_box.row().prop(settings, "spring_setting_type",expand=True)
        col = rigid_spring_setting_box.column()
        split = col.split(factor=0.5)
        col = split.column()
        col.label(text="Stiffness")
        col.prop(settings, "chain_spring_stiffness", text="")
        col = split.column()
        col.label(text="Damping")
        col.prop(settings, "chain_spring_damping", text="")

        rigid_box.label(text="Rigid setting", icon="SNAP_VOLUME")
        rigid_setting_box = rigid_box.box()
        col = rigid_setting_box.column()
        split = col.split(factor=0.5)
        col = split.column()
        col.label(text="Mass(Kg)")
        col.prop(settings, "rigid_mass", text="")
        col = split.column()
        col.label(text="Damping")
        col.prop(settings, "rigid_damping", text="")

        rigid_box.row().prop(settings, "disable_self_collision")

        row = rigid_box.row()
        row.scale_y = 2.0
        row.operator("skirt_rigid_gen.create_rigid_from_bone", text="Generate Rigid Body", icon="MESH_CUBE")
        row.enabled = (len(bpy.context.selected_objects) != 0 and 
                        bpy.context.selected_objects[-1].type == 'ARMATURE' and
                        bpy.context.selected_objects[-1].mode == 'POSE'
                        )

class SkirtRigidGenCreateGuideMeshOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.create_guide_mesh"
    bl_label = "create guide mesh"

    def execute(self, context):
        create_guide_mesh(context)
        return {'FINISHED'}
    
class SkirtRigidGenCreateBoneOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.create_bone_from_guide_mesh"
    bl_label = "create guide mesh"

    def execute(self, context):
        create_bone_from_guide_mesh(context)
        return {'FINISHED'}

class SkirtRigidGenClearAllOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.clear_all"
    bl_label = "Clear All"
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        all_addon_obj_list = [temp for temp in bpy.data.objects if temp.get('is_skirt_rigid_gen')]
        obj_with_id_list = [temp for temp in all_addon_obj_list if temp.get('skirt_rigid_gen_id')]
        selected_object_group = group_by_attr(obj_with_id_list, "skirt_rigid_gen_id")
        
        for obj in all_addon_obj_list:
            bpy.data.objects.remove(obj, do_unlink=True)
            
        refresh_rigid_group(context)
        # TODO:also check for rigid body collection
        return {'FINISHED'}

class SkirtRigidGenHideAllOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.hide_all"
    bl_label = "Hide All"
    
    def execute(self, context):
        all_obj = bpy.data.objects
        for obj in all_obj:
            if obj.get('is_skirt_rigid_gen'):
                obj.hide_viewport = True
        return {'FINISHED'}

class SkirtRigidGenShowAllOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.show_all"
    bl_label = "Show All"

    def execute(self, context):
        all_obj = bpy.data.objects
        for obj in all_obj:
            if obj.get('is_skirt_rigid_gen'):
                obj.hide_viewport = False
                obj.hide_set(False)
        return {'FINISHED'}
    
class SkirtRigidGenRefreshRigidGroupOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.refresh_rigid_group"
    bl_label = "refresh rigid group"

    def execute(self, context):
        refresh_rigid_group(context)
        return {'FINISHED'}

class SkirtRigidGenToolPanel(bpy.types.Panel):
    bl_label = "Tool"
    bl_idname = "VIEW3D_PT_OIMOYU_SKIRT_RIGID_TOOL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Skirt Rigid Gen"
    bl_order = 3
    
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.operator("skirt_rigid_gen.generate_passive_bone_rigid", text="Generate Passive Bone Rigid", icon="MESH_ICOSPHERE")
        row.enabled = (len(bpy.context.selected_objects) != 0 and 
                        bpy.context.selected_objects[-1].type == 'ARMATURE' and
                        bpy.context.selected_objects[-1].mode == 'POSE'
                        )
        
        layout.row().operator("skirt_rigid_gen.clear_frame_cache", text="Clear Frame Cache", icon="TRASH")
        
class SkirtRigidGenClearFrameCacheOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.clear_frame_cache"
    bl_label = "Clear Frame Cache"
    def execute(self, context):
        bpy.ops.mesh.primitive_cube_add()
        cube = bpy.context.active_object
        cube.name = "temp_obj"
        bpy.ops.rigidbody.object_add()
        cube.rigid_body.type = 'ACTIVE'
        bpy.ops.rigidbody.object_remove()
        bpy.data.objects.remove(cube, do_unlink=True)
        
        # for really in memory cache
        scene = bpy.context.scene
        if scene.rigidbody_world:
            scene.rigidbody_world.point_cache.frame_start = scene.frame_start
            scene.rigidbody_world.point_cache.frame_end = scene.frame_end
            bpy.ops.ptcache.free_bake_all()
            
        bpy.context.scene.frame_set(0)
        
        return {'FINISHED'}
    
class SkirtRigidGenGeneratePassiveBoneRigidOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.generate_passive_bone_rigid"
    bl_label = "Generate Passive Bone Rigid"
    def execute(self, context):
        selected_objects = bpy.context.selected_objects
        armature_obj = selected_objects[-1]
        if not armature_obj or armature_obj.type != 'ARMATURE':
            ShowMessageBox("no object selected.", "error message", 'ERROR')
            return {'FINISHED'}
        
        selected_pose_bones = [bone for bone in armature_obj.pose.bones if bone.bone.select]
        if not selected_pose_bones:
            ShowMessageBox("no bone selected.", "error message", 'ERROR')
            return {'FINISHED'}
        
        passive_bone_rigid_list = []
        for pose_bone in selected_pose_bones:
            # length and direction of the bone
            length = (pose_bone.head - pose_bone.tail).length
            bpy.ops.mesh.primitive_cube_add(size=length, enter_editmode=False, align='WORLD')
            rigid_obj = bpy.context.active_object
            rigid_obj['is_skirt_rigid_gen'] = True
            rigid_obj['skirt_rigid_gen_type'] = 'passive_bone_rigid'
            rigid_obj.name = 'passive_bone_rigid'
            rigid_obj.hide_render = True
            
            passive_bone_rigid_list.append(rigid_obj)
            
            # display
    #        rigid_obj.show_in_front = True
            rigid_obj.color[3] = 0.5
            
            rigid_obj.scale[0] = rigid_obj.scale[1] = 0.3
            bpy.ops.rigidbody.objects_add(type='PASSIVE')
            rigid_obj.rigid_body.kinematic = True
            # set margin
            rigid_obj.rigid_body.use_margin = True
            rigid_obj.rigid_body.collision_margin = 0.001
            rigid_obj.rigid_body.collision_shape = 'CAPSULE'

            bone_x_axis = pose_bone.x_axis
            bone_y_axis = pose_bone.y_axis
            bone_z_axis = pose_bone.z_axis
            X = Vector((1, 0, 0))
            Y = Vector((0, 0, 1))
            Z = Vector((0, 1, 0))
            rotation_matrix = mathutils.Matrix((bone_x_axis, bone_y_axis, bone_z_axis)).to_3x3().transposed() @ mathutils.Matrix((X, Y, Z)).to_3x3()
            rigid_obj.matrix_world = rotation_matrix.to_4x4() @ rigid_obj.matrix_world

    #        # fit when the armature transform is not 1
            rigid_obj.location = armature_obj.matrix_world @ ((pose_bone.head + pose_bone.tail) / 2)
            rigid_obj.scale = armature_obj.matrix_world @ rigid_obj.scale
            
            # parent to bone        
            rigid_obj.parent = armature_obj
            rigid_obj.parent_type = 'BONE'
            rigid_obj.parent_bone = pose_bone.name

            bpy.ops.object.select_all(action='DESELECT')
            rigid_obj.select_set(True)
            armature_obj.select_set(True)
            bpy.context.view_layer.objects.active = armature_obj
            armature_obj.data.bones.active = armature_obj.data.bones[pose_bone.name]
            bpy.ops.object.parent_set(type='BONE_RELATIVE')
            
            
            # apply scale
            apply_scale(rigid_obj)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        for passive_bone_rigid in passive_bone_rigid_list:
            passive_bone_rigid.select_set(True)
        
        return {'FINISHED'}

def get_select_rigid_body_list():
    return [temp for temp in bpy.context.selected_objects if temp.get('is_skirt_rigid_gen') and temp.rigid_body ]

def update_rigid_body_mass(self, context):
    select_rigid_body_list = get_select_rigid_body_list()
    for obj in select_rigid_body_list:
        obj.rigid_body.mass = context.scene.skirt_rigid_gen_settings.rigid_body_mass_temp
def update_rigid_body_friction(self, context):
    select_rigid_body_list = get_select_rigid_body_list()
    for obj in select_rigid_body_list:
        obj.rigid_body.friction = context.scene.skirt_rigid_gen_settings.rigid_body_friction_temp
        
def get_select_joint_list():
    return [temp for temp in bpy.context.selected_objects if temp.get('is_skirt_rigid_gen') and temp.rigid_body_constraint ]

def update_joint_stiffness(self, context):
    select_joint_list = get_select_joint_list()
    for obj in select_joint_list:
        chain_spring_stiffness = context.scene.skirt_rigid_gen_settings.chain_spring_stiffness_temp
        obj.rigid_body_constraint.spring_stiffness_ang_x = chain_spring_stiffness
        obj.rigid_body_constraint.spring_stiffness_ang_y = chain_spring_stiffness
        obj.rigid_body_constraint.spring_stiffness_ang_z = chain_spring_stiffness
    
def update_joint_damping(self, context):
    select_joint_list = get_select_joint_list()
    for obj in select_joint_list:
        chain_spring_damping = context.scene.skirt_rigid_gen_settings.chain_spring_damping_temp
        obj.rigid_body_constraint.spring_damping_ang_x = chain_spring_damping
        obj.rigid_body_constraint.spring_damping_ang_y = chain_spring_damping
        obj.rigid_body_constraint.spring_damping_ang_z = chain_spring_damping

def refresh_rigid_group(context):
    settings = context.scene.skirt_rigid_gen_settings
    object_list = [temp for temp in bpy.context.scene.objects if temp.get('is_skirt_rigid_gen') and temp.get('skirt_rigid_gen_id') and temp.get('skirt_rigid_gen_basename')]
    object_group = group_by_attr(object_list, "skirt_rigid_gen_id")
    my_item = settings.rigid_group.clear()
    
    for skirt_rigid_gen_id, obj_list in object_group.items():
        basename = obj_list[0].get('skirt_rigid_gen_basename')
        identity = obj_list[0].get('skirt_rigid_gen_id')
        
        my_item = settings.rigid_group.add()
        my_item.name = basename
        my_item.id = identity


class SkirtRigidGenHandleRigidGroupOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.handle_rigid_group"
    bl_label = "Handle rigid and joint"
    skirt_rigid_gen_id: bpy.props.StringProperty()
    action: bpy.props.StringProperty()
    obj_type: bpy.props.StringProperty()
    
    
    def invoke(self, context, event):
        if self.action == 'delete':
            return context.window_manager.invoke_confirm(self, event)
        else:
            return self.execute(context)
    
    def execute(self, context):
        rigid_group = context.scene.skirt_rigid_gen_settings.rigid_group
        rigid_group_index = context.scene.skirt_rigid_gen_settings.rigid_group_index
        if rigid_group_index < 0 or len(rigid_group) <= rigid_group_index:
#            ShowMessageBox("index err", "error message", 'ERROR')
            return {'FINISHED'}
        rigid_group_item = rigid_group[rigid_group_index]
        
        if self.action == 'select':
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = None
            
        obj_list = [temp for temp in bpy.data.objects if temp.get('skirt_rigid_gen_id') == rigid_group_item.id ]

        if self.action == 'delete':
            for obj in obj_list:
                bpy.data.objects.remove(obj, do_unlink=True)
            delete_armature_constraint(rigid_group_item.id)
            refresh_rigid_group(context)
            
        if self.action == 'select':
            for obj in obj_list:
                if not self.obj_type:
                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj
                else:
                    if self.obj_type == 'all_joint' and 'joint' in obj.get('skirt_rigid_gen_type', ''):
                        obj.select_set(True)
                        bpy.context.view_layer.objects.active = obj
                    else:
                        if obj.get('skirt_rigid_gen_type') == self.obj_type:
                            obj.select_set(True)
                            bpy.context.view_layer.objects.active = obj
                            
        if self.action == 'show':
            for obj in obj_list:
                obj.hide_viewport = False
                obj.hide_set(False)
                
        if self.action == 'hide':
            for obj in obj_list:
                if obj.type == 'ARMATURE':
                    continue
                obj.hide_viewport = True
            
        return {'FINISHED'}

    
# TODO: check large select performance
class SkirtRigidGenModifyPanel(bpy.types.Panel):
    """Creates a panel in the 3D Viewport"""
    bl_label = "Modify"
    bl_idname = "VIEW3D_PT_OIMOYU_SKIRT_RIGID_MODIFY"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Skirt Rigid Gen"
    bl_order = 2
        
    def draw(self, context):
        layout = self.layout
        settings = context.scene.skirt_rigid_gen_settings

        selected_object_list = bpy.context.selected_objects
        selected_object_list = [temp for temp in selected_object_list if temp.get('is_skirt_rigid_gen') and temp.get('skirt_rigid_gen_id')]
        
        rigid_body_list = [temp for temp in selected_object_list if temp.rigid_body ]
        joint_list = [temp for temp in selected_object_list if temp.type == 'EMPTY' and temp.rigid_body_constraint ]
        
        selected_object_group = group_by_attr(selected_object_list, "skirt_rigid_gen_id")
        
        row = layout.row()
        row.template_list("SKIRTRIGIDGEN_UL_RIGIDGROUP", "", settings, "rigid_group", settings, "rigid_group_index")
        col = row.column(align=True)
        col.operator("skirt_rigid_gen.refresh_rigid_group", text="", icon='FILE_REFRESH')
        op = col.operator('skirt_rigid_gen.handle_rigid_group', text="", icon='HIDE_OFF')
        op.action = 'show'
        op = col.operator('skirt_rigid_gen.handle_rigid_group', text="", icon='HIDE_ON')
        op.action = 'hide'
        op = col.operator('skirt_rigid_gen.handle_rigid_group', text="", icon='RESTRICT_SELECT_OFF')
        op.action = 'select'
        op = col.operator('skirt_rigid_gen.handle_rigid_group', text="", icon='X')
        op.action = 'delete'

        col = layout.column()
        split = col.split(factor=0.5)
        col = split.column()
        col.operator("skirt_rigid_gen.show_all", text="Show All", icon="HIDE_OFF")
        col = split.column()
        col.operator("skirt_rigid_gen.hide_all", text="Hide All", icon="HIDE_ON")
        layout.operator("skirt_rigid_gen.clear_all", text="Clear All", icon="X")


class SkirtRigidGenRigidGroupItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")
    id: bpy.props.StringProperty(name="ID")
    
class SKIRTRIGIDGEN_UL_RIGIDGROUP(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name)
                     
class SkirtRigidGenPanelSettings(bpy.types.PropertyGroup):
    h_num : bpy.props.IntProperty(name="horizonal segment number",min=1,default=3)
    v_num : bpy.props.IntProperty(name="vertical segment number",min=1,default=3)
    
    rigid_width : bpy.props.FloatProperty(name="rigid width",min=0.001,default=1)
    rigid_thickness : bpy.props.FloatProperty(name="rigid thickness",min=0.001,default=1)
    basename : bpy.props.StringProperty(name="basename",default='skirt')
    
    rigid_mass : bpy.props.FloatProperty(name="Rigid Mass",min=0.001,default=1.0)
    rigid_damping : bpy.props.FloatProperty(name="Rigid Damping",default=0.5,min=0,max=1)

    rigid_rad_angle_out : bpy.props.FloatProperty(name="Radial Angle Out",min=0,max=180,default=180, description="Angle limit outward along the radial direction")
    rigid_rad_angle_in : bpy.props.FloatProperty(name="Radial Angle In", min=0,max=180,default=45, description="Angle limit inward along the radial direction")
    rigid_circ_angle : bpy.props.FloatProperty(name="Circ Angle",min=0,max=90,default=45, description="Angular limits along the circumferential direction")

    angle_limit_type : bpy.props.EnumProperty(name="Angle Limit Type", items=(       
        ("linear", "Linear", ""),
        ("constant", "Constant", ""),
        ),
        default='linear',
        description="Angle limit change type"
    )
    
    spring_setting_type : bpy.props.EnumProperty(name="Spring Setting Type", items=(       
        ("linear", "Linear", ""),
        ("constant", "Constant", ""),
        ),
        default='linear',
        description="Spring Setting Type"
    )
    
    guide_mesh_type : bpy.props.EnumProperty(name="Guide Mesh Type", items=(    
        ("tube", "Tube", ""),  
        ("face", "Face", ""),
        ("line", "Line", ""),
        ),
        default='tube',
        description="Guide Mesh Type"
    )

    rigid_size_type : bpy.props.EnumProperty(name="Rigid Size Type", items=(    
        ("relative", "Relative", ""),        
        ("absolute", "Absolute", ""),
        ),
        default='relative',
        description="Rigid Size Type"
    )
    
    chain_spring_stiffness : bpy.props.FloatProperty(name="chain sping stiffness",min=0,default=10, description="Horizontal Spring Stiffness")
    chain_spring_damping : bpy.props.FloatProperty(name="chain sping damping",min=0,default=0.5, description="Horizontal Spring Damping")
   
    disable_self_collision : bpy.props.BoolProperty(name="Disable Self Collistion",default=False, description="This option can only be enabled when the number of rigid bodies is less than 32")
    
    rigid_body_mass_temp : bpy.props.FloatProperty(name="Temp Rigid Body Mass", default=1.0, min=0.0,update=update_rigid_body_mass)
    rigid_body_friction_temp : bpy.props.FloatProperty(name="Temp Rigid Body Friction", default=0.5, min=0.0, max=1,update=update_rigid_body_friction)
    
    chain_spring_stiffness_temp : bpy.props.FloatProperty(name="Temp Chain Spring Stiffness", default=1.0, min=0.0,update=update_joint_stiffness)
    chain_spring_damping_temp : bpy.props.FloatProperty(name="Temp Chain Spring Damping", default=0.5, min=0.0,update=update_joint_damping)
     
    rigid_group : bpy.props.CollectionProperty(type=SkirtRigidGenRigidGroupItem)
    rigid_group_index : bpy.props.IntProperty()



classes = [
    SkirtRigidGenGeneratePanel,
    SkirtRigidGenModifyPanel,
    SkirtRigidGenToolPanel,
    SkirtRigidGenCreateGuideMeshOperator,
    SkirtRigidGenCreateBoneOperator,
    SkirtRigidGenCreateRigidFromBoneOperator,
    SkirtRigidGenHandleRigidGroupOperator,
    SkirtRigidGenClearAllOperator,
    SkirtRigidGenClearFrameCacheOperator,
    SkirtRigidGenGeneratePassiveBoneRigidOperator,
    SkirtRigidGenHideAllOperator,
    SkirtRigidGenShowAllOperator,
    SkirtRigidGenRefreshRigidGroupOperator,
    SkirtRigidGenRigidGroupItem,
    SKIRTRIGIDGEN_UL_RIGIDGROUP,
    SkirtRigidGenPanelSettings
]
    
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.skirt_rigid_gen_settings = bpy.props.PointerProperty(type=SkirtRigidGenPanelSettings)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    del bpy.types.Scene.skirt_rigid_gen_settings


if __name__ == "__main__":
    register()
