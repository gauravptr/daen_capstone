import bpy
import ast
import os

print("=" * 60)
print("       FULL BATCH SCAN WITH COLLECTION")
print("=" * 60)

# ============================================================
# CONFIGURATION
# ============================================================

# Collection name for scan results
SCAN_COLLECTION_NAME = "Scan Results"

# Output folder
output_folder = r"C:\Users\grsha\Desktop\DAEN 460\output"
os.makedirs(output_folder, exist_ok=True)

# Get scene name for labeling
scene_name = os.path.basename(bpy.data.filepath).replace('.blend', '') if bpy.data.filepath else "unnamed_scene"

# ============================================================
# STEP 1: CREATE OR CLEAR SCAN RESULTS COLLECTION
# ============================================================

print(f"\n📁 Step 1: Setting up '{SCAN_COLLECTION_NAME}' collection...")

# Get or create collection
scan_collection = bpy.data.collections.get(SCAN_COLLECTION_NAME)

if scan_collection:
    # Clear existing scan results from collection
    for obj in list(scan_collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print(f"   Cleared existing objects from '{SCAN_COLLECTION_NAME}'")
else:
    # Create new collection
    scan_collection = bpy.data.collections.new(SCAN_COLLECTION_NAME)
    bpy.context.scene.collection.children.link(scan_collection)
    print(f"   Created new collection '{SCAN_COLLECTION_NAME}'")

# ============================================================
# STEP 2: GET SCAN POSITIONS
# ============================================================

print(f"\n📍 Step 2: Loading scan positions...")

if "scan_positions" not in bpy.context.scene:
    print("❌ No scan positions found! Run the path setup script first.")
else:
    scan_positions = ast.literal_eval(bpy.context.scene["scan_positions"])
    total = len(scan_positions)
    print(f"   Found {total} scan positions")
    
    # ============================================================
    # STEP 3: GET CAMERA
    # ============================================================
    
    print(f"\n📷 Step 3: Setting up camera...")
    
    camera = bpy.context.scene.camera
    if not camera:
        print("❌ No camera found!")
    else:
        print(f"   Using camera: {camera.name}")
        
        # Configure scanner
        props = bpy.context.scene.scannerProperties
        props.scannerObject = camera
        
        # ============================================================
        # STEP 4: TRACK OBJECTS BEFORE SCANNING
        # ============================================================
        
        objects_before = set(obj.name for obj in bpy.data.objects)
        
        # ============================================================
        # STEP 5: RUN BATCH SCAN
        # ============================================================
        
        # Set number of scans (change to 'total' for full scan)
        MAX_SCANS = total
        
        print(f"\n🎯 Step 4: Running {MAX_SCANS} scans...")
        print(f"   Scene: {scene_name}\n")
        
        successful = 0
        failed = 0
        
        for i in range(min(MAX_SCANS, total)):
            x, y, z = scan_positions[i]
            
            # Move camera
            camera.location = (x, y, z)
            camera.rotation_euler = (0, 0, 0)
            bpy.context.view_layer.update()
            
            # Progress bar
            progress = (i + 1) / MAX_SCANS
            bar_len = 30
            filled = int(bar_len * progress)
            bar = "█" * filled + "░" * (bar_len - filled)
            
            print(f"[{bar}] {i+1}/{MAX_SCANS} ({progress*100:.0f}%) ({x:.1f}, {y:.1f})", end="")
            
            # Execute scan
            try:
                bpy.ops.wm.execute_scan()
                successful += 1
                print(" ✅")
            except Exception as e:
                failed += 1
                print(f" ❌")
        
        # ============================================================
        # STEP 6: MOVE ALL SCAN RESULTS TO COLLECTION
        # ============================================================
        
        print(f"\n📁 Step 5: Organizing scan results into '{SCAN_COLLECTION_NAME}'...")
        
        objects_after = set(obj.name for obj in bpy.data.objects)
        new_objects = objects_after - objects_before
        
        moved_real = 0
        moved_noise = 0
        total_points = 0
        
        for obj_name in new_objects:
            obj = bpy.data.objects.get(obj_name)
            
            if obj and ("real_values" in obj_name or "noise_values" in obj_name):
                # Count points from real_values objects
                if obj.type == 'MESH' and "real_values" in obj_name:
                    total_points += len(obj.data.vertices)
                    moved_real += 1
                elif "noise_values" in obj_name:
                    moved_noise += 1
                
                # Unlink from all current collections
                for coll in list(obj.users_collection):
                    coll.objects.unlink(obj)
                
                # Link to scan results collection
                scan_collection.objects.link(obj)
        
        print(f"   ✅ Moved {moved_real} real_values objects")
        print(f"   ✅ Moved {moved_noise} noise_values objects")
        print(f"   📊 Total points captured: {total_points:,}")
        
        # ============================================================
        # SUMMARY
        # ============================================================
        
        print("\n" + "=" * 60)
        print("       SCAN COMPLETE!")
        print("=" * 60)
        
        print(f"""
📊 Results:
   - Scene: {scene_name}
   - Successful scans: {successful}/{MAX_SCANS}
   - Failed scans: {failed}
   - Total points: {total_points:,}
   
📁 Organization:
   - Collection: '{SCAN_COLLECTION_NAME}'
   - Real value objects: {moved_real}
   - Noise value objects: {moved_noise}
   
💡 Tip: In the Outliner, find '{SCAN_COLLECTION_NAME}' 
   to view all scan results together.
""")