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

def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


def create_root_mesh(location=(0,0,0)):
    if bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.mesh.primitive_cube_add(size=2)
    master_obj = bpy.context.active_object

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete(type='ONLY_FACE')
    bpy.ops.mesh.select_mode(type="VERT")
    bpy.ops.object.mode_set(mode='OBJECT')


    face_orientations = {
        "top": [(0, 0, 1), (0, 0, 0)],
        "bottom": [(0, 0, -1), (180, 0, 0)],
        "left": [(1, 0, 0), (90, 0, 90)],
        "right": [(-1, 0, 0), (90, 0, -90)],
        "back": [(0, 1, 0), (90, 0, 180)],
        "front": [(0, -1, 0), (90, 0, 0)],
    }

    text_obj_list = []
    for key, value in face_orientations.items():
        bpy.ops.object.text_add()
        text_object = bpy.context.active_object
        text_object.data.body = key.capitalize()
        text_object.rotation_euler = [radians(angle) for angle in value[1]]
        
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        bpy.ops.object.convert(target='MESH')
        text_object.location=value[0]
        text_object.scale = (0.6,0.6,0.6)
        
        text_obj_list.append(text_object)
        
    bpy.ops.object.select_all(action='DESELECT')
    for obj in text_obj_list:
        obj.select_set(True)
    master_obj.select_set(True)
    bpy.context.view_layer.objects.active = master_obj
    bpy.ops.object.join()
    
    master_obj.location = location
    
    return master_obj

#def get_matrix_neighbor_list_lr(matrix, row, col):
#    rows = len(matrix)
#    cols = len(matrix[0]) if matrix else 0
#    neighbors = []

#    for i in [-1, 0, 1]:
#        for j in [-2,-1, 0, 1,2]:
#            if i == 0 and j == 0:  # current element, skip
#                continue

#            newRow, newCol = row + i, (col + j) % cols  # The % operator ensures wrapping around
#            if 0 <= newRow < rows:  # Check vertical boundary
#                neighbors.append(matrix[newRow][newCol])

#    return neighbors
            
def apply_scale(obj):
    # in case change the active obj in the viewlayer
    active = bpy.context.view_layer.objects.active

    override = {
        'active_object': obj,
        'object': obj,
        'selected_editable_objects': [obj]
    }

    bpy.ops.object.transform_apply(override, scale=True, location=False, rotation=False)

    bpy.context.view_layer.objects.active = active
    
def init_collection():
    main_collection = create_collection(main_collection_name)
    rigid_joint_collection = bpy.data.collections.get(rigid_joint_collection_name)
    if not rigid_joint_collection:
        rigid_joint_collection = bpy.data.collections.new(rigid_joint_collection_name)
        main_collection.children.link(rigid_joint_collection)
    return main_collection, rigid_joint_collection


def create_guide_mesh(context):
    settings = context.scene.skirt_rigid_panel_settings
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
    mesh = bpy.data.meshes.new(f"guide_mesh_{random_suffix}")
    obj = bpy.data.objects.new(f"guide_mesh_{random_suffix}", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (0, 0, 0)
    
    obj['is_skirt_rigid_gen'] = True
    obj['skirt_rigid_type'] = 'guide_mesh'
    
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
    obj["is_guidemesh"] = True
    obj["guide_mesh_type"] = guide_mesh_type
    
    obj.display_type = 'WIRE'
    obj.show_in_front = True
    
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(True)
    
    main_collection, rigid_joint_collection = init_collection()
    main_collection.objects.link(obj)
    master_collection = bpy.context.scene.collection
    master_collection.objects.unlink(obj)
    
    return obj


def create_rigid_from_guide_mesh(context):
    settings = context.scene.skirt_rigid_panel_settings
    rigid_size_type = settings.rigid_size_type
    rigid_width = settings.rigid_width
    rigid_thickness = settings.rigid_thickness
    basename = settings.basename
    rigid_mass = settings.rigid_mass
    rigid_damping = settings.rigid_damping
    enable_angle_limit = settings.enable_angle_limit
    rigid_rad_angle_out = settings.rigid_rad_angle_out
    rigid_rad_angle_in = settings.rigid_rad_angle_in
    rigid_circ_angle = settings.rigid_circ_angle
    angle_limit_type = settings.angle_limit_type
    enable_horizontal_spring = settings.enable_horizontal_spring
    horizontal_spring_stiffness = settings.horizontal_spring_stiffness
    horizontal_spring_damping = settings.horizontal_spring_damping
    disable_self_collision = settings.disable_self_collision
    
    enable_chain_spring =  settings.enable_chain_spring
    chain_spring_stiffness = settings.chain_spring_stiffness
    chain_spring_damping = settings.chain_spring_damping
    
    random_suffix = random_string(16)
    
    selected_objects = bpy.context.selected_objects
    random_color = (*colorsys.hsv_to_rgb(random.random(), 1, 1), 0.5)
    
    if not selected_objects:
        ShowMessageBox("No object selected", "error message", 'ERROR')
        return 
    guide_mesh_obj = selected_objects[-1]
    
    if not basename:
        ShowMessageBox("Basename can not be empty", "error message", 'ERROR')
        return
    
    if not guide_mesh_obj.get('is_guidemesh'):
        ShowMessageBox("Not guidemesh selected", "error message", 'ERROR')
        return 

    bpy.context.scene.frame_set(0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except:
        pass
    bpy.ops.object.select_all(action='DESELECT')
    
    # disable hotizontal spring for line
    if guide_mesh_obj.get('guide_mesh_type') == 'line':
        enable_horizontal_spring = False
        
    # disable non-collision for line
    if guide_mesh_obj.get('guide_mesh_type') == 'line':
        disable_self_collision = True

    vg_idx_name_dict = {vg.index: vg.name for vg in guide_mesh_obj.vertex_groups}
    vg_name_list = [temp for temp in vg_idx_name_dict.values()]
    circle_seg_num = max([int(re.search(r'b_(\d+)_(\d+)',temp).group(1)) for temp in vg_name_list if temp.startswith("b_")]) + 1
    verticle_seg_num = max([int(re.search(r'b_(\d+)_(\d+)',temp).group(2)) for temp in vg_name_list if temp.startswith("b_")])
    
    main_collection, rigid_joint_collection = init_collection()

    master_collection = bpy.context.scene.collection
    
    # get lin_vertex_list
    line_vertex_list = []
    for i in range(circle_seg_num):
        temp_list = []
        for j in range(verticle_seg_num+1):
            vertex_id = j*circle_seg_num+i
            vertex = guide_mesh_obj.data.vertices[vertex_id]
            temp_list.append(vertex)
        line_vertex_list.append(temp_list)
    
    
    
    # create armature
    armature = bpy.data.armatures.new(name=f'Armature_{basename}_{random_suffix}')
    armature_obj = bpy.data.objects.new(f'Armature_{basename}_{random_suffix}', armature)
    # Add the armature object to the scene
    bpy.context.scene.collection.objects.link(armature_obj)
    
    armature_obj['is_skirt_rigid_gen'] = True
    armature_obj['skirt_rigid_type'] = 'armature'
    armature_obj.display_type = 'WIRE'
    armature_obj.show_in_front = True

    main_collection.objects.link(armature_obj)
    master_collection.objects.unlink(armature_obj)

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
    
    
    # create root mesh
#    bpy.ops.mesh.primitive_cube_add(size=0.5, enter_editmode=False, align='WORLD', location=root_location)
    root_mesh_obj = create_root_mesh(location=root_location)
    root_mesh_obj['is_skirt_rigid_gen'] = True
    root_mesh_obj['skirt_rigid_type'] = 'root_mesh'
    
    root_mesh_obj.name = 'root_mesh'
    root_mesh_obj.parent = armature_obj
    bpy.ops.rigidbody.objects_add(type='PASSIVE')
    root_mesh_obj.rigid_body.kinematic = True
    root_mesh_obj.rigid_body.collision_collections = tuple(False for _ in range(19))+ (True,)


    # create joint and rigid
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    joint_v_obj_list = []
    rigid_obj_list = []
    for i in range(len(line_vertex_list)):
        vertex_list = line_vertex_list[i]
        for j in range(len(vertex_list)-1):
            temp_id = j*circle_seg_num+i
            vertex = guide_mesh_obj.data.vertices[temp_id]
            
            bone = armature.edit_bones[f'b_{i}_{j}_{random_suffix}']
            start_coord = bone.head
            end_coord = bone.tail
            mid_coord = (start_coord + end_coord)/2
            
            length = (start_coord - end_coord).length
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

            bone_x_axis = bone.x_axis
            bone_y_axis = bone.y_axis
            bone_z_axis = bone.z_axis


            #joint
            joint_obj = bpy.data.objects.new(f"joint_{i}_{j}_{random_suffix}", None)
            joint_obj['skirt_rigid_type'] = 'v_joint'
            joint_obj['is_skirt_rigid_gen'] = True
            joint_v_obj_list.append(joint_obj)
            
            joint_obj.empty_display_type = 'ARROWS'
            joint_obj.empty_display_size = 0.1
            
            scene = bpy.context.scene
            scene.collection.objects.link(joint_obj)

             # Define the original orthogonal axes
            X = Vector((1, 0, 0))  # x-axis
            Y = Vector((0, 1, 0))  # y-axis
            Z = Vector((0, 0, 1))  # z-axis

            rotation_matrix = mathutils.Matrix((bone_x_axis, bone_y_axis, bone_z_axis)).to_3x3().transposed() @ mathutils.Matrix((X, Y, Z)).to_3x3()
            joint_obj.matrix_world = rotation_matrix.to_4x4() @ joint_obj.matrix_world
            joint_obj.location = vertex.co


            #rigid
            mesh = bpy.data.meshes.new(f"r_{i}_{j}_{random_suffix}")
            # Create a new cuboid object
            rigid_obj = bpy.data.objects.new(f"r_{i}_{j}_{random_suffix}", mesh)
            rigid_obj['skirt_rigid_type'] = 'rigid_body'
            rigid_obj['is_skirt_rigid_gen'] = True
            rigid_obj_list.append(rigid_obj)
            
            # Link the object to the scene
            scene = bpy.context.scene
            scene.collection.objects.link(rigid_obj)

            # Set the vertices of the cuboid
            verts = [(thickness/2, width/2, length/2), (thickness/2, -width/2, length/2), (-thickness/2, -width/2, length/2), (-thickness/2, width/2, length/2),
                     (thickness/2, width/2, -length/2), (thickness/2, -width/2, -length/2), (-thickness/2, -width/2, -length/2), (-thickness/2, width/2, -length/2)]

            # Set the edges of the cuboid
            edges = [(0,1), (1,2), (2,3), (3,0), (4,5), (5,6), (6,7), (7,4), (0,4), (1,5), (2,6), (3,7)]

            # Set the faces of the cuboid
            faces = [(3,2,1,0), (4,5,6,7), (0,4,7,3), (2,6,5,1), (0,1,5,4), (7,6,2,3)]

            # Add the vertices, edges, and faces to the mesh
            mesh.from_pydata(verts, edges, faces)
            mesh.update()

             # Define the original orthogonal axes
            X = Vector((-1, 0, 0))  # x-axis
            Y = Vector((0, 0, -1))  # y-axis
            Z = Vector((0, -1, 0))  # z-axis

            rotation_matrix = mathutils.Matrix((bone_x_axis, bone_y_axis, bone_z_axis)).to_3x3().transposed() @ mathutils.Matrix((X, Y, Z)).to_3x3()
            rigid_obj.matrix_world = rotation_matrix.to_4x4() @ rigid_obj.matrix_world
            
            rigid_obj.location = mid_coord
    
            
    # add rigid property
    bpy.ops.object.mode_set(mode='OBJECT')
    for rigid_obj in rigid_obj_list:
        bpy.ops.object.select_all(action='DESELECT')
        rigid_obj.select_set(True)
        bpy.context.view_layer.objects.active = rigid_obj
        bpy.ops.rigidbody.objects_add(type='ACTIVE')
        
        rigid_obj.rigid_body.collision_shape = 'BOX'
        rigid_obj.rigid_body.mass = rigid_mass
        rigid_obj.rigid_body.linear_damping = rigid_damping
        rigid_obj.rigid_body.angular_damping = rigid_damping
        
        # set margin
        rigid_obj.rigid_body.use_margin = True
        rigid_obj.rigid_body.collision_margin = 0.001
        

    # add vertical rigid_constraint
    bpy.ops.object.mode_set(mode='OBJECT')
    for joint_obj in joint_v_obj_list:
        bpy.ops.object.select_all(action='DESELECT')
        rigid_obj.select_set(True)
        bpy.context.view_layer.objects.active = joint_obj
        
        i = int(re.search(r"joint_(\d+)_(\d+)", joint_obj.name).group(1))
        j = int(re.search(r"joint_(\d+)_(\d+)", joint_obj.name).group(2))
        
#        if not enable_angle_limit:
#            rigid_rad_angle_out = 120
#            rigid_rad_angle_in = 45
#            rigid_circ_angle = 30
#            angle_limit_type = 'linear'
            
        if angle_limit_type == 'constant':
            rigid_rad_angle_out_single = rigid_rad_angle_out / (verticle_seg_num-1)
            rigid_rad_angle_in_single = rigid_rad_angle_in / (verticle_seg_num-1)
            rigid_circ_angle_single = rigid_circ_angle / (verticle_seg_num-1)
        elif angle_limit_type == 'linear':
            const_n = (verticle_seg_num)
            total_n = const_n + ( const_n * (const_n) ) / 2
            current_weight = j+1
            rigid_rad_angle_out_single = rigid_rad_angle_out * current_weight / total_n
            rigid_rad_angle_in_single = rigid_rad_angle_in * current_weight / total_n
            rigid_circ_angle_single = rigid_circ_angle * current_weight / total_n
            
        else:
            raise Exception("unknow type")

        bpy.ops.rigidbody.constraint_add(type='GENERIC_SPRING')
        
        # always fixed twist
        bpy.context.object.rigid_body_constraint.use_limit_ang_y = True
        bpy.context.object.rigid_body_constraint.limit_ang_y_lower = 0
        bpy.context.object.rigid_body_constraint.limit_ang_y_upper = 0
        if enable_angle_limit:
            bpy.context.object.rigid_body_constraint.use_limit_ang_x = True
            bpy.context.object.rigid_body_constraint.use_limit_ang_z = True
            bpy.context.object.rigid_body_constraint.limit_ang_x_lower = -rigid_circ_angle_single/180*math.pi
            bpy.context.object.rigid_body_constraint.limit_ang_x_upper = rigid_circ_angle_single/180*math.pi
            bpy.context.object.rigid_body_constraint.limit_ang_z_lower = -rigid_rad_angle_out_single/180*math.pi
            bpy.context.object.rigid_body_constraint.limit_ang_z_upper = rigid_rad_angle_in_single/180*math.pi


        bpy.context.object.rigid_body_constraint.use_limit_lin_x = True
        bpy.context.object.rigid_body_constraint.use_limit_lin_y = True
        bpy.context.object.rigid_body_constraint.use_limit_lin_z = True
        bpy.context.object.rigid_body_constraint.limit_lin_x_lower = 0
        bpy.context.object.rigid_body_constraint.limit_lin_x_upper = 0
        bpy.context.object.rigid_body_constraint.limit_lin_y_lower = 0
        bpy.context.object.rigid_body_constraint.limit_lin_y_upper = 0
        bpy.context.object.rigid_body_constraint.limit_lin_z_lower = 0
        bpy.context.object.rigid_body_constraint.limit_lin_z_upper = 0
        
        if enable_chain_spring:
            bpy.context.object.rigid_body_constraint.use_spring_ang_x = True
            bpy.context.object.rigid_body_constraint.use_spring_ang_y = True
            bpy.context.object.rigid_body_constraint.use_spring_ang_z = True
            bpy.context.object.rigid_body_constraint.spring_damping_ang_x = chain_spring_damping
            bpy.context.object.rigid_body_constraint.spring_damping_ang_y = chain_spring_damping
            bpy.context.object.rigid_body_constraint.spring_damping_ang_z = chain_spring_damping
            bpy.context.object.rigid_body_constraint.spring_stiffness_ang_x = chain_spring_stiffness
            bpy.context.object.rigid_body_constraint.spring_stiffness_ang_y = chain_spring_stiffness
            bpy.context.object.rigid_body_constraint.spring_stiffness_ang_z = chain_spring_stiffness
        
        
        if j == 0:
            bpy.context.object.rigid_body_constraint.object1 = root_mesh_obj
        else:
            bpy.context.object.rigid_body_constraint.object1 = rigid_obj_list[i*verticle_seg_num + j-1]
            
        bpy.context.object.rigid_body_constraint.object2 = rigid_obj_list[i*verticle_seg_num + j]


    # bone track to rigid body
    bpy.ops.object.mode_set(mode='OBJECT')
    pose_bone_list = armature_obj.pose.bones
    for i in range(len(line_vertex_list)):
        vertex_list = line_vertex_list[i]
        for j in range(len(vertex_list)-1):
            temp_id = j*circle_seg_num+i
            
            pose_bone = pose_bone_list[temp_id]
            rigid_obj = rigid_obj_list[temp_id]
            
            constraint = pose_bone.constraints.new('CHILD_OF')
            constraint.target = rigid_obj


    # add horizonal constraint 
    # get edit bone
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # create horizontal spring
    joint_h_obj_list = []
    if enable_horizontal_spring:
#        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bone_list = armature_obj.pose.bones
        for i in range(len(line_vertex_list)):
            vertex_list = line_vertex_list[i]
            for j in range(len(vertex_list))[1:]: 
                temp_id = j*circle_seg_num+i
                vertex = guide_mesh_obj.data.vertices[temp_id]
                j = j-1 #  bottom vertex for upper bone
                # set width by near vertex
                if temp_id % circle_seg_num == 0:
                    l_id = temp_id + (circle_seg_num-1)
                    r_id = temp_id + 1
                    l_i = i + (circle_seg_num-1)
                    r_i = i + 1
                    
                elif temp_id % circle_seg_num == circle_seg_num - 1:
                    l_id = temp_id - 1
                    r_id = temp_id - (circle_seg_num-1)
                    l_i = i - 1
                    r_i = i - (circle_seg_num-1)
                else:
                    l_id = temp_id - 1
                    r_id = temp_id +1
                    l_i = i - 1
                    r_i = i + 1
                    
                # skip left-right in face guide mesh
                if guide_mesh_obj.get('guide_mesh_type') == 'face' and l_i == 0 and r_i == circle_seg_num-1:
                    continue
                
                l_vertex = guide_mesh_obj.data.vertices[l_id]
                r_vertex = guide_mesh_obj.data.vertices[r_id]
                l_j = j
                r_j = j
        
                mid_coord = (r_vertex.co + vertex.co)/2
                bone = armature.edit_bones[f'b_{i}_{j}_{random_suffix}']
                r_bone = armature.edit_bones[f'b_{r_i}_{r_j}_{random_suffix}']
            
                
                # create joint
                joint_obj = bpy.data.objects.new(f"joint_{i}_{j}&{r_i}_{r_j}_{random_suffix}", None)
                joint_obj['skirt_rigid_type'] = 'h_joint'
                joint_obj['is_skirt_rigid_gen'] = True
                joint_h_obj_list.append(joint_obj)
                
                joint_obj.empty_display_type = 'ARROWS'
                joint_obj.empty_display_size = 0.1
                
                scene = bpy.context.scene
                scene.collection.objects.link(joint_obj)

                mid_x = (bone.x_axis + r_bone.x_axis)/2
                mid_y = (bone.y_axis + r_bone.y_axis)/2
                mid_z = (bone.z_axis + r_bone.z_axis)/2
                 # Define the original orthogonal axes
                X = Vector((1, 0, 0))  # x-axis
                Y = Vector((0, 1, 0))  # y-axis
                Z = Vector((0, 0, 1))  # z-axis
                rotation_matrix = mathutils.Matrix((mid_x, mid_y, mid_z)).to_3x3().transposed() @ mathutils.Matrix((X, Y, Z)).to_3x3()
                joint_obj.matrix_world = rotation_matrix.to_4x4() @ joint_obj.matrix_world

                joint_obj.location = mid_coord
    
    # create non collision joint
    nc_joint_obj_list = []
    if disable_self_collision:
        list1 = [(x, y) for x in range(circle_seg_num) for y in range(verticle_seg_num)]
        ij_list = combinations(list1, 2)
        for ij_1, ij_2 in ij_list:
            i1, j1 = ij_1
            i2, j2 = ij_2
            
            # skip for v neighbor
            if i1 == i2:
                continue

            # create joint
            joint_obj = bpy.data.objects.new(f"nc_{i1}_{j1}&{i2}_{j2}_{random_suffix}", None)
            joint_obj['skirt_rigid_type'] = 'nc_joint'
            joint_obj['is_skirt_rigid_gen'] = True
            joint_obj.location = root_location
            nc_joint_obj_list.append(joint_obj)
            
            joint_obj.empty_display_type = 'ARROWS'
            joint_obj.empty_display_size = 0.1
            
            scene = bpy.context.scene
            scene.collection.objects.link(joint_obj)
    
            # add non collision
            bpy.context.view_layer.objects.active = joint_obj
            bpy.ops.rigidbody.constraint_add(type='GENERIC')
            bpy.context.object.rigid_body_constraint.object1 = rigid_obj_list[i1*verticle_seg_num + j1]
            bpy.context.object.rigid_body_constraint.object2 = rigid_obj_list[i2*verticle_seg_num + j2]

    # add horizontal rigid_constraint
    bpy.ops.object.mode_set(mode='OBJECT')
    for joint_obj in joint_h_obj_list:
        bpy.ops.object.select_all(action='DESELECT')
        rigid_obj.select_set(True)
        bpy.context.view_layer.objects.active = joint_obj
        
        i = int(re.search(r"joint_(\d+)_(\d+)", joint_obj.name).group(1))
        j = int(re.search(r"joint_(\d+)_(\d+)", joint_obj.name).group(2))
        r_i = int(re.search(r"joint_\d+_\d+&(\d+)_(\d+)", joint_obj.name).group(1))
        r_j = int(re.search(r"joint_\d+_\d+&(\d+)_(\d+)", joint_obj.name).group(2))
        
        bpy.ops.rigidbody.constraint_add(type='GENERIC_SPRING')
        bpy.context.object.rigid_body_constraint.object1 = rigid_obj_list[i*verticle_seg_num + j]
        bpy.context.object.rigid_body_constraint.object2 = rigid_obj_list[r_i*verticle_seg_num + r_j]

        if enable_horizontal_spring:
            # Horizontal spring
            bpy.context.object.rigid_body_constraint.use_spring_x = True
            bpy.context.object.rigid_body_constraint.use_spring_y = True
            bpy.context.object.rigid_body_constraint.use_spring_z = True
            bpy.context.object.rigid_body_constraint.spring_stiffness_x = horizontal_spring_stiffness
            bpy.context.object.rigid_body_constraint.spring_stiffness_y = horizontal_spring_stiffness
            bpy.context.object.rigid_body_constraint.spring_stiffness_z = horizontal_spring_stiffness
            bpy.context.object.rigid_body_constraint.spring_damping_x = horizontal_spring_damping
            bpy.context.object.rigid_body_constraint.spring_damping_y = horizontal_spring_damping
            bpy.context.object.rigid_body_constraint.spring_damping_z = horizontal_spring_damping
    
    # info for resize joint and root mesh
    avg_bone_length = sum([(temp.head_local - temp.tail_local).length for temp in armature_obj.data.bones]) / len(armature_obj.data.bones)
    scale_factor = avg_bone_length / 0.25
    
    # last hide joint and rigid
    for joint_obj in joint_v_obj_list:
#        joint_obj.hide_set(True)
        rigid_joint_collection.objects.link(joint_obj)
        master_collection.objects.unlink(joint_obj)
        joint_obj.show_in_front = True
        joint_obj.scale = (scale_factor, scale_factor, scale_factor)

    for joint_obj in joint_h_obj_list:
#        joint_obj.hide_set(True)
        rigid_joint_collection.objects.link(joint_obj)
        master_collection.objects.unlink(joint_obj)
        joint_obj.show_in_front = True
        joint_obj.scale = (scale_factor, scale_factor, scale_factor)
        
    for joint_obj in nc_joint_obj_list:
#        joint_obj.hide_set(True)
        rigid_joint_collection.objects.link(joint_obj)
        master_collection.objects.unlink(joint_obj)
        joint_obj.show_in_front = True
        joint_obj.scale = (scale_factor, scale_factor, scale_factor)
        
    for rigid_obj in rigid_obj_list:
#        rigid_obj.hide_set(True)
        rigid_joint_collection.objects.link(rigid_obj)
        master_collection.objects.unlink(rigid_obj)
        rigid_obj.display_type = 'TEXTURED'
#        rigid_obj.show_in_front = True
        rigid_obj.hide_render = True
        rigid_obj.color = random_color

    # set root mesh obj display
    root_mesh_obj.display_type = 'WIRE'
    root_mesh_obj.show_in_front = True
    root_mesh_obj.hide_render = True
    
    # scale root mesh
    root_mesh_obj.scale = (avg_bone_length*1.5, avg_bone_length*1.5, avg_bone_length*1.5)
    
    # store property in armature obj
    for obj in joint_v_obj_list + joint_h_obj_list + nc_joint_obj_list + rigid_obj_list + [armature_obj] + [root_mesh_obj] :
        obj['is_skirt_rigid_gen'] = True
        obj['skirt_rigid_gen_basename'] = basename
        obj['skirt_rigid_gen_id'] = f'oimoyu_{basename}_{random_suffix}'


bl_info = {
    "name": "Skit Rigid Generator",
    "author": "Oimoyu",
    "version": (1, 3),
    "blender": (3, 6, 2),
    "location": "View3D > Sidebar > Skit Rigid Gen",
    "description": "generate rigid body for skirt",
    "category": "Object",
}

class GeneratePanel(bpy.types.Panel):
    """Creates a panel in the 3D Viewport"""
    bl_label = "Generate"
    bl_idname = "VIEW3D_PT_OIMOYU_SKIRT_RIGID_GENERATE"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Skirt Rigid Gen"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.skirt_rigid_panel_settings
        
        col = layout.column()
        split = col.split(factor=0.5)
        # Add input boxes to the first column
        col = split.column()
        col.label(text="H num")
        col.prop(settings, "h_num", text="")
        
        col = split.column()
        col.label(text="V num")
        col.prop(settings, "v_num", text="")
        
        row = layout.row()
        row.label(text="Guide Mesh Type")
        row = layout.row()
        row.prop(settings, "guide_mesh_type",expand=True)
        layout.separator()  # Adds a horizontal line
        row = layout.row()
        row.scale_y = 2.0
        row.operator("skirt_rigid_gen.create_guide_mesh", text="Generate Guid Mesh")
        layout.separator()
        layout.separator()
        
#        col = layout.column()
#        split = col.split(factor=0.5)
#        col = split.column()
#        col.label(text="Mass(kg)")
#        col.prop(settings, "rigid_mass", text="")
#        col = split.column()
#        col.label(text="Damping")
#        col.prop(settings, "rigid_damping", text="", slider=True)
        
        col = layout.column()
        split = col.split(factor=0.5)
        col = split.column()
        col.label(text="Basename")
        col = split.column()
        col.prop(settings, "basename", text="")
        
        row = layout.row()
        row.label(text="Rigid Size Type")
        row = layout.row()
        row.prop(settings, "rigid_size_type",expand=True)
        col = layout.column()
        split = col.split(factor=0.5)
        col = split.column()
        col.label(text="Width")
        col.prop(settings, "rigid_width", text="")
        col = split.column()
        col.label(text="Thickness")
        col.prop(settings, "rigid_thickness", text="")

        
        if settings.h_num * settings.v_num<=nc_num_limit:
            layout.prop(settings, "disable_self_collision")

        layout.prop(settings, "enable_angle_limit")
        if settings.enable_angle_limit:
            row = layout.row()
            row.label(text="Angle Limit (accumulated)")
            row = layout.row()
            row.prop(settings, "rigid_circ_angle", text="Circ Angle")
            row = layout.row()
            row.prop(settings, "rigid_rad_angle_in", text="Radial Angle In")
            row = layout.row()
            row.prop(settings, "rigid_rad_angle_out", text="Radial Angle Out")
            
            row = layout.row()
            row.label(text="Angle Limit Type")
            row = layout.row()
            row.prop(settings, "angle_limit_type",expand=True)
            layout.separator()  # Adds a horizontal line
            
        layout.prop(settings, "enable_chain_spring")
        if settings.enable_chain_spring:
            col = layout.column()
            split = col.split(factor=0.5)
            col = split.column()
            col.label(text="Stiffness")
            col.prop(settings, "chain_spring_stiffness", text="")
            col = split.column()
            col.label(text="Damping")
            col.prop(settings, "chain_spring_damping", text="")
            
        layout.prop(settings, "enable_horizontal_spring")
        if settings.enable_horizontal_spring:
            col = layout.column()
            split = col.split(factor=0.5)
            col = split.column()
            col.label(text="Stiffness")
            col.prop(settings, "horizontal_spring_stiffness",text='')
            col = split.column()
            col.label(text="Damping")
            col.prop(settings, "horizontal_spring_damping",text='')
            
        row = layout.row()
        row.scale_y = 2.0
        row.operator("skirt_rigid_gen.create_rigid_from_guide_mesh", text="Generate Rigid Body")

class CreateGuideMeshOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.create_guide_mesh"
    bl_label = "create guide mesh"

    def execute(self, context):
        create_guide_mesh(context)
        return {'FINISHED'}
    

class CreateRigidFromGuideMeshOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.create_rigid_from_guide_mesh"
    bl_label = "create rigid from guide mesh"

    def execute(self, context):
        create_rigid_from_guide_mesh(context)
        return {'FINISHED'}

    
class ClearAllOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.clear_all"
    bl_label = "Clear All"
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        all_obj = bpy.data.objects
        for obj in all_obj:
            if obj.get('is_skirt_rigid_gen'):
                bpy.data.objects.remove(obj, do_unlink=True)
        # TODO:also check for rigid body collection
        return {'FINISHED'}

class HideAllOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.hide_all"
    bl_label = "Hide All"
    
    def execute(self, context):
        all_obj = bpy.data.objects
        for obj in all_obj:
            if obj.get('is_skirt_rigid_gen'):
                obj.hide_viewport = True
        return {'FINISHED'}

class ShowAllOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.show_all"
    bl_label = "Show All"

    def execute(self, context):
        all_obj = bpy.data.objects
        for obj in all_obj:
            if obj.get('is_skirt_rigid_gen'):
                obj.hide_viewport = False
                obj.hide_set(False)
        return {'FINISHED'}
    

class ToolPanel(bpy.types.Panel):
    """Creates a panel in the 3D Viewport"""
    bl_label = "Tool"
    bl_idname = "VIEW3D_PT_OIMOYU_SKIRT_RIGID_TOOL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Skirt Rigid Gen"
    
    def draw(self, context):
        layout = self.layout
        layout.operator("skirt_rigid_gen.generate_bone_rigid", text="Generate Bone rigid")
        col = layout.column()
        split = col.split(factor=0.5)
        col = split.column()
        col.operator("skirt_rigid_gen.show_all", text="Show All", icon="HIDE_OFF")
        col = split.column()
        col.operator("skirt_rigid_gen.hide_all", text="Hide All", icon="HIDE_ON")
        layout.operator("skirt_rigid_gen.clear_all", text="Clear All", icon="X")
        


class VGTransferOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.vg_transfer"
    bl_label = "Transfer Vertex Group"
    obj_name: bpy.props.StringProperty()
    armature_obj_name: bpy.props.StringProperty()
    def execute(self, context):
        obj = bpy.data.objects[self.obj_name]
        armature_obj = bpy.data.objects[self.armature_obj_name]
        bone_name_list = [bone.name for bone in armature_obj.data.bones]
        
        for bone_name in bone_name_list:
            if not obj.vertex_groups.get(bone_name):
                obj.vertex_groups.new(name=bone_name)
        
        return {'FINISHED'}
    
class VGCheckOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.vg_check"
    bl_label = "Check Vertex Group"
    obj_name: bpy.props.StringProperty()
    armature_obj_name: bpy.props.StringProperty()
    def execute(self, context):
        obj = bpy.data.objects[self.obj_name]
        armature_obj = bpy.data.objects[self.armature_obj_name]
        bone_name_list = [bone.name for bone in armature_obj.data.bones]
        
        # check if all armature bones vg is created
        for bone_name in bone_name_list:
            if not obj.vertex_groups.get(bone_name):
                ShowMessageBox("Some of the vertex groups are not created.", "NOT OK", 'X')
        
        vertex_index_list = []
        for vertex in obj.data.vertices:
            vertex_assigned = False
            
            # Check the groups this vertex belongs to
            for group in vertex.groups:
                if obj.vertex_groups[group.group].name in bone_name_list:
                    vertex_assigned = True
                    break
            
            # If this vertex is not assigned to any of the specified groups, set the flag
            if not vertex_assigned:
                vertex_index_list.append(vertex.index)

        if vertex_index_list:
            ShowMessageBox("Not all vertices are assigned to the specified vertex groups.", "NOT OK", 'X')
            
            bpy.ops.object.mode_set(mode = 'OBJECT')
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode = 'EDIT') 
            bpy.ops.mesh.select_mode(type="VERT")
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.object.mode_set(mode = 'OBJECT')

            for vertex_index in vertex_index_list:
                obj.data.vertices[vertex_index].select = True

            bpy.ops.object.mode_set(mode='EDIT')

        else:
            ShowMessageBox("All vertices are assigned to at least one of the specified vertex groups.", "OK", 'FUND')
        
        return {'FINISHED'}
    
class VGTransferToolPanel(bpy.types.Panel):
    bl_label = "VG Transfer Tool"
    bl_idname = "VIEW3D_PT_OIMOYU_SKIRT_RIGID_VG_TRANSFER_TOOL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Skirt Rigid Gen"
    
    def draw(self, context):
        layout = self.layout
        obj_list = bpy.context.selected_objects

        mesh_obj = None
        armature_obj = None
        for obj in obj_list:
            if obj.type == 'MESH':
                mesh_obj = obj
            if obj.type == 'ARMATURE':
                armature_obj = obj
            
        if len(obj_list) == 2 and mesh_obj and armature_obj:
            row = layout.row()
            row.label(text=f"Mesh: {mesh_obj.name}")
            row = layout.row()
            row.label(text=f"Armature: {armature_obj.name}")
            op = layout.operator("skirt_rigid_gen.vg_transfer", text="Transfer Vertex Group")
            op.obj_name = mesh_obj.name
            op.armature_obj_name = armature_obj.name
            
#            op = layout.operator("skirt_rigid_gen.vg_check", text="Check Vertex Group")
#            op.obj_name = mesh_obj.name
#            op.armature_obj_name = armature_obj.name
            
        else:
            layout.label(text='Plear select one mesh obj and one armature obj to transfer vertex group')

def update_disable_self_collision(self,context):
    if self.v_num * self.h_num > nc_num_limit:
        self.disable_self_collision = False

class GenerateBoneRigidOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.generate_bone_rigid"
    bl_label = "Generate Bone Rigid"
    def execute(self, context):
        armature_obj = bpy.context.active_object
        if not armature_obj or armature_obj.type != 'ARMATURE':
            ShowMessageBox("no object selected.", "error message", 'ERROR')
            return {'FINISHED'}
        pose_bone = bpy.context.active_pose_bone
        if not pose_bone:
            ShowMessageBox("no bone selected.", "error message", 'ERROR')
            return {'FINISHED'}
        
        # length and direction of the bone
        length = (pose_bone.head - pose_bone.tail).length
        bpy.ops.mesh.primitive_cube_add(size=length, enter_editmode=False, align='WORLD')
        rigid_obj = bpy.context.active_object
        rigid_obj['is_skirt_rigid_gen'] = True
        rigid_obj['skirt_rigid_type'] = 'bone_rigid'
        rigid_obj.name = 'bone_rigid'
        
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
        
#        rigid_obj.location =  (pose_bone.head + pose_bone.tail) / 2
        
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
        
        # set collection
        main_collection, rigid_joint_collection = init_collection()
        
        # apply scale
        apply_scale(rigid_obj)
        
        return {'FINISHED'}

def get_select_rigid_body_list():
    return [temp for temp in bpy.context.selected_objects if temp.get('is_skirt_rigid_gen') and temp.rigid_body ]

def update_rigid_body_mass(self, context):
    select_rigid_body_list = get_select_rigid_body_list()
    for obj in select_rigid_body_list:
        obj.rigid_body.mass = context.scene.skirt_rigid_panel_settings.rigid_body_mass_temp
def update_rigid_body_friction(self, context):
    select_rigid_body_list = get_select_rigid_body_list()
    for obj in select_rigid_body_list:
        obj.rigid_body.friction = context.scene.skirt_rigid_panel_settings.rigid_body_friction_temp
        
def get_select_joint_list():
    return [temp for temp in bpy.context.selected_objects if temp.get('is_skirt_rigid_gen') and temp.rigid_body_constraint ]

def update_joint_stiffness(self, context):
    select_joint_list = get_select_joint_list()
    for obj in select_joint_list:
        chain_spring_stiffness = context.scene.skirt_rigid_panel_settings.chain_spring_stiffness_temp
        obj.rigid_body_constraint.spring_stiffness_ang_x = chain_spring_stiffness
        obj.rigid_body_constraint.spring_stiffness_ang_y = chain_spring_stiffness
        obj.rigid_body_constraint.spring_stiffness_ang_z = chain_spring_stiffness
    
def update_joint_damping(self, context):
    select_joint_list = get_select_joint_list()
    for obj in select_joint_list:
        chain_spring_damping = context.scene.skirt_rigid_panel_settings.chain_spring_damping_temp
        obj.rigid_body_constraint.spring_damping_ang_x = chain_spring_damping
        obj.rigid_body_constraint.spring_damping_ang_y = chain_spring_damping
        obj.rigid_body_constraint.spring_damping_ang_z = chain_spring_damping

    
class HandleRigidJointOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.handle_rigid_joint"
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
        if self.action == 'select':
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = None
            
        obj_list = [temp for temp in bpy.data.objects if temp.get('skirt_rigid_gen_id') == self.skirt_rigid_gen_id ]
        for obj in obj_list:
            if self.action == 'delete':
                bpy.data.objects.remove(obj, do_unlink=True)
                continue
            
            if self.action == 'select':
                if not self.obj_type:
                    obj.select_set(True)
                else:
                    if self.obj_type == 'all_joint' and 'joint' in obj.get('skirt_rigid_type', ''):
                        obj.select_set(True)
                        bpy.context.view_layer.objects.active = obj
                    else:
                        if obj.get('skirt_rigid_type') == self.obj_type:
                            obj.select_set(True)
                            bpy.context.view_layer.objects.active = obj
                continue
            
            if obj.type == 'ARMATURE':
                continue
            
            if self.action == 'show':
                obj.hide_viewport = False
                obj.hide_set(False)
                continue
#                # also set collection in case user set
#                if rigid_joint_collection_name in bpy.data.collections:
#                    rigid_joint_collection = bpy.data.collections[rigid_joint_collection_name]
#                    rigid_joint_collection.hide_viewport = False
#                    # there is no api for 'eye' button hide/show collection
                
            if self.action == 'hide':
                obj.hide_viewport = True
                continue

            
        return {'FINISHED'}

    
# TODO: check large select performance
class ModifyPanel(bpy.types.Panel):
    """Creates a panel in the 3D Viewport"""
    bl_label = "Modify"
    bl_idname = "VIEW3D_PT_OIMOYU_SKIRT_RIGID_MODIFY"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Skirt Rigid Gen"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.skirt_rigid_panel_settings
        
        selected_object_list = bpy.context.selected_objects
        selected_object_list = [temp for temp in selected_object_list if temp.get('is_skirt_rigid_gen') and temp.get('skirt_rigid_gen_id')]
        
        rigid_body_list = [temp for temp in selected_object_list if temp.rigid_body ]
        joint_list = [temp for temp in selected_object_list if temp.type == 'EMPTY' and temp.rigid_body_constraint ]
        
        selected_object_group = group_by_attr(selected_object_list, "skirt_rigid_gen_id")

        for skirt_rigid_gen_id, obj_list in selected_object_group.items():
            row = layout.row()
#            row.label(text=f"{obj_list[0].get('skirt_rigid_gen_basename')}: {len(obj_list)}")
            row.label(text=f"{obj_list[0].get('skirt_rigid_gen_basename')}")
            
            row = layout.row()
            op = row.operator('skirt_rigid_gen.handle_rigid_joint', text="", icon='HIDE_OFF')
            op.skirt_rigid_gen_id = skirt_rigid_gen_id
            op.action = 'show'
            
            op = row.operator('skirt_rigid_gen.handle_rigid_joint', text="", icon='HIDE_ON')
            op.skirt_rigid_gen_id = skirt_rigid_gen_id
            op.action = 'hide'
            
            op = row.operator('skirt_rigid_gen.handle_rigid_joint', text="", icon='RESTRICT_SELECT_OFF')
            op.skirt_rigid_gen_id = skirt_rigid_gen_id
            op.action = 'select'
            op.obj_type = ''

            op = row.operator('skirt_rigid_gen.handle_rigid_joint', text="", icon='X')
            op.skirt_rigid_gen_id = skirt_rigid_gen_id
            op.action = 'delete'
            
            row = layout.row()
            op = row.operator('skirt_rigid_gen.handle_rigid_joint', text="", icon='MESH_CUBE')
            op.skirt_rigid_gen_id = skirt_rigid_gen_id
            op.action = 'select'
            op.obj_type = 'rigid_body'
            op = row.operator('skirt_rigid_gen.handle_rigid_joint', text="", icon='EMPTY_AXIS')
            op.skirt_rigid_gen_id = skirt_rigid_gen_id
            op.action = 'select'
            op.obj_type = 'all_joint'
            op = row.operator('skirt_rigid_gen.handle_rigid_joint', text="", icon='EMPTY_AXIS')
            op.skirt_rigid_gen_id = skirt_rigid_gen_id
            op.action = 'select'
            op.obj_type = 'v_joint'
            op = row.operator('skirt_rigid_gen.handle_rigid_joint', text="", icon='EMPTY_AXIS')
            op.skirt_rigid_gen_id = skirt_rigid_gen_id
            op.action = 'select'
            op.obj_type = 'h_joint'
            op = row.operator('skirt_rigid_gen.handle_rigid_joint', text="", icon='EMPTY_AXIS')
            op.skirt_rigid_gen_id = skirt_rigid_gen_id
            op.action = 'select'
            op.obj_type = 'nc_joint'

            
#        if rigid_body_list:
#            layout.prop(settings, "rigid_body_mass_temp", text="Rigid Body Mass")
#            layout.prop(settings, "rigid_body_friction_temp")

#        if joint_list:
#            layout.prop(settings, "chain_spring_stiffness_temp")
#            layout.prop(settings, "chain_spring_damping_temp")

            
class SkirtRigidGenPanelSettings(bpy.types.PropertyGroup):
    h_num : bpy.props.IntProperty(name="horizonal segment number",min=1,default=3,update=update_disable_self_collision)
    v_num : bpy.props.IntProperty(name="vertical segment number",min=1,default=3,update=update_disable_self_collision)
    
    rigid_width : bpy.props.FloatProperty(name="rigid width",min=0.001,default=1)
    rigid_thickness : bpy.props.FloatProperty(name="rigid thickness",min=0.001,default=1)
    basename : bpy.props.StringProperty(name="basename",default='skirt')
    
    rigid_mass : bpy.props.FloatProperty(name="Rigid Mass",min=0.001,default=1.0)
    rigid_damping : bpy.props.FloatProperty(name="Rigid Damping",default=0.5,min=0,max=1)

    rigid_rad_angle_out : bpy.props.FloatProperty(name="Radial Angle Out",min=0,max=180,default=180, description="Angle limit outward along the radial direction")
    rigid_rad_angle_in : bpy.props.FloatProperty(name="Radial Angle In", min=0,max=180,default=45, description="Angle limit inward along the radial direction")
    rigid_circ_angle : bpy.props.FloatProperty(name="Circ Angle",min=0,max=90,default=45, description="Angular limits along the circumferential direction")
    enable_angle_limit : bpy.props.BoolProperty(name="Enable Angle Limit",description="Enable Angle Limit",default=False)

    angle_limit_type : bpy.props.EnumProperty(name="Angle Limit Type", items=(            
        ("constant", "Constant", ""),
        ("linear", "Linear", ""),
        ),
        default='constant',
        description="Angle limit change type"
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
    
    enable_chain_spring : bpy.props.BoolProperty(name="Enable Chain Spring",description="Enable Chain Spring",default=False)
    chain_spring_stiffness : bpy.props.FloatProperty(name="chain sping stiffness",min=0,default=10, description="Horizontal Spring Stiffness")
    chain_spring_damping : bpy.props.FloatProperty(name="chain sping damping",min=0,default=0.5, description="Horizontal Spring Damping")
    

    enable_horizontal_spring : bpy.props.BoolProperty(name="Enable Horizontal Spring",description="Enable Horizontal Spring",default=False)
    horizontal_spring_stiffness : bpy.props.FloatProperty(name="sping stiffness",min=0,default=10, description="Horizontal Spring Stiffness")
    horizontal_spring_damping : bpy.props.FloatProperty(name="sping damping",min=0,default=0.5, description="Horizontal Spring Damping")
    
    disable_self_collision : bpy.props.BoolProperty(
    name="Disable Self Collistion",default=False, description="This option can only be enabled when the number of rigid bodies is less than 32")
    
    
    rigid_body_mass_temp : bpy.props.FloatProperty(name="Temp Rigid Body Mass", default=1.0, min=0.0,update=update_rigid_body_mass)
    rigid_body_friction_temp : bpy.props.FloatProperty(name="Temp Rigid Body Friction", default=0.5, min=0.0, max=1,update=update_rigid_body_friction)
    
    chain_spring_stiffness_temp : bpy.props.FloatProperty(name="Temp Chain Spring Stiffness", default=1.0, min=0.0,update=update_joint_stiffness)
    chain_spring_damping_temp : bpy.props.FloatProperty(name="Temp Chain Spring Damping", default=0.5, min=0.0,update=update_joint_damping)


classes = (
    SkirtRigidGenPanelSettings,
    GeneratePanel,
    CreateGuideMeshOperator,
    CreateRigidFromGuideMeshOperator,
    ToolPanel,
    HandleRigidJointOperator,
    ModifyPanel,
    VGTransferOperator,
    VGTransferToolPanel,
    ClearAllOperator,
    VGCheckOperator,
    GenerateBoneRigidOperator,
    HideAllOperator,
    ShowAllOperator
)
    
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    # Add the property group to bpy.types.Scene using a PointerProperty
    bpy.types.Scene.skirt_rigid_panel_settings = bpy.props.PointerProperty(type=SkirtRigidGenPanelSettings)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    del bpy.types.Scene.skirt_rigid_panel_settings


if __name__ == "__main__":
    
    register()




