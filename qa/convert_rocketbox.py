import bpy, os, sys, re

args = sys.argv[sys.argv.index('--') + 1:]
fbx_path = os.path.abspath(args[0])
out_path = os.path.abspath(args[1])
walk_path = os.path.abspath(args[2]) if len(args) > 2 and args[2] else None
run_path = os.path.abspath(args[3]) if len(args) > 3 and args[3] else None
textures_dir = os.path.abspath(os.path.join(os.path.dirname(fbx_path), '..', 'Textures'))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx_path, use_image_search=True, automatic_bone_orientation=True)

avatar_armatures = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
if not avatar_armatures:
    raise RuntimeError('No avatar armature found')
avatar_arm = max(avatar_armatures, key=lambda o: len(o.data.bones))
print('AVATAR_ARMATURE', avatar_arm.name, 'BONES', len(avatar_arm.data.bones))
print('ROOT_BONES', [b.name for b in avatar_arm.data.bones if b.parent is None])

# Repair external texture paths.
for img in bpy.data.images:
    if not img or img.name == 'Render Result':
        continue
    raw = bpy.path.abspath(img.filepath) if img.filepath else ''
    if raw and os.path.exists(raw):
        continue
    base = os.path.basename(raw or img.name)
    cand = os.path.join(textures_dir, base)
    if os.path.exists(cand):
        img.filepath = cand
        try:
            img.reload()
        except Exception:
            pass

# Rocketbox's legacy opacity maps were being interpreted as transparent stripes on
# clothes/body in WebGL. Force opaque PBR for body/clothes; preserve alpha clipping
# only for obvious hair/eyelash materials.
for mat in bpy.data.materials:
    if not mat:
        continue
    mat.use_nodes = True
    name = (mat.name or '').lower()
    alpha_surface = any(k in name for k in ('hair', 'lash', 'brow'))
    try:
        mat.blend_method = 'CLIP' if alpha_surface else 'OPAQUE'
        mat.alpha_threshold = 0.35
        mat.show_transparent_back = alpha_surface
    except Exception:
        pass
    bsdf = mat.node_tree.nodes.get('Principled BSDF') if mat.node_tree else None
    if bsdf:
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = 0.58
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = 0.0
        if 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.24
        if 'Alpha' in bsdf.inputs and not alpha_surface:
            alpha = bsdf.inputs['Alpha']
            for link in list(alpha.links):
                mat.node_tree.links.remove(link)
            alpha.default_value = 1.0
    print('MATERIAL', mat.name, 'ALPHA_SURFACE', alpha_surface)

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
    # Remove horizontal root motion. The game moves the character root itself.
    if root_name:
        for fc in list(action.fcurves):
            if fc.data_path == 'pose.bones["%s"].location' % root_name and fc.array_index in (0, 1):
                action.fcurves.remove(fc)
    # Imported animation helper armature is no longer needed; keep the Action datablock.
    for o in new_objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return action

walk_action = import_motion(walk_path, 'Walk')
run_action = import_motion(run_path, 'Run')

# Store clips as NLA tracks on the avatar armature so glTF exports named animation clips.
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

# Select only the avatar hierarchy before export.
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
