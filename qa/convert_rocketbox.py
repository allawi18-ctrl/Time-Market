import bpy, os, sys

args = sys.argv[sys.argv.index('--') + 1:]
fbx_path, out_path = [os.path.abspath(x) for x in args[:2]]
textures_dir = os.path.abspath(os.path.join(os.path.dirname(fbx_path), '..', 'Textures'))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx_path, use_image_search=True, automatic_bone_orientation=True)

# Repair external texture paths and keep the useful high-resolution skin/clothes maps.
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

# Make imported legacy materials react naturally to modern PBR lighting.
for mat in bpy.data.materials:
    if not mat:
        continue
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF') if mat.node_tree else None
    if bsdf:
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = 0.62
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = 0.0
        if 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.28

# Normalize transforms without destroying the armature.
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.select_set(True)

os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    export_yup=True,
    export_apply=False,
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
    export_animations=False,
    export_image_format='AUTO'
)
print('EXPORTED', out_path, os.path.getsize(out_path))
