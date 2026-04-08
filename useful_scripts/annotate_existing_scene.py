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

# Map collection names to class labels/class IDs
# Format: "Collection Name": ("class_label", class_id, is_anomaly_flag)
#
# is_anomaly_flag: 
#   True = This is something you want to detect (anomaly, target, etc.)
#   False = This is background/normal terrain

COLLECTION_TO_CLASS = {
    "seafloor": ("seafloor", 0, False),
    "cube_anomaly": ("cube_anomaly", 1, True),
    "sphere_anomaly": ("sphere_anomaly", 2, True),
    "boat_anomaly": ("boat_anomaly", 3, True),
    "coral": ("coral", 4, False),
    "rock": ("rock", 5, False),
    "wildlife": ("wildlife", 6, False),
    "other": ("unknown", 99, False),
}

# Collections to skip (won't be annotated)
SKIP_COLLECTIONS = [
    "Scanner",
    "Cameras", 
    "Lights",
    "Empties",
]
SKIP_COLLECTIONS_LOWER = {name.lower() for name in SKIP_COLLECTIONS}

# Default label for objects in unmapped collections
DEFAULT_CLASS = ("unknown", 99, False)

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


def annotate_object(obj, class_label, class_id, is_anomaly):
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
    
    obj["class_id"] = int(class_id)


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
        if any(col.lower() in SKIP_COLLECTIONS_LOWER for col in obj_collections):
            print(f"[SKIP] {obj.name} (in skip collection)")
            stats['skipped'] += 1
            continue
        
        # Find the appropriate class label
        class_label, class_id, is_anomaly = DEFAULT_CLASS
        matched_collection = None
        
        for collection_name in obj_collections:
            key = collection_name.lower()
            if key in COLLECTION_TO_CLASS:
                class_label, class_id, is_anomaly = COLLECTION_TO_CLASS[key]
                matched_collection = key
                break
        
        # Annotate the object
        annotate_object(obj, class_label, class_id, is_anomaly)
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
        print(
            f"[{anomaly_str:7}] {obj.name:30} → class: '{class_label}' "
            f"(id={class_id}, from: {matched_collection or 'default'})"
        )
    
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
        class_label, class_id, is_anomaly = COLLECTION_TO_CLASS.get(collection.lower(), DEFAULT_CLASS)
        anomaly_str = "ANOMALY" if is_anomaly else "NORMAL"
        print(f"  '{collection}' → '{class_label}' id={class_id} [{anomaly_str}]: {len(objects)} objects")
    
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
        mapped = collection.name.lower() in COLLECTION_TO_CLASS
        status = "MAPPED" if mapped else "NOT MAPPED"
        
        print(f"\n[{status}] Collection: '{collection.name}'")
        print(f"  Mesh objects: {len(objects)}")
        
        if mapped:
            class_label, class_id, is_anomaly = COLLECTION_TO_CLASS[collection.name.lower()]
            print(f"  → class_label: '{class_label}', class_id: {class_id}, is_anomaly: {is_anomaly}")
        
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