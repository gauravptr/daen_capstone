"""
Generate one randomized pilot Blender scene and save it to ProceduralScenes.

Usage:
1) Open your base scene in Blender.
2) Open Blender Scripting tab.
3) Paste this script or run this file.
4) Press Run Script.

This script only creates and saves one randomized scene variant.
It does not run scanning or export point-cloud data.
"""

import bpy
import math
import os
import random
from datetime import datetime

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------
SEED = 460
FORCE_ANOMALY = True

# Change this if your project is in a different location.
OUTPUT_DIR = r"C:\Users\grsha\Desktop\DAEN 460\scenes\ProceduralScenes"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Scene bounds (50m x 50m)
X_MIN, X_MAX = -25.0, 25.0
Y_MIN, Y_MAX = -25.0, 25.0
Z_BASE = 0.0

# Randomization ranges
LARGE_ROCK_COUNT_RANGE = (1, 2)
CLUSTER_COUNT_RANGE = (4, 7)
CLUSTER_SIZE_RANGE = (5, 10)
CLUSTER_RADIUS = 5.0
SCATTERED_SMALL_COUNT_RANGE = (10, 20)
TURTLE_CHANCE = 0.3
TURTLE_HEIGHT_RANGE = (1.0, 3.0)
ROCK_SCALE_RANGE = (0.7, 1.0)
SMALL_SCALE_RANGE = (0.8, 1.2)

ANOMALY_TYPES = {
    "boat": "tekne",
    "cube": "Cube",
    "sphere": "Mball",
}
LARGE_ROCKS = ["Rock0", "Rock6", "Rock3"]
SMALL_OBJECTS = ["10010_Coral_v1_L3", "Mesh_0"]
OPTIONAL_OBJECTS = ["10042_Sea_Turtle_V2_iterations-2"]
PRESERVE = ["Plane", "Camera", "Light", "TextureField"]


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------
def name_matches(base_name, obj_name):
    return obj_name == base_name or obj_name.startswith(base_name + ".")


def random_position_in_area():
    return (
        random.uniform(X_MIN, X_MAX),
        random.uniform(Y_MIN, Y_MAX),
    )


def random_position_in_cluster(center, radius):
    angle = random.uniform(0.0, 2.0 * math.pi)
    dist = random.uniform(0.0, radius)
    return (
        center[0] + dist * math.cos(angle),
        center[1] + dist * math.sin(angle),
    )


def get_lowest_world_z(obj):
    if obj.type != "MESH" or not obj.data or len(obj.data.vertices) == 0:
        return obj.location.z
    world_vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return min(v.z for v in world_vertices)


def duplicate_object(obj_name):
    source = bpy.data.objects.get(obj_name)
    if source is None:
        return None, None

    dup = source.copy()
    if source.data:
        dup.data = source.data.copy()
    bpy.context.collection.objects.link(dup)

    dup.hide_viewport = False
    dup.hide_render = False
    return dup, source.rotation_euler.copy()


def place_object(obj, x, y, base_rotation, obj_type="small", turtle_mode=False):
    obj.location.x = x
    obj.location.y = y
    obj.location.z = 0.0

    if obj_type == "large_rock":
        obj.rotation_euler = (
            base_rotation[0] + random.uniform(-0.1, 0.1),
            base_rotation[1] + random.uniform(-0.1, 0.1),
            random.uniform(0.0, 2.0 * math.pi),
        )
        s = random.uniform(*ROCK_SCALE_RANGE)
        obj.scale = (s, s, s)
    else:
        obj.rotation_euler = (
            base_rotation[0],
            base_rotation[1],
            random.uniform(0.0, 2.0 * math.pi),
        )
        if obj_type == "small":
            s = random.uniform(*SMALL_SCALE_RANGE)
            obj.scale = (s, s, s)
        else:
            obj.scale = (1.0, 1.0, 1.0)

    bpy.context.view_layer.update()

    if turtle_mode:
        obj.location.z = Z_BASE + random.uniform(*TURTLE_HEIGHT_RANGE)
    elif obj.type == "MESH" and obj.data and len(obj.data.vertices) > 0:
        lowest_z = get_lowest_world_z(obj)
        offset = lowest_z - obj.location.z
        burial = random.uniform(0.0, 0.5)
        obj.location.z = Z_BASE - offset - burial
    else:
        obj.location.z = Z_BASE

    bpy.context.view_layer.update()


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
def run():
    random.seed(SEED)

    print("=" * 72)
    print("ONE-SCENE PILOT GENERATOR")
    print("=" * 72)
    print(f"Seed: {SEED}")
    print(f"Output dir: {OUTPUT_DIR}")

    anomaly_objects = {"boat": [], "cube": [], "sphere": []}
    large_rocks = []
    small_objects = []
    optional_objects = []
    preserved_objects = []

    for obj in bpy.data.objects:
        name = obj.name

        if any(key in name for key in PRESERVE):
            preserved_objects.append(name)
            continue

        matched_anomaly = False
        for anomaly_type, keyword in ANOMALY_TYPES.items():
            if name_matches(keyword, name):
                anomaly_objects[anomaly_type].append(name)
                matched_anomaly = True
                break
        if matched_anomaly:
            continue

        if any(name_matches(key, name) for key in LARGE_ROCKS):
            large_rocks.append(name)
            continue

        if any(name_matches(key, name) for key in OPTIONAL_OBJECTS):
            optional_objects.append(name)
            continue

        if any(name_matches(key, name) for key in SMALL_OBJECTS):
            small_objects.append(name)

    print("Detected source objects:")
    print(f"  Preserved: {len(preserved_objects)}")
    print(f"  Large rocks: {len(large_rocks)}")
    print(f"  Small objects: {len(small_objects)}")
    print(f"  Optional objects: {len(optional_objects)}")
    print(f"  Anomalies: {sum(len(v) for v in anomaly_objects.values())}")

    removed = 0
    for obj in list(bpy.data.objects):
        if obj.get("procedural_pilot") or any(
            prefix in obj.name for prefix in ["noise_values", "real_values", "PathMarker", "ScanPath"]
        ):
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    print(f"Removed old procedural/scan objects: {removed}")

    all_anomaly_names = anomaly_objects["boat"] + anomaly_objects["cube"] + anomaly_objects["sphere"]
    for obj_name in large_rocks + small_objects + optional_objects + all_anomaly_names:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.hide_viewport = True
            obj.hide_render = True

    for obj_name in preserved_objects:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.hide_viewport = False
            obj.hide_render = False

    placement_counts = {
        "large_rocks": 0,
        "small_clustered": 0,
        "small_scattered": 0,
        "optional": 0,
        "anomaly": 0,
    }
    placed_anomalies = []

    if large_rocks:
        n_large = random.randint(*LARGE_ROCK_COUNT_RANGE)
        for _ in range(n_large):
            x, y = random_position_in_area()
            src = random.choice(large_rocks)
            dup, rot = duplicate_object(src)
            if dup:
                dup["procedural_pilot"] = True
                place_object(dup, x, y, rot, obj_type="large_rock")
                placement_counts["large_rocks"] += 1

    if small_objects:
        n_clusters = random.randint(*CLUSTER_COUNT_RANGE)
        for _ in range(n_clusters):
            center = random_position_in_area()
            n_cluster = random.randint(*CLUSTER_SIZE_RANGE)
            for _ in range(n_cluster):
                x, y = random_position_in_cluster(center, CLUSTER_RADIUS)
                src = random.choice(small_objects)
                dup, rot = duplicate_object(src)
                if dup:
                    dup["procedural_pilot"] = True
                    place_object(dup, x, y, rot, obj_type="small")
                    placement_counts["small_clustered"] += 1

        n_scattered = random.randint(*SCATTERED_SMALL_COUNT_RANGE)
        for _ in range(n_scattered):
            x, y = random_position_in_area()
            src = random.choice(small_objects)
            dup, rot = duplicate_object(src)
            if dup:
                dup["procedural_pilot"] = True
                place_object(dup, x, y, rot, obj_type="small")
                placement_counts["small_scattered"] += 1

    if optional_objects and random.random() < TURTLE_CHANCE:
        x, y = random_position_in_area()
        src = random.choice(optional_objects)
        dup, rot = duplicate_object(src)
        if dup:
            dup["procedural_pilot"] = True
            place_object(dup, x, y, rot, obj_type="turtle", turtle_mode=True)
            placement_counts["optional"] += 1

    scene_has_anomaly = False
    if FORCE_ANOMALY:
        available_types = [k for k, v in anomaly_objects.items() if v]
        if available_types:
            chosen_type = random.choice(available_types)
            n_anomaly = random.randint(1, 2)
            for _ in range(n_anomaly):
                src = random.choice(anomaly_objects[chosen_type])
                x, y = random_position_in_area()
                dup, rot = duplicate_object(src)
                if dup:
                    dup["procedural_pilot"] = True
                    place_object(dup, x, y, rot, obj_type="anomaly")
                    placed_anomalies.append(src)
                    placement_counts["anomaly"] += 1
                    scene_has_anomaly = True
        else:
            print("WARNING: No anomaly source objects found; generated scene is clean.")

    label = "anomaly" if scene_has_anomaly else "no_anomaly"
    base_name = f"scene_001_{label}.blend"
    save_path = os.path.join(OUTPUT_DIR, base_name)

    if os.path.exists(save_path):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem, ext = os.path.splitext(base_name)
        save_path = os.path.join(OUTPUT_DIR, f"{stem}_{stamp}{ext}")

    # copy=True saves to new file while keeping your current open file unchanged.
    bpy.ops.wm.save_as_mainfile(filepath=save_path, copy=True)

    print("-" * 72)
    print("Pilot scene generated")
    print(f"Anomaly scene: {scene_has_anomaly}")
    print(f"Placed anomalies: {placed_anomalies}")
    print("Placement counts:")
    for key, value in placement_counts.items():
        print(f"  {key}: {value}")
    print(f"Saved file: {save_path}")
    print("=" * 72)


if __name__ == "__main__":
    run()
