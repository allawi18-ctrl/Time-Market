import bpy, os, sys

args = sys.argv[sys.argv.index('--') + 1:]
fbx_path = os.path.abspath(args[0])
out_path = os.path.abspath(args[1])
textures_dir = os.path.abspath(os.path.join(os.path.dirname(fbx_path), '..', 'Textures'))

bpy.ops.wm.read_factory_settings(use_empty=True)
# Keep the original FBX bone axes. Automatic reorientation can invalidate the
# legacy Rocketbox skin bind matrices when re-exporting to glTF.
bpy.ops.import_scene.fbx(
    filepath=fbx_path,
    use_image_search=False,
    automatic_bone_orientation=False,
    use_prepost_rot=True,
)

armatures = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
if not armatures:
    raise RuntimeError('No armature')
arm = max(armatures, key=lambda o: len(o.data.bones))
print('ARMATURE', arm.name, 'BONES', len(arm.data.bones))

prefix = None
for mat in bpy.data.materials:
    if mat and '_' in mat.name:
        p = mat.name.split('_', 1)[0].lower()
        if len(p) == 4 and p[0] in ('m','f'):
            prefix = p
            break
if not prefix:
    raise RuntimeError('No texture prefix')
print('PREFIX', prefix)


def image(name, noncolor=False):
    path = os.path.join(textures_dir, name)
    if not os.path.exists(path):
        print('MISSING', path)
        return None
    img = bpy.data.images.load(path, check_existing=True)
    if noncolor:
        try: img.colorspace_settings.name = 'Non-Color'
        except Exception: pass
    return img

body_c = image(f'{prefix}_body_color.tga')
body_n = image(f'{prefix}_body_normal.tga', True)
head_c = image(f'{prefix}_head_color.tga')
head_n = image(f'{prefix}_head_normal.tga', True)
opacity = image(f'{prefix}_opacity_color.tga')


def pbr(mat, kind):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    bsdf.inputs['Roughness'].default_value = .58 if kind != 'opacity' else .72
    bsdf.inputs['Metallic'].default_value = 0
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = .22
    cimg, nimg = (head_c, head_n) if kind == 'head' else ((body_c, body_n) if kind == 'body' else (opacity, None))
    if cimg:
        tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = cimg
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        if kind == 'opacity': nt.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
    if nimg:
        texn = nt.nodes.new('ShaderNodeTexImage'); texn.image = nimg
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = .42
        nt.links.new(texn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    try:
        mat.blend_method = 'CLIP' if kind == 'opacity' else 'OPAQUE'
        mat.alpha_threshold = .28
    except Exception: pass

for mat in bpy.data.materials:
    if not mat: continue
    n = mat.name.lower()
    pbr(mat, 'head' if '_head' in n else ('opacity' if '_opacity' in n else 'body'))

# Ensure no accidental imported animation affects the exported rest pose.
for obj in bpy.context.scene.objects:
    if obj.animation_data:
        obj.animation_data_clear()
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)
bpy.context.scene.frame_set(0)

bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH': obj.select_set(True)

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
    export_animations=False,
    export_image_format='AUTO',
)
print('EXPORTED_STATIC_NOAUTO', out_path, os.path.getsize(out_path))
