import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

"""
Assign materials to scan results based on spatial proximity
Works by finding which source object each scan point is closest to
"""

print("=" * 60)
print("   LABELING SCAN POINTS BY PROXIMITY")
print("=" * 60)

# Step 1: Build BVH trees for all source objects with materials
source_objects = []

for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    
    # Skip scan results
    if 'real_values' in obj.name or 'noise_values' in obj.name:
        continue
    
    # Skip helpers
    if any(x in obj.name for x in ['PathMarker', 'ScanPath', 'Camera', 'Light']):
        continue
    
    # Check if has semantic material
    if len(obj.material_slots) > 0 and obj.material_slots[0].material:
        mat = obj.material_slots[0].material
        if mat.name[0].isdigit() and '_' in mat.name:
            try:
                class_id = int(mat.name.split('_')[0])
                source_objects.append({
                    'name': obj.name,
                    'object': obj,
                    'material': mat,
                    'class_id': class_id,
                })
                print(f"  📝 {obj.name} → class {class_id}")
            except:
                pass

print(f"\n✅ Found {len(source_objects)} labeled source objects")

if len(source_objects) == 0:
    print("❌ No source objects found!")
    print("   Make sure you ran the material assignment script on your base scene.")
else:
    # Step 2: For each scan result, assign material based on closest source object
    scan_objects = [obj for obj in bpy.data.objects 
                    if obj.type == 'MESH' and 'real_values' in obj.name]
    
    print(f"\n🔍 Processing {len(scan_objects)} scan result objects...")
    
    labeled_count = 0
    
    for scan_obj in scan_objects:
        # Get scan point position (centroid)
        scan_pos = scan_obj.matrix_world @ scan_obj.data.vertices[0].co
        
        # Find closest source object
        min_dist = float('inf')
        closest_source = None
        
        for source in source_objects:
            # Calculate distance to source object's bounding box center
            source_pos = source['object'].matrix_world @ source['object'].location
            dist = (scan_pos - source_pos).length
            
            if dist < min_dist:
                min_dist = dist
                closest_source = source
        
        # Assign material from closest source
        if closest_source and min_dist < 50.0:  # Within 50m (whole scene)
            scan_obj.data.materials.clear()
            scan_obj.data.materials.append(closest_source['material'])
            labeled_count += 1
            
            if labeled_count <= 10:  # Show first 10
                print(f"  ✅ {scan_obj.name} ← {closest_source['name']} ({closest_source['class_id']})")
    
    print(f"\n✅ Labeled {labeled_count} / {len(scan_objects)} scan objects")
    
    if labeled_count > 0:
        print("\n✅ Ready to export! Run the export script now.")
    else:
        print("\n⚠️  No scan objects were labeled. Check:")
        print("   1. Source objects have semantic materials (00_seafloor, 01_anomaly, etc.)")
        print("   2. Scan results exist (real_values_* objects)")