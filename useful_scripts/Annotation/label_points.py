import numpy as np
import json
import os
from collections import defaultdict

"""
Step 3: Label scan points based on source object bounding boxes
Run this OUTSIDE Blender (regular Python)
"""

# ============================================================
# CONFIGURATION
# ============================================================
scan_dir = r"C:\Users\jcwin\OneDrive\Desktop\Capstone\labeled_scans"
scene_name = "BASE_scanned"  # ⚠️ CHANGE THIS for each scene

xyz_path = os.path.join(scan_dir, f"{scene_name}_scan.xyz")
metadata_path = os.path.join(scan_dir, f"{scene_name}_metadata.json")
output_path = os.path.join(scan_dir, f"{scene_name}_labeled.ply")

# Labeling parameters
BBOX_MARGIN = 0.2  # ✅ TIGHTER: 0.2m margin instead of 0.5m
DEFAULT_CLASS = 0  # Seafloor (anything not in a bbox)

print("=" * 60)
print("   LABELING SCAN POINTS")
print("=" * 60)

# Load scan points
print(f"📖 Loading scan points from {xyz_path}")
points = np.loadtxt(xyz_path)
print(f"   Loaded {len(points):,} points")

# Load metadata
print(f"📖 Loading metadata from {metadata_path}")
with open(metadata_path, 'r') as f:
    metadata = json.load(f)

source_objects = metadata['source_objects']
print(f"   Found {len(source_objects)} source objects")

# Show object breakdown
class_obj_count = defaultdict(int)
for obj in source_objects:
    class_obj_count[obj['class_id']] += 1

print("\n📦 Object breakdown:")
class_names = {0: 'seafloor', 1: 'anomaly', 2: 'coral', 3: 'rock', 4: 'wildlife'}
for class_id in sorted(class_obj_count.keys()):
    print(f"   Class {class_id} ({class_names.get(class_id, 'unknown')}): {class_obj_count[class_id]} objects")

# ============================================================
# Label points using TIGHTER bounding boxes
# ============================================================
print("\n🏷️  Labeling points...")

labels = np.full(len(points), DEFAULT_CLASS, dtype=np.uint8)
class_counts = defaultdict(int)

# Sort objects by priority (anomalies first, then small to large)
# This prevents seafloor from overriding small objects
def get_bbox_volume(obj):
    bbox = obj['bbox']
    dx = bbox['max'][0] - bbox['min'][0]
    dy = bbox['max'][1] - bbox['min'][1]
    dz = bbox['max'][2] - bbox['min'][2]
    return dx * dy * dz

# Prioritize: anomalies > wildlife > coral > rock > seafloor
priority_order = [1, 4, 2, 3, 0]
sorted_objects = sorted(source_objects, 
                       key=lambda obj: (priority_order.index(obj['class_id']) if obj['class_id'] in priority_order else 99, 
                                       get_bbox_volume(obj)))

for i, point in enumerate(points):
    x, y, z = point
    
    # Check each object's bounding box
    for obj in sorted_objects:
        bbox = obj['bbox']
        
        # Check if point is inside bounding box with small margin
        inside = (
            bbox['min'][0] - BBOX_MARGIN <= x <= bbox['max'][0] + BBOX_MARGIN and
            bbox['min'][1] - BBOX_MARGIN <= y <= bbox['max'][1] + BBOX_MARGIN and
            bbox['min'][2] - BBOX_MARGIN <= z <= bbox['max'][2] + BBOX_MARGIN
        )
        
        if inside:
            labels[i] = obj['class_id']
            break  # Use first matching bbox (highest priority)
    
    class_counts[labels[i]] += 1
    
    # Progress
    if (i + 1) % 100000 == 0:
        print(f"   Processed {i+1:,} / {len(points):,} points...")

# Print distribution
print("\n📊 Class distribution:")
for class_id in sorted(class_counts.keys()):
    count = class_counts[class_id]
    pct = count / len(points) * 100
    name = class_names.get(class_id, 'unknown')
    print(f"   Class {class_id} ({name:12s}): {count:8,} points ({pct:5.2f}%)")

# ============================================================
# Export labeled PLY
# ============================================================
print(f"\n💾 Exporting to {output_path}")

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

print(f"✅ Exported labeled point cloud!")
print(f"   File: {output_path}")
print(f"   Size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")