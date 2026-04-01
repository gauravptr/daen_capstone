import numpy as np
import json
import os
from collections import defaultdict

"""
Automated: Label ALL scan points from metadata files
Run this OUTSIDE Blender (regular Python)
"""

# ============================================================
# CONFIGURATION
# ============================================================
LABELED_SCANS_DIR = r"C:\Users\jcwin\OneDrive\Desktop\Capstone\Annotation\labeled_scans"

# Labeling parameters from [1]
BBOX_MARGIN = 0.2
DEFAULT_CLASS = 0
class_names = {
    0: 'seafloor', 
    1: 'cube_anomaly',      # ✅ Cube
    2: 'sphere_anomaly',    # ✅ Sphere
    3: 'boat_anomaly',      # ✅ Boat
    4: 'coral', 
    5: 'rock', 
    6: 'wildlife'
}
# ============================================================
# HELPER FUNCTIONS
# ============================================================
def get_bbox_volume(obj):
    """Calculate bounding box volume"""
    bbox = obj['bbox']
    dx = bbox['max'][0] - bbox['min'][0]
    dy = bbox['max'][1] - bbox['min'][1]
    dz = bbox['max'][2] - bbox['min'][2]
    return dx * dy * dz

def label_scene(scene_name):
    """Label a single scene's points"""
    xyz_path = os.path.join(LABELED_SCANS_DIR, f"{scene_name}_scan.xyz")
    metadata_path = os.path.join(LABELED_SCANS_DIR, f"{scene_name}_metadata.json")
    output_path = os.path.join(LABELED_SCANS_DIR, f"{scene_name}_labeled.ply")
    
    # Check files exist
    if not os.path.exists(xyz_path):
        print(f"  ⚠️  Scan file not found: {xyz_path}")
        return False
    
    if not os.path.exists(metadata_path):
        print(f"  ⚠️  Metadata not found: {metadata_path}")
        return False
    
    # Load scan points
    print(f"  📖 Loading {xyz_path}")
    points = np.loadtxt(xyz_path)
    print(f"     {len(points):,} points")
    
    # Load metadata
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    source_objects = metadata['source_objects']
    print(f"     {len(source_objects)} source objects")
    
    if len(source_objects) == 0:
        print(f"  ⚠️  No source objects - skipping")
        return False
    
    # Label points using priority order from [1]
    labels = np.full(len(points), DEFAULT_CLASS, dtype=np.uint8)
    priority_order = [1, 2, 3, 6, 4, 5, 0]  # cube, sphere, boat, wildlife, coral, rock, seafloor
    sorted_objects = sorted(source_objects, 
                           key=lambda obj: (priority_order.index(obj['class_id']) if obj['class_id'] in priority_order else 99, 
                                           get_bbox_volume(obj)))
    
    for i, point in enumerate(points):
        x, y, z = point
        
        for obj in sorted_objects:
            bbox = obj['bbox']
            
            inside = (
                bbox['min'][0] - BBOX_MARGIN <= x <= bbox['max'][0] + BBOX_MARGIN and
                bbox['min'][1] - BBOX_MARGIN <= y <= bbox['max'][1] + BBOX_MARGIN and
                bbox['min'][2] - BBOX_MARGIN <= z <= bbox['max'][2] + BBOX_MARGIN
            )
            
            if inside:
                labels[i] = obj['class_id']
                break
    
    # Count distribution
    class_counts = defaultdict(int)
    for label in labels:
        class_counts[label] += 1
    
    print(f"  📊 Distribution:")
    for class_id in sorted(class_counts.keys()):
        count = class_counts[class_id]
        pct = count / len(points) * 100
        name = class_names.get(class_id, 'unknown')
        print(f"     Class {class_id} ({name:10s}): {count:7,} ({pct:5.2f}%)")
    
    # Export PLY
    with open(output_path, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar class\n")
        f.write("end_header\n")
        
        for i, point in enumerate(points):
            x, y, z = point
            c = labels[i]
            f.write(f"{x:.6f} {y:.6f} {z:.6f} {c}\n")
    
    file_size = os.path.getsize(output_path) / (1024*1024)
    print(f"  ✅ Exported: {output_path} ({file_size:.2f} MB)")
    
    return True

# ============================================================
# MAIN LOOP
# ============================================================
# Find all scenes with metadata
metadata_files = [f for f in os.listdir(LABELED_SCANS_DIR) if f.endswith('_metadata.json')]
scene_names = [f.replace('_metadata.json', '') for f in metadata_files]

print("=" * 60)
print(f"   BATCH LABELING {len(scene_names)} SCENES")
print("=" * 60)

successful = 0
failed = 0

for i, scene_name in enumerate(sorted(scene_names), 1):
    print(f"\n{'='*60}")
    print(f"Scene {i}/{len(scene_names)}: {scene_name}")
    print(f"{'='*60}")
    
    if label_scene(scene_name):
        successful += 1
    else:
        failed += 1

print("\n" + "=" * 60)
print("   LABELING COMPLETE!")
print("=" * 60)
print(f"  ✅ Successful: {successful}")
print(f"  ❌ Failed: {failed}")
print(f"  📁 Output: {LABELED_SCANS_DIR}")
print("=" * 60)