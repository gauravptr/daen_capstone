import bpy
import json
import os
from mathutils import Vector

"""
Automated: Assign materials + Export metadata for ALL scanned scenes
Run this in Blender - it will process all .blend files in a folder
"""

# ============================================================
# CONFIGURATION
# ============================================================
SCANNED_SCENES_FOLDER = r"C:\Users\jcwin\OneDrive\Desktop\Capstone\Annotation\ProcessedScenes"
OUTPUT_DIR = r"C:\Users\jcwin\OneDrive\Desktop\Capstone\Annotation\labeled_scans"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Material mapping - update these to separate anomaly types if needed [2]
MATERIAL_ASSIGNMENTS = {
    '00_seafloor': ['Plane'],
    '01_cube': ['Cube'],           # Separate cube anomaly
    '02_sphere': ['Mball'],         # Separate sphere anomaly  
    '03_boat': ['tekne'],           # Separate boat anomaly
    '04_coral': ['10010_Coral_v1_L3'],
    '05_rock': ['Rock', 'Mesh_0'],
    '06_wildlife': ['10042_Sea_Turtle'],
}

IGNORE_OBJECTS = ['Camera', 'Light', 'SonarPath', 'PathMarker', 'TextureField', 'real_values', 'noise_values']

material_colors = {
    '00_seafloor': (0.55, 0.27, 0.07),  # Brown
    '01_cube': (1.0, 0.0, 0.0),         # Red
    '02_sphere': (1.0, 0.5, 0.0),       # Orange
    '03_boat': (1.0, 0.0, 0.5),         # Magenta
    '04_coral': (1.0, 0.41, 0.71),      # Pink
    '05_rock': (0.5, 0.5, 0.5),         # Gray
    '06_wildlife': (0.0, 1.0, 0.0),     # Green
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def assign_materials():
    """Assign semantic materials to objects in current scene [2]"""
    # Create materials if needed
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
    
    return assigned

def export_metadata(scene_name):
    """Export scan points and metadata for current scene [2]"""
    # Export scan points
    scan_points = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and 'real_values' in obj.name:
            mesh = obj.data
            for v in mesh.vertices:
                world_co = obj.matrix_world @ v.co
                scan_points.append((world_co.x, world_co.y, world_co.z))
    
    print(f"  📊 Collected {len(scan_points):,} scan points")
    
    xyz_path = os.path.join(OUTPUT_DIR, f"{scene_name}_scan.xyz")
    with open(xyz_path, 'w') as f:
        for x, y, z in scan_points:
            f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")
    
    print(f"  ✅ Exported: {xyz_path}")
    
    # Export source object metadata with TIGHT bounding boxes [2]
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
        
        # Get TIGHT bounding box using actual vertices
        world_verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
        
        source_objects.append({
            'name': obj.name,
            'class_id': class_id,
            'class_name': class_name,
            'bbox': {
                'min': [min(v.x for v in world_verts), min(v.y for v in world_verts), min(v.z for v in world_verts)],
                'max': [max(v.x for v in world_verts), max(v.y for v in world_verts), max(v.z for v in world_verts)],
            },
            'center': [obj.matrix_world.translation.x, obj.matrix_world.translation.y, obj.matrix_world.translation.z],
        })
    
    print(f"  ✅ Found {len(source_objects)} labeled source objects")
    
    if len(source_objects) > 0:
        metadata = {
            'scene_name': scene_name,
            'num_scan_points': len(scan_points),
            'source_objects': source_objects,
        }
        
        json_path = os.path.join(OUTPUT_DIR, f"{scene_name}_metadata.json")
        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"  ✅ Exported: {json_path}")
    else:
        print(f"  ⚠️  No labeled objects found in {scene_name}")

# ============================================================
# MAIN LOOP
# ============================================================
blend_files = [f for f in os.listdir(SCANNED_SCENES_FOLDER) if f.endswith('.blend')]

print("=" * 60)
print(f"   BATCH PROCESSING {len(blend_files)} SCENES")
print("=" * 60)

for i, filename in enumerate(sorted(blend_files), 1):
    scene_name = filename.replace('.blend', '')
    scene_path = os.path.join(SCANNED_SCENES_FOLDER, filename)
    
    print(f"\n{'='*60}")
    print(f"Scene {i}/{len(blend_files)}: {scene_name}")
    print(f"{'='*60}")
    
    # Open scene
    bpy.ops.wm.open_mainfile(filepath=scene_path)
    
    # Assign materials
    print("\n🎨 Assigning materials...")
    assigned = assign_materials()
    print(f"  ✅ Assigned materials to {assigned} objects")
    
    # Export metadata
    print("\n📤 Exporting metadata...")
    export_metadata(scene_name)

print("\n" + "=" * 60)
print("   ✅ ALL SCENES PROCESSED!")
print(f"   Output: {OUTPUT_DIR}")
print("=" * 60)