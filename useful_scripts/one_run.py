import bpy
import os

# ==============================
# PATHS (EDIT IF NEEDED)
# ==============================
SCENE_SCRIPTS_FOLDER = r"C:\Users\jcwin\OneDrive\Desktop\Capstone\scene scanning scripts"
SCENE_FOLDER         = r"C:\Users\jcwin\OneDrive\Desktop\Capstone\Annotation\ProceduralScenes"
SAVE_FOLDER          = r"C:\Users\jcwin\OneDrive\Desktop\Capstone\Annotation\ProcessedScenes"
OUTPUT_FOLDER        = r"C:\Users\jcwin\OneDrive\Desktop\Capstone\Annotation\output"

os.makedirs(SAVE_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Helper to run a script by filename from SCENE_SCRIPTS_FOLDER
def run_script(script_name):
    script_path = os.path.join(SCENE_SCRIPTS_FOLDER, script_name)
    if not os.path.isfile(script_path):
        print(f"⚠️ Script not found: {script_path}")
        return
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            code = f.read()
        exec(compile(code, script_path, 'exec'), {"__name__": "__main__"})
        print(f"✅ Ran {script_name}")
    except Exception as e:
        print(f"⚠️ {script_name} error: {e}")

# Collect .blend files once
blend_files = [f for f in os.listdir(SCENE_FOLDER) if f.lower().endswith(".blend")]
total_files = len(blend_files)

print("\n========================================")
print(f"   STARTING BATCH FOR {total_files} SCENES")
print("========================================\n")

for i, filename in enumerate(sorted(blend_files)):
    print("\n" + "=" * 60)
    print(f"Processing {filename} ({i+1}/{total_files})")
    print("=" * 60)

    scene_path = os.path.join(SCENE_FOLDER, filename)
    bpy.ops.wm.open_mainfile(filepath=scene_path)

    # ----------------------
    # RUN FIXES / CLEANUP
    # ----------------------
    run_script("ignore_texture.py")
    run_script("scan_readiness.py")
    run_script("delete_hidden.py")

    # ----------------------
    # RUN UPDATED WAYPOINT SCRIPT (50x50_path)
    # ----------------------
    run_script("50X50_path.py")

    # Optional: sanity check on scan_positions
    scan_positions_str = bpy.context.scene.get("scan_positions", None)
    if scan_positions_str is None:
        print("⚠️ No scan_positions found after 50X50_path.py — check that script.")
    else:
        try:
            import ast
            scan_positions = ast.literal_eval(scan_positions_str)
            print(f"🔍 Detected {len(scan_positions)} scan positions in scene.")
        except Exception as e:
            print(f"⚠️ Could not parse scan_positions: {e}")

    # ----------------------
    # RUN FULL BATCH SCAN
    # ----------------------
    run_script("full_batch.py")

    # ----------------------
    # SAVE UPDATED BLEND
    # ----------------------
    name_parts = filename.replace(".blend", "").split("_")
    # name_parts example:
    #   scene_001_anomaly        -> ['scene', '001', 'anomaly']
    #   scene_006_no_anomaly     -> ['scene', '006', 'no', 'anomaly']
    if len(name_parts) >= 2:
        number = name_parts[1]
    else:
        number = f"{i:03d}"

    if len(name_parts) >= 3:
        anomaly = "_".join(name_parts[2:])  # preserves "no_anomaly"
    else:
        anomaly = "noanomaly"

    new_name = f"scene_{number}_{anomaly}.blend"
    save_path = os.path.join(SAVE_FOLDER, new_name)

    bpy.ops.wm.save_as_mainfile(filepath=save_path)
    print(f"✅ Saved updated .blend: {save_path}")

    # ----------------------
    # EXPORT PLY FILE
    # ----------------------
    try:
        import mathutils  # noqa: F401
        all_points = []
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and "real_values" in obj.name:
                mesh = obj.data
                for v in mesh.vertices:
                    world_co = obj.matrix_world @ v.co
                    all_points.append((world_co.x, world_co.y, world_co.z))

        if all_points:
            ply_path = os.path.join(OUTPUT_FOLDER, f"scene_{number}_{anomaly}.ply")
            with open(ply_path, 'w', encoding="utf-8") as f:
                f.write("ply\nformat ascii 1.0\n")
                f.write(f"element vertex {len(all_points)}\n")
                f.write("property float x\nproperty float y\nproperty float z\n")
                f.write("end_header\n")
                for x, y, z in all_points:
                    f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")
            print(f"✅ Exported PLY: {ply_path}")
        else:
            print("⚠️ No points found for PLY export")
    except Exception as e:
        print(f"⚠️ PLY export error: {e}")

print("\n🎉 ALL SCENES PROCESSED!")
