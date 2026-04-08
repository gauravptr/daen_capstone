import bpy
import csv
import os
from mathutils import Vector

def manual_raycast_scan(scanner_name, output_file, fov_h=60, fov_v=60, steps_h=50, steps_v=50, max_distance=10.0):
    """
    Perform a simple raycast scan and export with class labels.
    This is a simplified scanner for testing annotation pipeline.
    """
    
    import math
    
    # Get scanner object
    scanner = bpy.data.objects.get(scanner_name)
    if not scanner:
        print(f"ERROR: Scanner object '{scanner_name}' not found!")
        return
    
    # Get depsgraph for raycasting
    depsgraph = bpy.context.evaluated_depsgraph_get()
    
    # Scanner position and orientation
    scanner_pos = scanner.matrix_world.translation
    scanner_matrix = scanner.matrix_world.to_3x3()
    
    # Calculate angular steps
    h_start = -fov_h / 2
    h_end = fov_h / 2
    v_start = -fov_v / 2
    v_end = fov_v / 2
    
    h_step = fov_h / steps_h
    v_step = fov_v / steps_v
    
    # Store results
    points = []
    
    print(f"Starting scan from '{scanner_name}'...")
    print(f"FOV: {fov_h}° x {fov_v}°, Steps: {steps_h} x {steps_v}")
    
    # Perform raycasting
    for i in range(steps_h + 1):
        h_angle = math.radians(h_start + i * h_step)
        
        for j in range(steps_v + 1):
            v_angle = math.radians(v_start + j * v_step)
            
            # Calculate ray direction (local space)
            local_dir = Vector((
                math.sin(h_angle) * math.cos(v_angle),
                math.sin(v_angle),
                -math.cos(h_angle) * math.cos(v_angle)
            ))
            
            # Transform to world space
            world_dir = scanner_matrix @ local_dir
            world_dir.normalize()
            
            # Perform raycast
            result, location, normal, index, obj, matrix = bpy.context.scene.ray_cast(
                depsgraph,
                scanner_pos,
                world_dir,
                distance=max_distance
            )
            
            if result and obj:
                # Get class label from object's custom property
                class_label = obj.get("class_label", "unknown")
                is_anomaly = obj.get("is_anomaly", False)
                
                # Calculate distance
                distance = (location - scanner_pos).length
                
                # Store point data
                point_data = {
                    'x': location.x,
                    'y': location.y,
                    'z': location.z,
                    'distance': distance,
                    'object_name': obj.name,
                    'class_label': class_label,
                    'is_anomaly': int(is_anomaly),
                    'normal_x': normal.x,
                    'normal_y': normal.y,
                    'normal_z': normal.z
                }
                points.append(point_data)
    
    print(f"Scan complete! {len(points)} points captured.")
    
    # Export to CSV
    if points:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Write CSV
        fieldnames = ['x', 'y', 'z', 'distance', 'object_name', 'class_label', 'is_anomaly', 'normal_x', 'normal_y', 'normal_z']
        
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(points)
        
        print(f"Exported to: {output_file}")
        
        # Print summary
        anomaly_count = sum(1 for p in points if p['is_anomaly'])
        background_count = len(points) - anomaly_count
        print(f"\nSummary:")
        print(f"  Total points: {len(points)}")
        print(f"  Anomaly points: {anomaly_count}")
        print(f"  Background points: {background_count}")
        
        # Print per-object breakdown
        object_counts = {}
        for p in points:
            obj_name = p['object_name']
            if obj_name not in object_counts:
                object_counts[obj_name] = {'count': 0, 'class': p['class_label']}
            object_counts[obj_name]['count'] += 1
        
        print("\nPer-object breakdown:")
        for obj_name, data in object_counts.items():
            print(f"  {obj_name}: {data['count']} points (class: {data['class']})")
    
    return points


# Run the custom scan
if __name__ == "__main__":
    # Output file path (in same directory as .blend file)
    output_path = bpy.path.abspath("//annotated_pointcloud.csv")
    
    # If blend file not saved, use temp directory
    if output_path == "annotated_pointcloud.csv":
        import tempfile
        output_path = os.path.join(tempfile.gettempdir(), "annotated_pointcloud.csv")
    
    # Run scan
    points = manual_raycast_scan(
        scanner_name="Scanner_Origin",
        output_file=output_path,
        fov_h=60,
        fov_v=60,
        steps_h=100,
        steps_v=100,
        max_distance=15.0
    )