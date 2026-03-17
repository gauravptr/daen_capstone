import bpy
import ast

print("=" * 60)
print("       FULL BATCH SCAN - ALL POSITIONS")
print("=" * 60)

# Get positions
scan_positions = ast.literal_eval(bpy.context.scene["scan_positions"])
camera = bpy.context.scene.camera
total = len(scan_positions)

print(f"\n🎯 Scanning ALL {total} positions...")
print("⏱️  This may take several minutes...\n")

successful = 0
failed = 0
total_hits = 0

for i in range(total):
    x, y, z = scan_positions[i]
    
    # Move camera
    camera.location = (x, y, z)
    camera.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    
    # Progress bar
    progress = (i + 1) / total
    bar_len = 30
    filled = int(bar_len * progress)
    bar = "█" * filled + "░" * (bar_len - filled)
    
    print(f"📍 [{bar}] {i+1}/{total} ({progress*100:.1f}%) - ({x:.1f}, {y:.1f}, {z:.1f})", end="")
    
    # Trigger scan
    try:
        bpy.ops.wm.execute_scan()
        successful += 1
        print(" ✅")
    except Exception as e:
        failed += 1
        print(" ❌")

print(f"\n" + "=" * 60)
print(f"       FULL BATCH COMPLETE!")
print(f"=" * 60)
print(f"\n   ✅ Successful scans: {successful}")
print(f"   ❌ Failed scans: {failed}")
print(f"   📊 Coverage: {successful/total*100:.1f}%")
