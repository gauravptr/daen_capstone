import bpy
import json
import os
from mathutils import Vector

"""
Combined: Assign materials + Export metadata
Run this in your scanned scene
"""

output_dir = r"C:\Users\jcwin\OneDrive\Desktop\Capstone\labeled_scans"
os.makedirs(output_dir, exist_ok=True)

scene_name = "BASE_scanned"

print("=" * 60)
print("   STEP 1: ASSIGNING MATERIALS")
print("=" * 60)

# Material mapping
MATERIAL_ASSIGNMENTS = {
    '00_seafloor': ['Plane'],
    '01_anomaly': ['Cube', 'Mball', 'tekne'],
    '02_coral': ['10010_Coral_v1_L3'],
    '03_rock': ['Rock', 'Mesh_0'],
    '04_wildlife': ['10042_Sea_Turtle'],
}

IGNORE_OBJECTS = ['Camera', 'Light', 'SonarPath', 'PathMarker', 'TextureField', 'real_values', 'noise_values']

# Create materials
material_colors = {
    '00_seafloor': (0.55, 0.27, 0.07),
    '01_anomaly': (1.0, 0.0, 0.0),
    '02_coral': (1.0, 0.41, 0.71),
    '03_rock': (0.5, 0.5, 0.5),
    '04_wildlife': (0.0, 1.0, 0.0),
}

for mat_name, color in material_colors.items():
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        output = nodes.new('ShaderNodeOutputMaterial')
        mat.node_tree.links.new(bsdf.outputs[0], output.inputs[0])

# Assign materials
assigned = 0
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    
    if any(ignore in obj.name for ignore in IGNORE_OBJECTS):
        continue
    
    for mat_name, prefixes in MATERIAL_ASSIGNMENTS.items():
        for prefix in prefixes:
            if obj.name.startswith(prefix):
                mat = bpy.data.materials[mat_name]
                obj.data.materials.clear()
                obj.data.materials.append(mat)
                assigned += 1
                print(f"  ✅ {obj.name} → {mat_name}")
                break

print(f"\n✅ Assigned materials to {assigned} objects")

# ============================================================
print("\n" + "=" * 60)
print("   STEP 2: EXPORTING SCAN + METADATA")
print("=" * 60)
# ============================================================

# Export scan points
scan_points = []
for obj in bpy.data.objects:
    if obj.type == 'MESH' and 'real_values' in obj.name:
        mesh = obj.data
        for v in mesh.vertices:
            world_co = obj.matrix_world @ v.co
            scan_points.append((world_co.x, world_co.y, world_co.z))

print(f"📊 Collected {len(scan_points):,} scan points")

xyz_path = os.path.join(output_dir, f"{scene_name}_scan.xyz")
with open(xyz_path, 'w') as f:
    for x, y, z in scan_points:
        f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")

print(f"✅ Exported scan: {xyz_path}")

# Export source object metadata with TIGHT bounding boxes
source_objects = []

for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    
    if any(x in obj.name for x in ['real_values', 'noise_values', 'PathMarker', 'SonarPath', 'Camera', 'Light']):
        continue
    
    # Get material/class
    class_id = None
    class_name = None
    
    if len(obj.material_slots) > 0 and obj.material_slots[0].material:
        mat = obj.material_slots[0].material
        if mat.name[0].isdigit() and '_' in mat.name:
            try:
                class_id = int(mat.name.split('_')[0])
                class_name = mat.name.split('_')[1]
            except:
                pass
    
    if class_id is None:
        continue
    
    # Get TIGHT bounding box using actual mesh vertices
    world_verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    
    min_x = min(v.x for v in world_verts)
    max_x = max(v.x for v in world_verts)
    min_y = min(v.y for v in world_verts)
    max_y = max(v.y for v in world_verts)
    min_z = min(v.z for v in world_verts)
    max_z = max(v.z for v in world_verts)
    
    source_objects.append({
        'name': obj.name,
        'class_id': class_id,
        'class_name': class_name,
        'bbox': {
            'min': [min_x, min_y, min_z],
            'max': [max_x, max_y, max_z],
        },
        'center': [obj.matrix_world.translation.x, 
                   obj.matrix_world.translation.y, 
                   obj.matrix_world.translation.z],
    })
    
    print(f"  📦 {obj.name} → class {class_id} ({class_name})")

print(f"\n✅ Found {len(source_objects)} labeled source objects")

if len(source_objects) == 0:
    print("\n❌ ERROR: Still no source objects found!")
    print("   Check that your scene has these objects:")
    print("   - Plane, Mesh_0, Rock0/3/6, Cube, Mball, tekne, Coral, Turtle")
else:
    metadata = {
        'scene_name': scene_name,
        'num_scan_points': len(scan_points),
        'source_objects': source_objects,
    }
    
    json_path = os.path.join(output_dir, f"{scene_name}_metadata.json")
    with open(json_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Exported metadata: {json_path}")
    print("\n✅ Now run label_points.py outside Blender")
    print(f"   Change scene_name to: '{scene_name}'")