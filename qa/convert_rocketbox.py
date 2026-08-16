import bpy, os, sys

args = sys.argv[sys.argv.index('--') + 1:]
fbx_path = os.path.abspath(args[0])
out_path = os.path.abspath(args[1])
walk_path = os.path.abspath(args[2]) if len(args) > 2 and args[2] else None
run_path = os.path.abspath(args[3]) if len(args) > 3 and args[3] else None
textures_dir = os.path.abspath(os.path.join(os.path.dirname(fbx_path), '..', 'Textures'))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx_path, use_image_search=False, automatic_bone_orientation=True)

avatar_armatures = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
if not avatar_armatures:
    raise RuntimeError('No avatar armature found')
avatar_arm = max(avatar_armatures, key=lambda o: len(o.data.bones))
print('AVATAR_ARMATURE', avatar_arm.name, 'BONES', len(avatar_arm.data.bones))
print('ROOT_BONES', [b.name for b in avatar_arm.data.bones if b.parent is None])

prefix = None
for mat in bpy.data.materials:
    if mat and '_' in mat.name:
        p = mat.name.split('_', 1)[0].lower()
        if p.startswith(('m', 'f')) and len(p) == 4:
            prefix = p
            break
if not prefix:
    raise RuntimeError('Could not infer Rocketbox texture prefix')
print('TEXTURE_PREFIX', prefix)


def load_img(filename, non_color=False):
    path = os.path.join(textures_dir, filename)
    if not os.path.exists(path):
        print('MISSING_TEXTURE', path)
        return None
    img = bpy.data.images.load(path, check_existing=True)
    img.name = filename
    if non_color:
        try:
            img.colorspace_settings.name = 'Non-Color'
        except Exception:
            pass
    print('LOADED_TEXTURE', filename, img.size[:])
    return img

body_color = load_img(f'{prefix}_body_color.tga')
body_normal = load_img(f'{prefix}_body_normal.tga', True)
head_color = load_img(f'{prefix}_head_color.tga')
head_normal = load_img(f'{prefix}_head_normal.tga', True)
opacity_color = load_img(f'{prefix}_opacity_color.tga')


def rebuild_material(mat, kind):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    out.location = (520, 0)
    bsdf.location = (220, 0)
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    bsdf.inputs['Roughness'].default_value = 0.56 if kind in ('body', 'head') else 0.68
    bsdf.inputs['Metallic'].default_value = 0.0
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.22

    if kind == 'head':
        color_img, normal_img = head_color, head_normal
    elif kind == 'body':
        color_img, normal_img = body_color, body_normal
    else:
        color_img, normal_img = opacity_color, None

    if color_img:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = color_img
        tex.location = (-430, 90)
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        if kind == 'opacity':
            nt.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])

    if normal_img:
        texn = nt.nodes.new('ShaderNodeTexImage')
        texn.image = normal_img
        texn.location = (-430, -180)
        normal = nt.nodes.new('ShaderNodeNormalMap')
        normal.inputs['Strength'].default_value = 0.48
        normal.location = (-80, -170)
        nt.links.new(texn.outputs['Color'], normal.inputs['Color'])
        nt.links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])

    try:
        if kind == 'opacity':
            mat.blend_method = 'CLIP'
            mat.alpha_threshold = 0.28
            mat.show_transparent_back = True
        else:
            mat.blend_method = 'OPAQUE'
            mat.show_transparent_back = False
    except Exception:
        pass
    print('REBUILT_MATERIAL', mat.name, kind)


for mat in bpy.data.materials:
    if not mat:
        continue
    n = mat.name.lower()
    if '_head' in n:
        rebuild_material(mat, 'head')
    elif '_opacity' in n:
        rebuild_material(mat, 'opacity')
    else:
        rebuild_material(mat, 'body')

root_names = [b.name for b in avatar_arm.data.bones if b.parent is None]
root_name = root_names[0] if root_names else None


def import_motion(path, clip_name):
    if not path or not os.path.exists(path):
        print('MOTION_SKIPPED', clip_name, path)
        return None
    before_objs = set(bpy.data.objects)
    before_actions = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=path, use_image_search=False, automatic_bone_orientation=True)
    new_objs = [o for o in bpy.data.objects if o not in before_objs]
    new_actions = [a for a in bpy.data.actions if a not in before_actions]
    if not new_actions:
        print('NO_ACTION_FOUND', clip_name)
        for o in new_objs:
            bpy.data.objects.remove(o, do_unlink=True)
        return None
    action = max(new_actions, key=lambda a: len(a.fcurves))
    action.name = clip_name
    action.use_fake_user = True
    print('ACTION', clip_name, 'FCURVES', len(action.fcurves), 'RANGE', tuple(action.frame_range))

    if root_name:
        root_loc = f'pose.bones["{root_name}"].location'
        removed = 0
        for fc in list(action.fcurves):
            if fc.data_path == root_loc:
                action.fcurves.remove(fc)
                removed += 1
        print('REMOVED_ROOT_LOCATION_CURVES', clip_name, removed)

    removed_object = []
    for fc in list(action.fcurves):
        if fc.data_path == 'location':
            removed_object.append(fc.array_index)
            action.fcurves.remove(fc)
    for idx in removed_object:
        print('REMOVED_OBJECT_LOCATION_CURVE', clip_name, idx)

    for o in new_objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return action

walk_action = import_motion(walk_path, 'Walk')
run_action = import_motion(run_path, 'Run')

avatar_arm.animation_data_create()
avatar_arm.animation_data.action = None
for action in (walk_action, run_action):
    if not action:
        continue
    track = avatar_arm.animation_data.nla_tracks.new()
    track.name = action.name
    start = int(action.frame_range[0])
    strip = track.strips.new(action.name, start, action)
    strip.name = action.name
    strip.action_frame_start = action.frame_range[0]
    strip.action_frame_end = action.frame_range[1]

bpy.ops.object.select_all(action='DESELECT')
avatar_arm.select_set(True)
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.select_set(True)

os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_yup=True,
    export_apply=False,
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
    export_animations=True,
    export_nla_strips=True,
    export_image_format='AUTO'
)
print('EXPORTED', out_path, os.path.getsize(out_path))
