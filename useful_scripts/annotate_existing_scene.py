"""
SCRIPT 1: ANNOTATE EXISTING SCENE BY COLLECTION
================================================
Purpose: Assign class labels to objects based on their collection membership.

How to use:
1. Open your existing Blender scene
2. Make sure objects are organized into collections
3. Modify the COLLECTION_TO_CLASS mapping below
4. Run this script in Blender's Scripting tab
5. All objects will be annotated with class labels

Example mapping:
    "Anomalies" collection → class_label = "anomaly"
    "Rocks" collection → class_label = "rock"
    "Debris" collection → class_label = "debris"
    "Seabed" collection → class_label = "background"
"""

import bpy

# =============================================================================
# CONFIGURATION - MODIFY THIS FOR YOUR SCENE
# =============================================================================

# Map collection names to class labels
# Format: "Collection Name": ("class_label", is_anomaly_flag)
#
# is_anomaly_flag: 
#   True = This is something you want to detect (anomaly, target, etc.)
#   False = This is background/normal terrain

COLLECTION_TO_CLASS = {
    # Anomaly classes (things you want to detect)
    "Anomalies": ("anomaly", True),
    "Mines": ("mine", True),
    "Debris": ("debris", True),
    "Targets": ("target", True),
    
    # Background classes (normal seabed features)
    "Rocks": ("rock", False),
    "Seabed": ("background", False),
    "Terrain": ("background", False),
    "Sand": ("background", False),
    
    # Add more mappings as needed for your scene...
}

# Collections to skip (won't be annotated)
SKIP_COLLECTIONS = [
    "Scanner",
    "Cameras", 
    "Lights",
    "Empties",
]

# Default label for objects in unmapped collections
DEFAULT_CLASS = ("unknown", False)

# =============================================================================
# ANNOTATION FUNCTIONS
# =============================================================================

def get_object_collections(obj):
    """
    Get all collections an object belongs to.
    
    Args:
        obj: Blender object
    
    Returns:
        List of collection names
    """
    collections = []
    for collection in bpy.data.collections:
        if obj.name in collection.objects:
            collections.append(collection.name)
    return collections


def annotate_object(obj, class_label, is_anomaly):
    """
    Add annotation custom properties to an object.
    
    Args:
        obj: Blender object to annotate
        class_label: String class label (e.g., "anomaly", "rock")
        is_anomaly: Boolean flag for binary classification
    """
    # Primary annotations
    obj["class_label"] = class_label
    obj["is_anomaly"] = is_anomaly
    
    # Optional: Add numeric class ID for easier processing
    # You can customize this mapping
    class_id_map = {
        "background": 0,
        "anomaly": 1,
        "mine": 2,
        "debris": 3,
        "rock": 4,
        "target": 5,
        "unknown": -1,
    }
    obj["class_id"] = class_id_map.get(class_label, -1)


def annotate_scene():
    """
    Main function to annotate all objects in the scene based on their collections.
    """
    
    print("=" * 70)
    print("ANNOTATING SCENE BY COLLECTION")
    print("=" * 70)
    
    # Statistics tracking
    stats = {
        'total_objects': 0,
        'annotated': 0,
        'skipped': 0,
        'by_class': {},
        'by_collection': {},
    }
    
    # Get all mesh objects in the scene (we only care about scannable geometry)
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    stats['total_objects'] = len(mesh_objects)
    
    print(f"\nFound {len(mesh_objects)} mesh objects to process")
    print("-" * 70)
    
    # Process each object
    for obj in mesh_objects:
        # Get collections this object belongs to
        obj_collections = get_object_collections(obj)
        
        # Skip if in a skip collection
        if any(skip in obj_collections for skip in SKIP_COLLECTIONS):
            print(f"[SKIP] {obj.name} (in skip collection)")
            stats['skipped'] += 1
            continue
        
        # Find the appropriate class label
        class_label, is_anomaly = DEFAULT_CLASS
        matched_collection = None
        
        for collection_name in obj_collections:
            if collection_name in COLLECTION_TO_CLASS:
                class_label, is_anomaly = COLLECTION_TO_CLASS[collection_name]
                matched_collection = collection_name
                break
        
        # Annotate the object
        annotate_object(obj, class_label, is_anomaly)
        stats['annotated'] += 1
        
        # Update statistics
        if class_label not in stats['by_class']:
            stats['by_class'][class_label] = []
        stats['by_class'][class_label].append(obj.name)
        
        if matched_collection:
            if matched_collection not in stats['by_collection']:
                stats['by_collection'][matched_collection] = []
            stats['by_collection'][matched_collection].append(obj.name)
        
        # Print annotation result
        anomaly_str = "ANOMALY" if is_anomaly else "NORMAL"
        print(f"[{anomaly_str:7}] {obj.name:30} → class: '{class_label}' (from: {matched_collection or 'default'})")
    
    # Print summary
    print("\n" + "=" * 70)
    print("ANNOTATION SUMMARY")
    print("=" * 70)
    print(f"Total mesh objects:  {stats['total_objects']}")
    print(f"Annotated:           {stats['annotated']}")
    print(f"Skipped:             {stats['skipped']}")
    
    print("\n--- Objects by Class Label ---")
    for class_label, objects in sorted(stats['by_class'].items()):
        print(f"  '{class_label}': {len(objects)} objects")
        for obj_name in objects[:5]:  # Show first 5
            print(f"      - {obj_name}")
        if len(objects) > 5:
            print(f"      ... and {len(objects) - 5} more")
    
    print("\n--- Objects by Collection ---")
    for collection, objects in sorted(stats['by_collection'].items()):
        class_label, is_anomaly = COLLECTION_TO_CLASS.get(collection, DEFAULT_CLASS)
        anomaly_str = "ANOMALY" if is_anomaly else "NORMAL"
        print(f"  '{collection}' → '{class_label}' [{anomaly_str}]: {len(objects)} objects")
    
    print("\n" + "=" * 70)
    print("ANNOTATION COMPLETE")
    print("=" * 70)
    
    return stats


def verify_annotations():
    """
    Verify that annotations were applied correctly.
    Run this to check your scene after annotation.
    """
    print("\n" + "=" * 70)
    print("VERIFYING ANNOTATIONS")
    print("=" * 70)
    
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    
    annotated = 0
    missing = 0
    
    for obj in mesh_objects:
        if "class_label" in obj:
            annotated += 1
            print(f"✓ {obj.name:30} class='{obj['class_label']}', is_anomaly={obj.get('is_anomaly', 'N/A')}")
        else:
            missing += 1
            print(f"✗ {obj.name:30} NO ANNOTATION")
    
    print("-" * 70)
    print(f"Annotated: {annotated}/{len(mesh_objects)}")
    print(f"Missing:   {missing}/{len(mesh_objects)}")
    print("=" * 70)


def list_collections():
    """
    List all collections in the scene.
    Useful to see what collections exist before setting up the mapping.
    """
    print("\n" + "=" * 70)
    print("COLLECTIONS IN SCENE")
    print("=" * 70)
    
    for collection in bpy.data.collections:
        objects = [obj.name for obj in collection.objects if obj.type == 'MESH']
        mapped = collection.name in COLLECTION_TO_CLASS
        status = "MAPPED" if mapped else "NOT MAPPED"
        
        print(f"\n[{status}] Collection: '{collection.name}'")
        print(f"  Mesh objects: {len(objects)}")
        
        if mapped:
            class_label, is_anomaly = COLLECTION_TO_CLASS[collection.name]
            print(f"  → class_label: '{class_label}', is_anomaly: {is_anomaly}")
        
        for obj_name in objects[:5]:
            print(f"    - {obj_name}")
        if len(objects) > 5:
            print(f"    ... and {len(objects) - 5} more")
    
    print("\n" + "=" * 70)


# =============================================================================
# RUN THE SCRIPT
# =============================================================================

if __name__ == "__main__":
    # Step 1: List collections (optional - helps you set up mapping)
    list_collections()
    
    # Step 2: Annotate all objects
    stats = annotate_scene()
    
    # Step 3: Verify annotations
    verify_annotations()