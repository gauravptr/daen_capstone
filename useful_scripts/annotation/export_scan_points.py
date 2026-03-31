import bpy
import json
import os
from mathutils import Vector

"""
Export scan points + source object metadata
"""

output_dir = r"C:\Users\jcwin\Desktop\Capstone\labeled_scans"
os.makedirs(output_dir, exist_ok=True)

scene_name = bpy.path.basename(bpy.data.filepath).replace('.blend', '')
if not scene_name:
    scene_name = "test1_config"

print("=" * 60)
print("   EXPORTING SCAN + METADATA")
print("=" * 60)
print(f"Scene: {scene_name}")

# ============================================================
# Part 1: Export all scan points (unlabeled)
# ============================================================

scan_points = []

for obj in bpy.data.objects:
    if obj.type == 'MESH' and 'real_values' in obj.name:
        mesh = obj.data
        for v in mesh.vertices:
            world_co = obj.matrix_world @ v.co
            scan_points.append((world_co.x, world_co.y, world_co.z))

print(f"📊 Collected {len(scan_points):,} scan points")

# Export as XYZ
xyz_path = os.path.join(output_dir, f"{scene_name}_scan.xyz")
with open(xyz_path, 'w') as f:
    for x, y, z in scan_points:
        f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")

print(f"✅ Exported scan: {xyz_path}")

# ============================================================
# Part 2: Export source object bounding boxes + materials
# ============================================================

source_objects = []

for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    
    # Skip scan results and helpers
    if any(x in obj.name for x in ['real_values', 'noise_values', 'PathMarker', 'ScanPath', 'Camera', 'Light']):
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
    
    # Get bounding box in world space
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    
    min_x = min(c.x for c in bbox_corners)
    max_x = max(c.x for c in bbox_corners)
    min_y = min(c.y for c in bbox_corners)
    max_y = max(c.y for c in bbox_corners)
    min_z = min(c.z for c in bbox_corners)
    max_z = max(c.z for c in bbox_corners)
    
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
    print("\n❌ ERROR: No source objects with materials found!")
    print("   Make sure you ran the material assignment script first.")
    print("   Objects should have materials like: 00_seafloor, 01_anomaly, etc.")
else:
    # Export metadata
    metadata = {
        'scene_name': scene_name,
        'num_scan_points': len(scan_points),
        'source_objects': source_objects,
    }
    
    json_path = os.path.join(output_dir, f"{scene_name}_metadata.json")
    with open(json_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Exported metadata: {json_path}")
    print("\n✅ Now run the labeling script in Python (outside Blender)")