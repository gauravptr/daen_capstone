import bpy
import math

print("=" * 60)
print("       PRECISE BOAT SCANNING PATH")
print("=" * 60)

# ============================================================
# CONFIGURATION
# ============================================================

PLANE_SIZE = 50  # 50m x 50m plane
HALF_SIZE = PLANE_SIZE / 2  # 25m

CAMERA_HEIGHT = 10  # Height above plane
SCAN_WIDTH = 8  # Width covered per pass
OVERLAP = 2  # Overlap between passes
PASS_SPACING = SCAN_WIDTH - OVERLAP  # 6m between passes

# Animation timing
FRAMES_PER_METER = 2  # Slower = more frames per meter

# ============================================================
# STEP 1: Setup Camera
# ============================================================
print("\n🧹 Step 1: Setting up camera...")

# Delete old path objects
for obj in list(bpy.data.objects):
    if obj.name.startswith("ScanPath") or obj.name.startswith("PathMarker"):
        bpy.data.objects.remove(obj, do_unlink=True)

# Get or create camera
camera = bpy.context.scene.camera
if camera:
    camera.animation_data_clear()
    print(f"   Using existing camera: {camera.name}")
else:
    bpy.ops.object.camera_add()
    camera = bpy.context.active_object
    camera.name = "ScannerCamera"
    bpy.context.scene.camera = camera
    print(f"   Created new camera: {camera.name}")

# Point camera straight down
camera.rotation_euler = (0, 0, 0)

# ============================================================
# STEP 2: Generate Precise Waypoints
# ============================================================
print("\n📍 Step 2: Generating precise waypoints...")

waypoints = []

# Calculate number of passes
num_passes = math.ceil(PLANE_SIZE / PASS_SPACING) + 1

# Starting position
start_x = -HALF_SIZE + (PASS_SPACING / 2)

for i in range(num_passes):
    x = start_x + (i * PASS_SPACING)
    
    # Don't go beyond the plane
    if x > HALF_SIZE:
        x = HALF_SIZE
    
    if i % 2 == 0:
        # Moving in +Y direction (bottom to top)
        y_start = -HALF_SIZE
        y_end = HALF_SIZE
    else:
        # Moving in -Y direction (top to bottom)
        y_start = HALF_SIZE
        y_end = -HALF_SIZE
    
    # Add start point of this pass
    waypoints.append({
        'x': x,
        'y': y_start,
        'z': CAMERA_HEIGHT,
        'type': 'pass_start'
    })
    
    # Add end point of this pass
    waypoints.append({
        'x': x,
        'y': y_end,
        'z': CAMERA_HEIGHT,
        'type': 'pass_end'
    })
    
    # Stop if we've covered the whole plane
    if x >= HALF_SIZE - (PASS_SPACING / 2):
        break

print(f"   Generated {len(waypoints)} waypoints")
print(f"   Number of passes: {len(waypoints) // 2}")

# ============================================================
# STEP 3: Create Animation with Linear Interpolation
# ============================================================
print("\n🎬 Step 3: Creating animation...")

frame = 1
bpy.context.scene.frame_start = 1

# Create keyframes for each waypoint
for i, wp in enumerate(waypoints):
    x, y, z = wp['x'], wp['y'], wp['z']
    
    # Set camera position
    camera.location = (x, y, z)
    camera.rotation_euler = (0, 0, 0)  # Keep pointing down
    
    # Insert location keyframe
    camera.keyframe_insert(data_path="location", frame=frame)
    camera.keyframe_insert(data_path="rotation_euler", frame=frame)
    
    # Calculate frames to next waypoint
    if i < len(waypoints) - 1:
        next_wp = waypoints[i + 1]
        
        # Calculate distance to next point
        dx = next_wp['x'] - x
        dy = next_wp['y'] - y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Frames based on distance
        frames_to_next = max(1, int(distance * FRAMES_PER_METER))
        frame += frames_to_next

bpy.context.scene.frame_end = frame

print(f"   Total frames: {frame}")

# ============================================================
# STEP 4: Set LINEAR Interpolation (Critical!)
# ============================================================
print("\n🔧 Step 4: Setting linear interpolation...")

try:
    if camera.animation_data and camera.animation_data.action:
        for fcurve in camera.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'
        print("   ✅ Linear interpolation set - camera will move in straight lines")
except Exception as e:
    print(f"   ⚠️ Could not set interpolation: {e}")

# ============================================================
# STEP 5: Create Visual Path
# ============================================================
print("\n📍 Step 5: Creating visual path...")

# Create a mesh to show the exact path
mesh = bpy.data.meshes.new("ScanPathMesh")
path_obj = bpy.data.objects.new("ScanPath", mesh)
bpy.context.collection.objects.link(path_obj)

# Create vertices and edges
vertices = [(wp['x'], wp['y'], wp['z']) for wp in waypoints]
edges = [(i, i+1) for i in range(len(vertices)-1)]

mesh.from_pydata(vertices, edges, [])
mesh.update()

# Add material to make it visible
mat = bpy.data.materials.new("ScanPathMaterial")
mat.diffuse_color = (1, 0, 0, 1)  # Red
path_obj.data.materials.append(mat)

print("   ✅ Red line shows exact camera path")

# ============================================================
# STEP 6: Create Position Markers
# ============================================================
print("\n📌 Step 6: Creating position markers...")

# Create small spheres at each waypoint
for i, wp in enumerate(waypoints):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.3,
        location=(wp['x'], wp['y'], wp['z'])
    )
    marker = bpy.context.active_object
    marker.name = f"PathMarker_{i:03d}"
    
    # Color based on type
    mat = bpy.data.materials.new(f"MarkerMat_{i}")
    if wp['type'] == 'pass_start':
        mat.diffuse_color = (0, 1, 0, 1)  # Green for start
    else:
        mat.diffuse_color = (0, 0, 1, 1)  # Blue for end
    marker.data.materials.append(mat)

print(f"   ✅ Created {len(waypoints)} markers (green=start, blue=end)")

# ============================================================
# STEP 7: Store Scan Positions
# ============================================================
print("\n💾 Step 7: Storing scan positions...")

# Create more granular scan positions along the path
scan_positions = []
SCAN_INTERVAL = 4  # Take a scan every 4 meters

for i in range(0, len(waypoints) - 1, 2):
    start_wp = waypoints[i]
    end_wp = waypoints[i + 1]
    
    # Calculate number of scans for this pass
    y_distance = abs(end_wp['y'] - start_wp['y'])
    num_scans = int(y_distance / SCAN_INTERVAL) + 1
    
    for j in range(num_scans):
        t = j / max(1, num_scans - 1)  # 0 to 1
        
        x = start_wp['x']
        y = start_wp['y'] + t * (end_wp['y'] - start_wp['y'])
        z = start_wp['z']
        
        scan_positions.append((x, y, z))

# Store for batch scanning
bpy.context.scene["scan_positions"] = str(scan_positions)
bpy.context.scene["current_scan_index"] = 0

print(f"   ✅ Created {len(scan_positions)} scan positions")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("       SETUP COMPLETE!")
print("=" * 60)

print(f"""
📊 Configuration:
   - Plane size: {PLANE_SIZE}m x {PLANE_SIZE}m
   - Camera height: {CAMERA_HEIGHT}m
   - Pass spacing: {PASS_SPACING}m
   - Number of passes: {len(waypoints) // 2}
   - Total animation frames: {frame}
   - Scan positions: {len(scan_positions)}

🎨 Visual Guide:
   - RED LINE: Camera path
   - GREEN SPHERES: Pass start points
   - BLUE SPHERES: Pass end points

🎮 To Preview:
   1. Press SPACEBAR to play animation
   2. Or drag the timeline slider
   
📷 To Scan:
   Run the batch scanning script next!
""")
