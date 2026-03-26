import bpy
import os
import csv

print("=" * 60)
print("       COMBINING ALL POINT CLOUDS")
print("=" * 60)

output_folder = r"C:\Users\grsha\Desktop\DAEN 460\output"
os.makedirs(output_folder, exist_ok=True)

# Collect all points from Blender objects
all_points = []

for obj in bpy.data.objects:
    if obj.type == 'MESH' and "real_values" in obj.name:
        mesh = obj.data
        for v in mesh.vertices:
            # Transform to world coordinates
            world_co = obj.matrix_world @ v.co
            all_points.append((world_co.x, world_co.y, world_co.z))

print(f"\n📊 Collected {len(all_points):,} total points")

if len(all_points) > 0:
    # Export as PLY
    ply_path = os.path.join(output_folder, "combined_full_scan.ply")
    
    with open(ply_path, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(all_points)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("end_header\n")
        
        for x, y, z in all_points:
            f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")
    
    print(f"\n✅ Exported PLY: {ply_path}")
    file_size = os.path.getsize(ply_path) / (1024*1024)
    print(f"   Size: {file_size:.2f} MB")
    
    # Export as XYZ
    xyz_path = os.path.join(output_folder, "combined_full_scan.xyz")
    with open(xyz_path, 'w') as f:
        for x, y, z in all_points:
            f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")
    
    print(f"✅ Exported XYZ: {xyz_path}")

    # Export combined CSV with full scanner details when frame CSVs are present.
    csv_path = os.path.join(output_folder, "combined_full_scan.csv")
    frame_csv_files = sorted(
        [
            os.path.join(output_folder, f)
            for f in os.listdir(output_folder)
            if f.startswith("_frames_") and f.endswith(".csv")
        ]
    )

    if frame_csv_files:
        header = None
        merged_rows = 0

        with open(csv_path, 'w', newline='') as out_f:
            writer = csv.writer(out_f, delimiter=';')

            for src_path in frame_csv_files:
                with open(src_path, 'r', newline='') as in_f:
                    reader = csv.reader(in_f, delimiter=';')
                    src_header = next(reader, None)

                    if src_header is None:
                        continue

                    if header is None:
                        header = src_header
                        writer.writerow(header)
                    elif src_header != header:
                        print(f"⚠️  Skipping {os.path.basename(src_path)} (header mismatch)")
                        continue

                    for row in reader:
                        if not row:
                            continue
                        writer.writerow(row)
                        merged_rows += 1

        print(f"✅ Exported CSV: {csv_path}")
        print(f"   Included {len(frame_csv_files)} frame CSV files")
        print(f"   Total merged rows: {merged_rows:,}")
    else:
        # Fallback: only XYZ is available from combined mesh points.
        with open(csv_path, 'w') as f:
            f.write("x,y,z\n")
            for x, y, z in all_points:
                f.write(f"{x:.6f},{y:.6f},{z:.6f}\n")

        print(f"✅ Exported CSV: {csv_path}")
        print("   No frame CSV files found; wrote x,y,z only.")
    
    # Show point cloud bounds
    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    zs = [p[2] for p in all_points]
    
    print(f"\n📐 Point cloud bounds:")
    print(f"   X: {min(xs):.2f} to {max(xs):.2f} ({max(xs)-min(xs):.2f}m)")
    print(f"   Y: {min(ys):.2f} to {max(ys):.2f} ({max(ys)-min(ys):.2f}m)")
    print(f"   Z: {min(zs):.2f} to {max(zs):.2f} ({max(zs)-min(zs):.2f}m)")
else:
    print("❌ No points found!")
