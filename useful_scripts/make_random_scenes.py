import bpy
import random
import math
import os



# -----------------------
# CONFIGURATION
# -----------------------
num_scenes = 10
output_dir = bpy.path.abspath("//ProceduralScenes")
os.makedirs(output_dir, exist_ok=True)

# Seabed bounds (50m x 50m)
x_min, x_max = -25, 25
y_min, y_max = -25, 25
z_base = 0  # Top of the sand plane

# -----------------------
# CLEAN UP SCAN RESULTS
# -----------------------
print("=" * 60)
print("   UNDERWATER SCENE GENERATOR")
print("=" * 60)
print("\n🧹 Cleaning up previous scan results...")

cleaned = 0
for obj in list(bpy.data.objects):
    if any(prefix in obj.name for prefix in ['noise_values', 'real_values', 'PathMarker', 'ScanPath']):
        bpy.data.objects.remove(obj, do_unlink=True)
        cleaned += 1

print(f"   Removed {cleaned} scan result objects")

# -----------------------
# AUTO-DETECT OBJECTS
# -----------------------
print("\n📋 Detecting scene objects...")

ANOMALY_TYPES = {
    'boat': 'tekne',
    'cube': 'Cube',
    'sphere': 'Mball'
}

# Categorize rocks by size
LARGE_ROCKS = ['Rock0', 'Rock6', 'Rock3']  # only 1-2 per scene
SMALL_OBJECTS = ['10010_Coral_v1_L3', 'Mesh_0']  # Coral and other small stuff
PRESERVE = ['Plane', 'Camera', 'Light', 'TextureField']
OPTIONAL = ['10042_Sea_Turtle_V2_iterations-2']

anomaly_objects = {'boat': [], 'cube': [], 'sphere': []}
large_rocks = []
small_objects = []
optional_objects = []
preserved_objects = []

for obj in bpy.data.objects:
    obj_name = obj.name
    
    if any(preserve in obj_name for preserve in PRESERVE):
        preserved_objects.append(obj_name)
        print(f"  🔒 PRESERVE: {obj_name}")
        continue
    
    is_anomaly = False
    for anom_type, anom_keyword in ANOMALY_TYPES.items():
        if obj_name == anom_keyword or obj_name.startswith(anom_keyword + '.'):
            anomaly_objects[anom_type].append(obj_name)
            print(f"  🎯 ANOMALY ({anom_type}): {obj_name}")
            is_anomaly = True
            break
    
    if is_anomaly:
        continue
    
    is_large_rock = False
    for rock in LARGE_ROCKS:
        if obj_name == rock or obj_name.startswith(rock + '.'):
            large_rocks.append(obj_name)
            print(f"  🪨 LARGE ROCK: {obj_name}")
            is_large_rock = True
            break
    
    if is_large_rock:
        continue
    
    is_optional = False
    for opt in OPTIONAL:
        if obj_name == opt or obj_name.startswith(opt + '.'):
            optional_objects.append(obj_name)
            print(f"  🐢 OPTIONAL: {obj_name}")
            is_optional = True
            break
    
    if is_optional:
        continue
    
    # Check for small objects (coral, mesh)
    for small in SMALL_OBJECTS:
        if obj_name == small or obj_name.startswith(small + '.'):
            small_objects.append(obj_name)
            print(f"  🌿 SMALL OBJECT: {obj_name}")
            break

print(f"\n📊 Configuration:")
print(f"   Seabed: 50m × 50m at Z={z_base}")
print(f"   Large rocks: {len(large_rocks)} (1-2 per scene)")
print(f"   Small objects: {len(small_objects)}")
print(f"   Anomaly types: {sum(len(v) for v in anomaly_objects.values())}")
print(f"   Optional: {len(optional_objects)}")

# -----------------------
# CLUSTERING PARAMETERS
# -----------------------
large_rock_count = (1, 2)  # Only 1-2 large rocks per scene

small_object_params = {
    "clusters": (4, 7),
    "per_cluster": (5, 10),
    "cluster_radius": 5.0,
    "scattered": (10, 20)
}

turtle_chance = 0.3
turtle_height_range = (1.0, 3.0) 

# Scale variation
ROCK_SCALE_RANGE = (0.7, 1.0)
SMALL_SCALE_RANGE = (0.8, 1.2)

# -----------------------
# HELPER FUNCTIONS
# -----------------------
def random_position_in_area():
    """Generate random XY position within seabed bounds"""
    return (
        random.uniform(x_min, x_max),
        random.uniform(y_min, y_max)
    )

def random_position_in_cluster(center, radius):
    """Generate random position within cluster radius"""
    angle = random.uniform(0, 6.28319)
    distance = random.uniform(0, radius)
    return (
        center[0] + distance * math.cos(angle),
        center[1] + distance * math.sin(angle)
    )

def get_object_bounds_in_world(obj):
    """Get the lowest Z point of object in world coordinates"""
    if obj.type != 'MESH' or len(obj.data.vertices) == 0:
        return obj.location.z
    
    # Get all vertex positions in world space
    world_vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
    
    # Find the lowest Z
    min_z = min(v.z for v in world_vertices)
    
    return min_z

def place_object(obj, x, y, original_rotation, obj_type='small', is_turtle=False):
    """
    Place object at position with natural orientation
    Objects are placed FIRST, THEN moved to touch sand based on actual bounds
    """
    # Set position
    obj.location.x = x
    obj.location.y = y
    obj.location.z = 0  # Start at sand level temporarily
    
    # Set rotation
    if obj_type == 'large_rock':
        obj.rotation_euler = (
            original_rotation[0] + random.uniform(-0.1, 0.1),
            original_rotation[1] + random.uniform(-0.1, 0.1),
            random.uniform(0, 6.28319)
        )
        scale = random.uniform(*ROCK_SCALE_RANGE)
        obj.scale = (scale, scale, scale)
    else:
        obj.rotation_euler = (
            original_rotation[0],
            original_rotation[1],
            random.uniform(0, 6.28319)
        )
        if obj_type == 'small':
            scale = random.uniform(*SMALL_SCALE_RANGE)
            obj.scale = (scale, scale, scale)
        else:
            obj.scale = (1, 1, 1)
    
    # UPDATE: Force Blender to recalculate transforms
    bpy.context.view_layer.update()
    
    # Now calculate proper Z position
    if is_turtle:
        # Turtles swim above the seabed
        obj.location.z = z_base + random.uniform(*turtle_height_range)
    elif obj.type == 'MESH' and len(obj.data.vertices) > 0:
        # Get the actual lowest point after rotation/scale applied
        lowest_z = get_object_bounds_in_world(obj)
        
        # Move object so its lowest point is at or slightly below sand level
        offset = lowest_z - obj.location.z  # How far below origin is lowest point
        burial = random.uniform(0, 0.5)  # 0-0.5m burial
        
        obj.location.z = z_base - offset - burial
    else:
        obj.location.z = z_base
    
    # Final update
    bpy.context.view_layer.update()

def duplicate_object(obj_name):
    """Duplicate object and return copy with original rotation"""
    orig = bpy.data.objects.get(obj_name)
    if not orig:
        return None, None
    
    try:
        original_rotation = orig.rotation_euler.copy()
        
        dup = orig.copy()
        if orig.data:
            dup.data = orig.data.copy()
        bpy.context.collection.objects.link(dup)
        dup.hide_viewport = False
        dup.hide_render = False
        
        return dup, original_rotation
    except Exception as e:
        print(f"    ⚠️  Could not duplicate {obj_name}: {e}")
        return None, None

# -----------------------
# MAIN GENERATION LOOP
# -----------------------
print(f"\n{'='*60}")
print(f"   GENERATING {num_scenes} SCENES")
print(f"{'='*60}\n")

# Create balanced anomaly distribution
anomaly_scenes = num_scenes // 2
anomaly_types_list = ['boat', 'cube', 'sphere'] * (anomaly_scenes // 3 + 1)
random.shuffle(anomaly_types_list)
anomaly_types_list = anomaly_types_list[:anomaly_scenes]

for scene_idx in range(1, num_scenes + 1):
    print(f"{'='*60}")
    print(f"SCENE {scene_idx}/{num_scenes}")
    print(f"{'='*60}")
    
    # Clean up previous procedural objects
    for obj in list(bpy.context.collection.objects):
        if obj.get("procedural"):
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # Hide all originals except preserved
    all_anomalies = anomaly_objects['boat'] + anomaly_objects['cube'] + anomaly_objects['sphere']
    for obj_name in large_rocks + small_objects + optional_objects + all_anomalies:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.hide_viewport = True
            obj.hide_render = True
    
    for obj_name in preserved_objects:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.hide_viewport = False
            obj.hide_render = False
    
    # -----------------------
    # PLACE LARGE ROCKS
    # -----------------------
    if len(large_rocks) > 0:
        num_large = random.randint(*large_rock_count)
        
        for _ in range(num_large):
            pos = random_position_in_area()
            obj_name = random.choice(large_rocks)
            dup, original_rotation = duplicate_object(obj_name)
            if dup:
                dup["procedural"] = True
                place_object(dup, pos[0], pos[1], original_rotation, obj_type='large_rock')
        
        print(f"  🪨 Large rocks: {num_large}")
    
    # -----------------------
    # SCATTER SMALL OBJECTS (CORAL/MESH)
    # -----------------------
    if len(small_objects) > 0:
        num_clusters = random.randint(*small_object_params["clusters"])
        total_clustered = 0
        
        for _ in range(num_clusters):
            center = random_position_in_area()
            obj_count = random.randint(*small_object_params["per_cluster"])
            
            for _ in range(obj_count):
                pos = random_position_in_cluster(center, small_object_params["cluster_radius"])
                obj_name = random.choice(small_objects)
                dup, original_rotation = duplicate_object(obj_name)
                if dup:
                    dup["procedural"] = True
                    place_object(dup, pos[0], pos[1], original_rotation, obj_type='small')
                    total_clustered += 1
        
        num_scattered = random.randint(*small_object_params["scattered"])
        
        for _ in range(num_scattered):
            pos = random_position_in_area()
            obj_name = random.choice(small_objects)
            dup, original_rotation = duplicate_object(obj_name)
            if dup:
                dup["procedural"] = True
                place_object(dup, pos[0], pos[1], original_rotation, obj_type='small')
        
        print(f"  🌿 Small objects: {total_clustered} clustered + {num_scattered} scattered")
    
    # -----------------------
    # OPTIONAL TURTLES (SWIMMING)
    # -----------------------
    if len(optional_objects) > 0 and random.random() < turtle_chance:
        pos = random_position_in_area()
        obj_name = random.choice(optional_objects)
        dup, original_rotation = duplicate_object(obj_name)
        if dup:
            dup["procedural"] = True
            place_object(dup, pos[0], pos[1], original_rotation, obj_type='turtle', is_turtle=True)
            print(f"  🐢 Turtle: swimming")
    
    # -----------------------
    # ANOMALIES
    # -----------------------
    scene_has_anomaly = scene_idx <= anomaly_scenes
    
    if scene_has_anomaly:
        assigned_type = anomaly_types_list[scene_idx - 1]
        
        if len(anomaly_objects[assigned_type]) > 0:
            num_to_add = random.randint(1, 2)
            added = []
            
            for _ in range(num_to_add):
                anomaly_name = random.choice(anomaly_objects[assigned_type])
                pos = random_position_in_area()
                dup, original_rotation = duplicate_object(anomaly_name)
                if dup:
                    dup["procedural"] = True
                    place_object(dup, pos[0], pos[1], original_rotation, obj_type='anomaly')
                    added.append(anomaly_name)
            
            print(f"  🎯 Anomalies: {', '.join(added)} ({assigned_type})")
        else:
            print(f"  ⚠️  No {assigned_type} available")
            scene_has_anomaly = False
    else:
        print(f"  ✅ Clean scene (no anomalies)")
    
    # -----------------------
    # SAVE SCENE
    # -----------------------
    label = "anomaly" if scene_has_anomaly else "no_anomaly"
    blend_path = os.path.join(output_dir, f"scene_{scene_idx:03d}_{label}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"  💾 Saved: {os.path.basename(blend_path)}\n")

# -----------------------
# SUMMARY
# -----------------------
print(f"{'='*60}")
print(f"   GENERATION COMPLETE")
print(f"{'='*60}")
print(f"  ✅ Generated: {num_scenes} scenes")
print(f"  🎯 Anomaly scenes: {anomaly_scenes}")
print(f"  ✅ Clean scenes: {num_scenes - anomaly_scenes}")
print(f"  📁 Output: {output_dir}")
print(f"{'='*60}\n")