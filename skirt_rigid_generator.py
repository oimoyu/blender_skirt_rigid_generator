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


def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)
    

def paint_pin_weight(conte):
    # Get the active object and the selected vertices
    obj = bpy.context.active_object
    selected_verts = [v.index for v in obj.data.vertices if v.select]


    root_vertex_group = obj.vertex_groups.get('root')
    if not root_vertex_group:
        root_vertex_group = obj.vertex_groups.new(name=f"root")
        
    pin_vertex_group = obj.vertex_groups.get('pin')
    pin_vertex_id_list = [v.index for v in obj.data.vertices if pin_vertex_group.index in [vg.group for vg in v.groups]]

    pin_vertex_weight_list = []
    for v in obj.data.vertices:
        index = v.index
        if index in pin_vertex_id_list:
            weight = pin_vertex_group.weight(index)
            pin_vertex_weight_list.append(weight)

    pin_vertex_weight_list = [temp for temp in pin_vertex_weight_list]

    # delete pin for all vg
    for vertex_index, vertex_weight in zip(pin_vertex_id_list,pin_vertex_weight_list):
        for vg in obj.vertex_groups:
            if vg.name == 'pin':
                continue
            if not vg.name.startswith('b_'):
                continue
        
            try:
                ori_weight = vg.weight(vertex_index)
            except:
                continue
            pin_weight = vertex_weight
            reverse_weight = 1 - pin_weight
            vg.add(index=[vertex_index],weight=min(reverse_weight,ori_weight),type='REPLACE')
            
           
    # add pin to root
    for vertex_index, vertex_weight in zip(pin_vertex_id_list,pin_vertex_weight_list):
        root_vertex_group.add(index=[vertex_index],weight=vertex_weight,type='REPLACE')


def create_guide_mesh(context):
    settings = context.scene.skirt_rigid_panel_settings
    circle_seg_num = settings.h_num
    radius = 1.0
    height = 1
    verticle_seg_num = settings.v_num

    vertex_num = circle_seg_num * (verticle_seg_num+1)
    
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except:
        pass
    bpy.ops.object.select_all(action='DESELECT')
        
    # create a new mesh object
    mesh = bpy.data.meshes.new("GuideMesh")
    obj = bpy.data.objects.new("GuideMeshObject", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (0, 0, 0)

    # create a new circle
    circle_vertices = []
    circle_edges = []
    circle_faces = []

    for i in range(circle_seg_num):
        theta = i / circle_seg_num * 2 * 3.14159
        x = radius * math.cos(theta)
        y = radius * math.sin(theta)
        circle_vertices.append((x, y, 0))

    for i in range(circle_seg_num):
        circle_edges.append((i, (i + 1) % circle_seg_num))

    # assign geometry to the mesh object
    mesh.from_pydata(circle_vertices, circle_edges, circle_faces)
    mesh.update()

    bpy.context.view_layer.objects.active = obj
    # extrude the circle
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='VERT')
    bpy.ops.mesh.select_all(action='SELECT')
    for i in range(verticle_seg_num):
        height_temp = height / verticle_seg_num
        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":(0, 0, -height_temp)})
        scale_factor = 1.03
        bpy.ops.transform.resize(value=(scale_factor,scale_factor,scale_factor))
        
        

    bpy.ops.object.mode_set(mode='OBJECT')
    # assign vertex group
    line_vertex_list = []
    pin_vg = obj.vertex_groups.new(name='pin')
    for i in range(circle_seg_num):
        temp_list = []
        for j in range(verticle_seg_num+1):
            vertex_id = j*circle_seg_num+i
            vertex = obj.data.vertices[vertex_id]
            
            vg = obj.vertex_groups.new(name=f"b_{i}_{j}")
            vg.add([vertex.index], 1.0, 'ADD')
            
            if j==0:
                pin_vg.add([vertex.index], 1.0, 'ADD')
                
            temp_list.append(vertex)
        line_vertex_list.append(temp_list)
    
    # Flip the normals
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.flip_normals()


    obj = bpy.context.object
    obj["is_guidemesh"] = True

    
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(True)
    return obj


def create_rigid_from_guide_mesh(context):
    settings = context.scene.skirt_rigid_panel_settings
    width_factor = settings.rigid_width
    thickness_factor = settings.rigid_thickness
    rigid_mass = settings.rigid_mass
    rigid_damping = settings.rigid_damping
    rigid_rad_angle_out = settings.rigid_rad_angle_out
    rigid_rad_angle_in = settings.rigid_rad_angle_in
    rigid_circ_angle = settings.rigid_circ_angle
    angle_limit_type = settings.angle_limit_type
    enable_horizontal_spring = settings.enable_horizontal_spring
    horizontal_spring_stiffness = settings.horizontal_spring_stiffness
    horizontal_spring_damping = settings.horizontal_spring_damping
    disable_self_collision = settings.disable_self_collision
        
    selected_objects = bpy.context.selected_objects

    bpy.context.scene.frame_set(0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    if not selected_objects:
        ShowMessageBox("No object selected", "error message", 'ERROR')
        return 
    guide_mesh_obj = selected_objects[-1]
    
    if not guide_mesh_obj.get('is_guidemesh'):
        ShowMessageBox("Not guidemesh selected", "error message", 'ERROR')
        return 

    vg_idx_name_dict = {vg.index: vg.name for vg in guide_mesh_obj.vertex_groups}
    vg_name_list = [temp for temp in vg_idx_name_dict.values()]
    circle_seg_num = max([int(re.search(r'b_(\d+)_(\d+)',temp).group(1)) for temp in vg_name_list if temp.startswith("b_")]) + 1
    verticle_seg_num = max([int(re.search(r'b_(\d+)_(\d+)',temp).group(2)) for temp in vg_name_list if temp.startswith("b_")])


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
    armature = bpy.data.armatures.new(name='Armature_cloth')
    armature_obj = bpy.data.objects.new('Armature_cloth', armature)
    # Add the armature object to the scene
    bpy.context.scene.collection.objects.link(armature_obj)


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
            bone = armature.edit_bones.new(name=f'b_{i}_{j}')
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

    # add root bone at last
    bone = armature.edit_bones.new(name=f'root')
    bone.head = (0,0,0)
    bone.tail = (0,0,1)


    # create joint and rigid
    bpy.ops.object.mode_set(mode='EDIT')
    joint_v_obj_list = []
    rigid_obj_list = []
    for i in range(len(line_vertex_list)):
        vertex_list = line_vertex_list[i]
        for j in range(len(vertex_list)-1):
            temp_id = j*circle_seg_num+i
            vertex = guide_mesh_obj.data.vertices[temp_id]
            
            bone = armature.edit_bones[f'b_{i}_{j}']
            start_coord = bone.head
            end_coord = bone.tail
            mid_coord = (start_coord + end_coord)/2
            
            length = (start_coord - end_coord).length
            width = width_factor * length
            thickness = thickness_factor * length

            bone_x_axis = bone.x_axis
            bone_y_axis = bone.y_axis
            bone_z_axis = bone.z_axis

            if j !=0 :
                #joint
                joint_obj = bpy.data.objects.new(f"joint_{i}_{j}", None)
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

            # Create a new mesh for the cuboid
            mesh = bpy.data.meshes.new(f"r_{i}_{j}_mesh")
            # Create a new cuboid object
            rigid_obj = bpy.data.objects.new(f"r_{i}_{j}", mesh)
            
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

        if re.search(r"_(\d+)_0",rigid_obj.name):
            bpy.ops.rigidbody.objects_add(type='PASSIVE')
            rigid_obj.rigid_body.kinematic = True
        else:
            bpy.ops.rigidbody.objects_add(type='ACTIVE')
            
        rigid_obj.rigid_body.mass = rigid_mass
        rigid_obj.rigid_body.linear_damping = rigid_damping
        rigid_obj.rigid_body.angular_damping = rigid_damping



    # add vertical rigid_constraint
    bpy.ops.object.mode_set(mode='OBJECT')
    for joint_obj in joint_v_obj_list:
        bpy.ops.object.select_all(action='DESELECT')
        rigid_obj.select_set(True)
        bpy.context.view_layer.objects.active = joint_obj
        
        i = int(re.search(r"joint_(\d+)_(\d+)", joint_obj.name).group(1))
        j = int(re.search(r"joint_(\d+)_(\d+)", joint_obj.name).group(2))

        ramp_factor = j / (verticle_seg_num-1)
        
        if angle_limit_type == 'constant':
            rigid_rad_angle_out_single = rigid_rad_angle_out / (verticle_seg_num-1)
            rigid_rad_angle_in_single = rigid_rad_angle_in / (verticle_seg_num-1)
            rigid_circ_angle_single = rigid_circ_angle / (verticle_seg_num-1)
        elif angle_limit_type == 'linear':
            const_n = (verticle_seg_num-1)
            total_n = const_n + ( const_n * (const_n-1) ) / 2
            current_weight = verticle_seg_num-1 - j
            current_weight = j
            rigid_rad_angle_out_single = rigid_rad_angle_out * current_weight / total_n
            rigid_rad_angle_in_single = rigid_rad_angle_in * current_weight / total_n
            rigid_circ_angle_single = rigid_circ_angle * current_weight / total_n
        else:
            raise Exception("unknow type")
        
        bpy.ops.rigidbody.constraint_add(type='GENERIC_SPRING')
        bpy.context.object.rigid_body_constraint.use_limit_ang_x = True
        bpy.context.object.rigid_body_constraint.use_limit_ang_y = True
        bpy.context.object.rigid_body_constraint.use_limit_ang_z = True
        bpy.context.object.rigid_body_constraint.limit_ang_x_lower = -rigid_circ_angle_single/180*math.pi
        bpy.context.object.rigid_body_constraint.limit_ang_x_upper = rigid_circ_angle_single/180*math.pi
        bpy.context.object.rigid_body_constraint.limit_ang_y_lower = 0
        bpy.context.object.rigid_body_constraint.limit_ang_y_upper = 0
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

#    bpy.ops.object.mode_set(mode='OBJECT')
    pose_bone_list = armature_obj.pose.bones
    joint_h_obj_list = []
    for i in range(len(line_vertex_list)):
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
                
            l_vertex = guide_mesh_obj.data.vertices[l_id]
            r_vertex = guide_mesh_obj.data.vertices[r_id]
            l_j = j
            r_j = j
    
            mid_coord = (r_vertex.co + vertex.co)/2
            bone = armature.edit_bones[f'b_{i}_{j}']
            r_bone = armature.edit_bones[f'b_{r_i}_{r_j}']
        
            
            # create joint
            joint_obj = bpy.data.objects.new(f"joint_{i}_{j}&{r_i}_{r_j}", None)
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
    print(disable_self_collision)
    if disable_self_collision:
        for i1 in range(len(line_vertex_list)):
            for j1 in range(len(vertex_list)-1):
                for i2 in range(len(line_vertex_list)):
                    for j2 in range(len(vertex_list)-1):
                        # create joint
                        joint_obj = bpy.data.objects.new(f"nc_{i1}_{j1}&{i2}_{j2}", None)
                        nc_joint_obj_list.append(joint_obj)
                        
                        joint_obj.empty_display_type = 'ARROWS'
                        joint_obj.empty_display_size = 0.1
                        
                        scene = bpy.context.scene
                        scene.collection.objects.link(joint_obj)
            
    
    # parent joint
    for joint_obj in joint_v_obj_list:
        joint_obj.parent = armature_obj
        constraint = joint_obj.constraints.new('CHILD_OF')
        constraint.target = armature_obj
        constraint.subtarget = 'root'
        constraint.set_inverse_pending = True
        
    for joint_obj in joint_h_obj_list:
        joint_obj.parent = armature_obj
        constraint = joint_obj.constraints.new('CHILD_OF')
        constraint.target = armature_obj
        constraint.subtarget = 'root'
        constraint.set_inverse_pending = True
        
    for joint_obj in nc_joint_obj_list:
        joint_obj.parent = armature_obj
        
    # parent rigid
    for rigid_obj in rigid_obj_list:
        rigid_obj.parent = armature_obj
        constraint = rigid_obj.constraints.new('CHILD_OF')
        constraint.target = armature_obj
        constraint.subtarget = 'root'
        constraint.set_inverse_pending = True

    # add non collision rigid_constraint
    bpy.ops.object.mode_set(mode='OBJECT')
    for joint_obj in nc_joint_obj_list:
        bpy.ops.object.select_all(action='DESELECT')
        rigid_obj.select_set(True)
        bpy.context.view_layer.objects.active = joint_obj
        i1 = int(re.search(r"nc_(\d+)_(\d+)", joint_obj.name).group(1))
        j1 = int(re.search(r"nc_(\d+)_(\d+)", joint_obj.name).group(2))
        i2 = int(re.search(r"nc_\d+_\d+&(\d+)_(\d+)", joint_obj.name).group(1))
        j2 = int(re.search(r"nc_\d+_\d+&(\d+)_(\d+)", joint_obj.name).group(2))
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
            bpy.context.object.rigid_body_constraint.spring_stiffness_z = horizontal_spring_stiffness
            bpy.context.object.rigid_body_constraint.spring_damping_x = horizontal_spring_damping
            bpy.context.object.rigid_body_constraint.spring_damping_z = horizontal_spring_damping
    
    collection_name = "rigid&joint"
    if collection_name in bpy.data.collections:
        rigid_joint_collection = bpy.data.collections[collection_name]
    else:
        rigid_joint_collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(rigid_joint_collection)
    
    master_collection = bpy.context.scene.collection


    # last hide joint and rigid
    for joint_obj in joint_v_obj_list:
        joint_obj.hide_set(True)
        rigid_joint_collection.objects.link(joint_obj)
        master_collection.objects.unlink(joint_obj)
        
    for joint_obj in joint_h_obj_list:
        joint_obj.hide_set(True)
        rigid_joint_collection.objects.link(joint_obj)
        master_collection.objects.unlink(joint_obj)
        
    for joint_obj in nc_joint_obj_list:
        joint_obj.hide_set(True)
        rigid_joint_collection.objects.link(joint_obj)
        master_collection.objects.unlink(joint_obj)
        
    for rigid_obj in rigid_obj_list:
        rigid_obj.hide_set(True)
        rigid_joint_collection.objects.link(rigid_obj)
        master_collection.objects.unlink(rigid_obj)






bl_info = {
    "name": "Skit Rigid Generator",
    "author": "Oimoyu",
    "version": (1, 2),
    "blender": (3, 2, 2),
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
        layout.operator("skirt_rigid_gen.create_guide_mesh", text="Generate Guid Mesh")
        layout.separator()  # Adds a horizontal line
        
        col = layout.column()
        split = col.split(factor=0.5)
        # Add input boxes to the first column
        col = split.column()
        col.label(text="Mass(kg)")
        col.prop(settings, "rigid_mass", text="")
        col = split.column()
        col.label(text="Damping")
        col.prop(settings, "rigid_damping", text="", slider=True)
        
        col = layout.column()
        split = col.split(factor=0.5)
        # Add input boxes to the first column
        col = split.column()
        col.label(text="Width")
        col.prop(settings, "rigid_width", text="")
        col = split.column()
        col.label(text="Thickness")
        col.prop(settings, "rigid_thickness", text="")
        layout.separator()  # Adds a horizontal line
        
        if settings.h_num * settings.v_num<=32:
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
        
        layout.prop(settings, "enable_horizontal_spring")
        if settings.enable_horizontal_spring:
            layout.prop(settings, "horizontal_spring_stiffness")
            layout.prop(settings, "horizontal_spring_damping")
        layout.separator()  # Adds a horizontal line
        
        layout.operator("skirt_rigid_gen.create_rigid_from_guide_mesh", text="Generate Rigid Body")

class EnableSelfCollision(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.enable_self_collision"
    bl_label = "enable self_collision"
    def execute(self, context):
        context.scene.skirt_rigid_panel_settings.disable_self_collision = False
        return {'FINISHED'}

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
    
class PaintPinWeightOperator(bpy.types.Operator):
    bl_idname = "skirt_rigid_gen.paint_pin_weight"
    bl_label = "Paint Pin Weight"
    def execute(self, context):
        paint_pin_weight(context)
        return {'FINISHED'}
    
class ModifyPanel(bpy.types.Panel):
    """Creates a panel in the 3D Viewport"""
    bl_label = "Modify"
    bl_idname = "VIEW3D_PT_OIMOYU_SKIRT_RIGID_MODIFY"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Skirt Rigid Gen"
    
    def draw(self, context):
        layout = self.layout
        layout.operator("skirt_rigid_gen.paint_pin_weight", text="Paint Pin Weight")

def update_disable_self_collision(self,context):
    if self.v_num * self.h_num > 32:
        self.disable_self_collision = False

        
class SkirtRigidGenPanelSettings(bpy.types.PropertyGroup):
    h_num : bpy.props.IntProperty(name="horizonal segment number",min=3,default=5,update=update_disable_self_collision)
    v_num : bpy.props.IntProperty(name="vertical segment number",min=2,default=5,update=update_disable_self_collision)
    
    rigid_width : bpy.props.FloatProperty(name="rigid width",min=0.001,default=1)
    rigid_thickness : bpy.props.FloatProperty(name="rigid thickness",min=0.001,default=1)
    
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

    enable_horizontal_spring : bpy.props.BoolProperty(name="Enable Horizontal Spring",description="Enable Horizontal Spring",default=False)
    horizontal_spring_stiffness : bpy.props.FloatProperty(name="sping stiffness",min=0,default=1000, description="Horizontal Spring Stiffness")
    horizontal_spring_damping : bpy.props.FloatProperty(name="sping damping",min=0,default=1000, description="Horizontal Spring Damping")
    
    disable_self_collision : bpy.props.BoolProperty(
    name="Disable Self Collistion",default=False, description="This option can only be enabled when the number of rigid bodies is less than 32")

    
    
def register():
    bpy.utils.register_class(SkirtRigidGenPanelSettings)
    # Add the property group to bpy.types.Scene using a PointerProperty
    bpy.types.Scene.skirt_rigid_panel_settings = bpy.props.PointerProperty(type=SkirtRigidGenPanelSettings)

    bpy.utils.register_class(GeneratePanel)
    bpy.utils.register_class(CreateGuideMeshOperator)
    bpy.utils.register_class(CreateRigidFromGuideMeshOperator)
    bpy.utils.register_class(PaintPinWeightOperator)

    bpy.utils.register_class(ModifyPanel)


def unregister():
    bpy.utils.unregister_class(GeneratePanel)
    bpy.utils.unregister_class(CreateGuideMeshOperator)
    bpy.utils.unregister_class(CreateRigidFromGuideMeshOperator)
    bpy.utils.unregister_class(PaintPinWeightOperator)
    
    del bpy.types.Scene.skirt_rigid_panel_settings
    
    bpy.utils.unregister_class(ModifyPanel)
    
if __name__ == "__main__":
    register()






