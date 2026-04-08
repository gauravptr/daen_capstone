"""
MULTI-ANGLE SCENE SCANNER
=========================
Purpose: Generate comprehensive point cloud by scanning from multiple positions
         around the scene (vertices, midpoints, and overhead), then merge.

Scanner Positions (top-down view):
         
    NW -------- N -------- NE
    |                       |
    |                       |
    W          TOP          E
    |                       |
    |                       |
    SW -------- S -------- SE

Total: 9 scan positions
- 4 corners (NW, NE, SW, SE): Looking diagonally inward and down
- 4 midpoints (N, S, E, W): Looking straight inward and down  
- 1 overhead (TOP): Looking straight down

How to use:
1. Open your Blender scene with annotated objects
2. Adjust SCAN_CONFIG settings as needed
3. Run script in Blender's Scripting tab
4. Output: Combined point cloud CSV with noise

Note: Manually adjust camera FOV in Blender if needed to capture entire scene.
"""

import bpy
import csv
import os
import math
import random
from datetime import datetime
from mathutils import Vector, Matrix

# =============================================================================
# CONFIGURATION
# =============================================================================

SCAN_CONFIG = {
    # === OUTPUT SETTINGS ===
    'output_directory': r"C:\Users\grsha\Desktop\DAEN 460\scenes\annotation_test",
    'output_filename': "combined_scan.csv",
    'save_individual_scans': True,  # Also save each scan separately
    
    # === SCENE BOUNDS ===
    # Set to 'auto' to automatically calculate from scene objects
    # Or specify manually: {'min': (-5, -5, 0), 'max': (5, 5, 2)}
    'scene_bounds': 'auto',
    
    # Collections to include when calculating bounds (empty = all)
    'include_collections': [],  # e.g., ['Threats', 'Natural', 'Background']
    
    # Collections to exclude from scanning
    'exclude_collections': ['Scanner', 'Cameras', 'Lights'],

    # === SCAN ENGINE ===
    # True: use blAInder scanner operator then label captured points
    # False: use pure raycast scan (legacy mode)
    'use_blainder_scan': True,
    'scanner_object_name': 'ScannerCamera',
    # If True, patch invalid image texture nodes before/after a failed scan.
    # This avoids range_scanner assertion errors on empty texture images.
    'auto_fix_invalid_textures': True,
    
    # === SCANNER POSITIONING ===
    'scanner_height': 12.0,          # Height above scene max Z
    'scanner_inset': 0.5,           # How far inside bounds to place corner/edge scanners
    'look_at_height': 0.0,          # Z height of the point scanners look at (usually seabed level)
    
    # === SCAN PARAMETERS ===
    'fov_horizontal': 90.0,         # Degrees - adjust to capture full scene
    'fov_vertical': 90.0,           # Degrees - adjust to capture full scene
    'resolution': 0.5,              # Degrees between rays (smaller = more points)
    'max_distance': 50.0,           # Maximum scan range
    
    # === NOISE SETTINGS ===
    'add_noise': True,
    'position_noise_std': 0.2,     # Standard deviation for XYZ noise (meters)
    'dropout_rate': 0.05,           # Fraction of points to randomly drop (0-1)
    'outlier_rate': 0.005,          # Fraction of random outlier points to add
    'outlier_range': 1.0,           # Max distance for outlier offset
    
    # === OUTPUT DATA OPTIONS ===
    'include_normals': True,
    'include_distance': True,
    'include_intensity': True,
    'include_scan_id': True,        # Which scanner captured this point
    'export_noise_values': False,   # Exclude synthetic scanner noise rows from CSV output

    # === CLASS MAPPING ===
    'default_class_id': 0,
    'other_class_id': 99,
    'unknown_class_id': 99,
    'noise_class_id': 99,
    'class_names': {
        0: 'seafloor',
        1: 'cube_anomaly',
        2: 'sphere_anomaly',
        3: 'boat_anomaly',
        4: 'coral',
        5: 'rock',
        6: 'wildlife',
        99: 'unknown',
    },
    # Collection names are matched case-insensitively.
    # Supports both legacy *_anomaly names and direct collection names.
    'collection_to_class_id': {
        'seafloor': 0,
        'cube': 1,
        'cube_anomaly': 1,
        'sphere': 2,
        'shpere': 2,       # Typo compatibility alias
        'sphere_anomaly': 2,
        'boat': 3,
        'boat_anomaly': 3,
        'coral': 4,
        'rock': 5,
        'wildlife': 6,
        'other': 99,
    },
}

# =============================================================================
# HELPER CLASSES
# =============================================================================

class SceneBounds:
    """Calculate and store scene bounding box."""
    
    def __init__(self, config):
        self.config = config
        self.min_corner = None
        self.max_corner = None
        self.center = None
        self.size = None
        self._calculate_bounds()
    
    def _calculate_bounds(self):
        """Calculate bounding box from scene objects."""
        
        if self.config['scene_bounds'] != 'auto':
            # Use manual bounds
            bounds = self.config['scene_bounds']
            self.min_corner = Vector(bounds['min'])
            self.max_corner = Vector(bounds['max'])
        else:
            # Calculate from objects
            min_co = Vector((float('inf'), float('inf'), float('inf')))
            max_co = Vector((float('-inf'), float('-inf'), float('-inf')))
            
            found_objects = False
            
            for obj in bpy.data.objects:
                if obj.type != 'MESH':
                    continue
                
                # Check collection filtering
                obj_collections = [c.name for c in obj.users_collection]
                
                if any(exc in obj_collections for exc in self.config['exclude_collections']):
                    continue
                
                if self.config['include_collections']:
                    if not any(inc in obj_collections for inc in self.config['include_collections']):
                        continue
                
                found_objects = True
                
                # Get world-space bounding box corners
                for corner in obj.bound_box:
                    world_corner = obj.matrix_world @ Vector(corner)
                    min_co.x = min(min_co.x, world_corner.x)
                    min_co.y = min(min_co.y, world_corner.y)
                    min_co.z = min(min_co.z, world_corner.z)
                    max_co.x = max(max_co.x, world_corner.x)
                    max_co.y = max(max_co.y, world_corner.y)
                    max_co.z = max(max_co.z, world_corner.z)
            
            if not found_objects:
                print("WARNING: No objects found, using default bounds")
                min_co = Vector((-5, -5, 0))
                max_co = Vector((5, 5, 2))
            
            self.min_corner = min_co
            self.max_corner = max_co
        
        # Calculate center and size
        self.center = (self.min_corner + self.max_corner) / 2
        self.size = self.max_corner - self.min_corner
    
    def print_info(self):
        """Print bounding box information."""
        print(f"Scene Bounds:")
        print(f"  Min corner: ({self.min_corner.x:.2f}, {self.min_corner.y:.2f}, {self.min_corner.z:.2f})")
        print(f"  Max corner: ({self.max_corner.x:.2f}, {self.max_corner.y:.2f}, {self.max_corner.z:.2f})")
        print(f"  Center: ({self.center.x:.2f}, {self.center.y:.2f}, {self.center.z:.2f})")
        print(f"  Size: ({self.size.x:.2f}, {self.size.y:.2f}, {self.size.z:.2f})")


class ScannerPosition:
    """Represents a scanner position and orientation."""
    
    def __init__(self, name, position, look_at):
        self.name = name
        self.position = Vector(position)
        self.look_at = Vector(look_at)
        self.direction = (self.look_at - self.position).normalized()
    
    def get_rotation_matrix(self):
        """Calculate rotation matrix to look at target."""
        direction = self.direction
        
        # Calculate rotation to align -Z with direction
        # Default forward is -Z in Blender
        up = Vector((0, 0, 1))
        
        # Handle case where direction is parallel to up
        if abs(direction.dot(up)) > 0.999:
            up = Vector((0, 1, 0))
        
        right = direction.cross(up).normalized()
        up = right.cross(direction).normalized()
        
        # Build rotation matrix
        rotation_matrix = Matrix((
            (right.x, up.x, -direction.x),
            (right.y, up.y, -direction.y),
            (right.z, up.z, -direction.z)
        )).transposed()
        
        return rotation_matrix


class MultiAngleScanner:
    """Scanner that captures scene from multiple positions."""
    
    def __init__(self, config):
        self.config = config
        self.bounds = SceneBounds(config)
        self.scanner_positions = []
        self.all_points = []
        self.depsgraph = bpy.context.evaluated_depsgraph_get()
        
        self._setup_scanner_positions()
    
    def _setup_scanner_positions(self):
        """Create scanner positions at vertices, midpoints, and overhead."""
        
        config = self.config
        bounds = self.bounds
        
        # Shortcuts
        min_x = bounds.min_corner.x + config['scanner_inset']
        max_x = bounds.max_corner.x - config['scanner_inset']
        min_y = bounds.min_corner.y + config['scanner_inset']
        max_y = bounds.max_corner.y - config['scanner_inset']
        mid_x = bounds.center.x
        mid_y = bounds.center.y
        
        scanner_z = bounds.max_corner.z + config['scanner_height']
        look_at_z = config['look_at_height']
        
        # Target point (center of scene at ground level)
        look_at = Vector((mid_x, mid_y, look_at_z))
        
        # === 4 CORNER POSITIONS ===
        corners = [
            ("NW", (min_x, max_y, scanner_z)),
            ("NE", (max_x, max_y, scanner_z)),
            ("SW", (min_x, min_y, scanner_z)),
            ("SE", (max_x, min_y, scanner_z)),
        ]
        
        # === 4 MIDPOINT POSITIONS ===
        midpoints = [
            ("N", (mid_x, max_y, scanner_z)),
            ("S", (mid_x, min_y, scanner_z)),
            ("E", (max_x, mid_y, scanner_z)),
            ("W", (min_x, mid_y, scanner_z)),
        ]
        
        # === 1 OVERHEAD POSITION ===
        overhead = [
            ("TOP", (mid_x, mid_y, scanner_z)),
        ]
        
        # Create scanner position objects
        for name, pos in corners + midpoints:
            self.scanner_positions.append(ScannerPosition(name, pos, look_at))
        
        # Overhead looks straight down
        overhead_pos = overhead[0][1]
        overhead_look_at = (mid_x, mid_y, look_at_z)
        self.scanner_positions.append(ScannerPosition("TOP", overhead_pos, overhead_look_at))
    
    def _get_ray_direction(self, scanner_pos, h_angle_rad, v_angle_rad):
        """Calculate ray direction for given angles relative to scanner orientation."""
        
        # Base direction (scanner looking direction)
        base_dir = scanner_pos.direction
        
        # Create perpendicular vectors for horizontal and vertical rotation
        up = Vector((0, 0, 1))
        if abs(base_dir.dot(up)) > 0.999:
            up = Vector((0, 1, 0))
        
        right = base_dir.cross(up).normalized()
        up = right.cross(base_dir).normalized()
        
        # Apply angular offsets
        # Rotate around up vector (horizontal) and right vector (vertical)
        h_offset = right * math.sin(h_angle_rad)
        v_offset = up * math.sin(v_angle_rad)
        
        # Combine with base direction
        direction = (base_dir * math.cos(h_angle_rad) * math.cos(v_angle_rad) + 
                     h_offset * math.cos(v_angle_rad) + 
                     v_offset)
        
        return direction.normalized()
    
    def _add_noise_to_point(self, point_data):
        """Add noise to a single point."""
        
        config = self.config
        
        if not config['add_noise']:
            return point_data
        
        # Position noise (Gaussian)
        if config['position_noise_std'] > 0:
            point_data['x'] += random.gauss(0, config['position_noise_std'])
            point_data['y'] += random.gauss(0, config['position_noise_std'])
            point_data['z'] += random.gauss(0, config['position_noise_std'])
        
        # Intensity noise
        if 'intensity' in point_data and config['position_noise_std'] > 0:
            noise = random.gauss(0, 0.1)
            point_data['intensity'] = max(0, min(1, point_data['intensity'] + noise))
        
        return point_data
    
    def _should_drop_point(self):
        """Determine if point should be dropped (simulates sensor dropout)."""
        return random.random() < self.config['dropout_rate']
    
    def _generate_outlier(self, base_point):
        """Generate an outlier point near the base point."""
        
        outlier_range = self.config['outlier_range']
        
        noise_id = self.config.get('noise_class_id', self.config.get('unknown_class_id', 99))

        return {
            'x': base_point['x'] + random.uniform(-outlier_range, outlier_range),
            'y': base_point['y'] + random.uniform(-outlier_range, outlier_range),
            'z': base_point['z'] + random.uniform(-outlier_range, outlier_range),
            'distance': base_point.get('distance', 0) + random.uniform(-1, 1),
            'object_name': 'noise_outlier',
            'class_label': self._class_name(noise_id),
            'is_anomaly': 0,
            'class_id': noise_id,
            'scan_id': base_point.get('scan_id', 'unknown'),
        }
    
    def _calculate_intensity(self, ray_dir, normal, distance):
        """Calculate simulated return intensity."""
        
        # Base intensity from incidence angle
        incidence = max(0, -ray_dir.dot(normal))
        
        # Distance attenuation
        max_dist = self.config['max_distance']
        attenuation = 1.0 - (distance / max_dist) ** 2
        attenuation = max(0, attenuation)
        
        intensity = incidence * attenuation
        return round(intensity, 4)

    def _class_name(self, class_id):
        """Return class name for class id, falling back to 'other'."""

        class_names = self.config.get('class_names', {})
        unknown_id = self.config.get('unknown_class_id', 99)
        return class_names.get(class_id, class_names.get(unknown_id, 'unknown'))

    def _get_class_id_from_collections(self, obj):
        """Resolve class id from object collection names."""

        mapping = self.config.get('collection_to_class_id', {})
        normalized_map = {k.lower(): v for k, v in mapping.items()}

        for col in obj.users_collection:
            class_id = normalized_map.get(col.name.lower())
            if class_id is not None:
                return class_id

        return None

    def _resolve_object_class(self, obj):
        """Resolve (class_id, class_label, is_anomaly) with robust fallbacks."""

        class_names = self.config.get('class_names', {})
        default_id = self.config.get('default_class_id', 0)
        unknown_id = self.config.get('unknown_class_id', 99)

        # 1) Prefer explicit numeric class id if valid.
        raw_id = obj.get('class_id', None)
        resolved_id = None
        if raw_id is not None:
            try:
                parsed_id = int(raw_id)
                if parsed_id in class_names:
                    resolved_id = parsed_id
            except Exception:
                resolved_id = None

        # 2) Fallback to collection mapping.
        if resolved_id is None:
            resolved_id = self._get_class_id_from_collections(obj)

        # 3) Fallback to class_label if it already matches known class names.
        if resolved_id is None:
            raw_label = str(obj.get('class_label', '')).strip().lower()
            reverse_map = {name.lower(): cid for cid, name in class_names.items()}
            resolved_id = reverse_map.get(raw_label)

        # 4) Final fallback.
        if resolved_id is None:
            resolved_id = unknown_id

        class_label = class_names.get(resolved_id, self._class_name(unknown_id))

        is_anomaly = 1 if obj.get('is_anomaly', False) else 0
        if resolved_id in {1, 2, 3}:
            is_anomaly = 1

        # Seafloor is always normal background.
        if resolved_id == default_id:
            is_anomaly = 0

        return resolved_id, class_label, is_anomaly

    def _get_or_create_camera(self):
        """Get scene camera, creating one if necessary."""

        scene = bpy.context.scene
        camera = scene.camera

        if camera is None:
            bpy.ops.object.camera_add()
            camera = bpy.context.active_object
            camera.name = self.config.get('scanner_object_name', 'ScannerCamera')
            scene.camera = camera

        return camera

    def _set_camera_pose(self, camera, scanner_pos):
        """Place and orient camera to match scanner position."""

        camera.location = scanner_pos.position
        direction = (scanner_pos.look_at - scanner_pos.position).normalized()
        camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()

    def _ensure_fallback_image(self):
        """Create (or reuse) a tiny valid image for broken texture slots."""

        image_name = "range_scanner_fallback_1x1"
        image = bpy.data.images.get(image_name)

        if image is None:
            image = bpy.data.images.new(name=image_name, width=1, height=1, alpha=True)
            image.generated_color = (0.5, 0.5, 0.5, 1.0)

        return image

    def _fix_invalid_texture_nodes(self):
        """Attach a fallback image to TEX_IMAGE nodes with missing/empty image data."""

        fallback_image = self._ensure_fallback_image()
        fixed_count = 0

        for material in bpy.data.materials:
            if material is None or material.node_tree is None:
                continue

            for node in material.node_tree.nodes:
                if node.type != 'TEX_IMAGE':
                    continue

                image = node.image
                is_invalid = (
                    image is None or
                    getattr(image, 'pixels', None) is None or
                    len(image.pixels) == 0
                )

                if is_invalid:
                    node.image = fallback_image
                    fixed_count += 1

        if fixed_count > 0:
            print(f"  Patched {fixed_count} invalid image texture node(s) for scanner compatibility")

        return fixed_count

    def _is_excluded_object(self, obj):
        """Return True when object should be ignored for labeling."""

        if obj is None:
            return True

        if obj.type != 'MESH':
            return True

        name_lower = obj.name.lower()
        if 'real_values' in name_lower or 'noise_values' in name_lower:
            return True

        obj_collections = [c.name for c in obj.users_collection]
        if any(exc in obj_collections for exc in self.config['exclude_collections']):
            return True

        return False

    def _label_point_from_scene(self, scanner_origin, point_world, scan_id):
        """Assign labels by raycasting from scanner origin toward captured point."""

        direction = point_world - scanner_origin
        distance = direction.length

        if distance <= 1e-6:
            unknown_id = self.config.get('unknown_class_id', 99)
            return {
                'x': round(point_world.x, 6),
                'y': round(point_world.y, 6),
                'z': round(point_world.z, 6),
                'class_label': self._class_name(unknown_id),
                'is_anomaly': 0,
                'class_id': unknown_id,
                'object_name': 'unknown',
                'distance': 0.0,
                'scan_id': scan_id,
            }

        ray_dir = direction.normalized()
        hit, _, normal, _, obj, _ = bpy.context.scene.ray_cast(
            self.depsgraph,
            scanner_origin,
            ray_dir,
            distance=distance + 0.5
        )

        unknown_id = self.config.get('unknown_class_id', 99)
        point_data = {
            'x': round(point_world.x, 6),
            'y': round(point_world.y, 6),
            'z': round(point_world.z, 6),
            'class_label': self._class_name(unknown_id),
            'is_anomaly': 0,
            'class_id': unknown_id,
            'object_name': 'unknown',
        }

        if hit and not self._is_excluded_object(obj):
            class_id, class_label, is_anomaly = self._resolve_object_class(obj)
            point_data['class_label'] = class_label
            point_data['is_anomaly'] = is_anomaly
            point_data['class_id'] = class_id
            point_data['object_name'] = obj.name

            if self.config['include_normals']:
                point_data['normal_x'] = round(normal.x, 6)
                point_data['normal_y'] = round(normal.y, 6)
                point_data['normal_z'] = round(normal.z, 6)

            if self.config['include_intensity']:
                point_data['intensity'] = self._calculate_intensity(ray_dir, normal, distance)
        elif self.config['include_normals']:
            point_data['normal_x'] = 0.0
            point_data['normal_y'] = 0.0
            point_data['normal_z'] = 0.0

        if self.config['include_distance']:
            point_data['distance'] = round(distance, 6)

        if self.config['include_scan_id']:
            point_data['scan_id'] = scan_id

        return point_data

    def _scan_with_blainder(self, scanner_pos):
        """Run blAInder scanner at one position, then label captured points."""

        camera = self._get_or_create_camera()
        self._set_camera_pose(camera, scanner_pos)

        scene = bpy.context.scene
        if hasattr(scene, 'scannerProperties'):
            scene.scannerProperties.scannerObject = camera

        if self.config.get('auto_fix_invalid_textures', True):
            self._fix_invalid_texture_nodes()

        objects_before = set(obj.name for obj in bpy.data.objects)

        try:
            bpy.ops.wm.execute_scan()
        except Exception as exc:
            # The range_scanner extension can assert on invalid/empty image textures.
            if self.config.get('auto_fix_invalid_textures', True):
                print("  Scan failed; retrying once after texture sanitization...")
                self._fix_invalid_texture_nodes()
                try:
                    bpy.ops.wm.execute_scan()
                except Exception as retry_exc:
                    raise RuntimeError(
                        "blAInder scan failed after texture sanitization. "
                        "Check scene materials/textures for invalid image nodes."
                    ) from retry_exc
            else:
                raise RuntimeError(
                    "blAInder scan failed. Ensure the scanner addon is enabled and configured."
                ) from exc

        objects_after = set(obj.name for obj in bpy.data.objects)
        new_names = objects_after - objects_before

        real_points = []
        noise_points = []
        created_scan_objects = []

        for obj_name in new_names:
            obj = bpy.data.objects.get(obj_name)
            if obj is None or obj.type != 'MESH':
                continue

            name_lower = obj_name.lower()
            if 'real_values' not in name_lower and 'noise_values' not in name_lower:
                continue

            created_scan_objects.append(obj)

            target = noise_points if 'noise_values' in name_lower else real_points
            for vertex in obj.data.vertices:
                target.append(obj.matrix_world @ vertex.co)

        # Remove generated scan meshes so they don't interfere with future labels/scans.
        for obj in created_scan_objects:
            bpy.data.objects.remove(obj, do_unlink=True)

        points = []
        for point_world in real_points:
            points.append(self._label_point_from_scene(scanner_pos.position, point_world, scanner_pos.name))

        if self.config.get('export_noise_values', False):
            for point_world in noise_points:
                noise_id = self.config.get('noise_class_id', self.config.get('unknown_class_id', 99))
                noise_row = {
                    'x': round(point_world.x, 6),
                    'y': round(point_world.y, 6),
                    'z': round(point_world.z, 6),
                    'class_label': self._class_name(noise_id),
                    'is_anomaly': 0,
                    'class_id': noise_id,
                    'object_name': 'noise_values',
                }

                if self.config['include_distance']:
                    noise_row['distance'] = round((point_world - scanner_pos.position).length, 6)
                if self.config['include_normals']:
                    noise_row['normal_x'] = 0.0
                    noise_row['normal_y'] = 0.0
                    noise_row['normal_z'] = 0.0
                if self.config['include_intensity']:
                    noise_row['intensity'] = 0.0
                if self.config['include_scan_id']:
                    noise_row['scan_id'] = scanner_pos.name

                points.append(noise_row)

        return points, len(real_points)

    def _scan_with_raycast(self, scanner_pos):
        """Legacy pure raycast scan from one scanner position."""

        raise NotImplementedError(
            "Raycast mode is disabled in this hybrid build. "
            "Set 'use_blainder_scan' to True and use the blAInder scanner operator."
        )

    def scan_from_position(self, scanner_pos):
        """Perform scan from a single scanner position."""

        if self.config.get('use_blainder_scan', True):
            return self._scan_with_blainder(scanner_pos)
        return self._scan_with_raycast(scanner_pos)
    
    def scan_all_positions(self):
        """Scan from all positions and collect points."""
        
        print("=" * 70)
        print("MULTI-ANGLE SCENE SCANNER")
        print("=" * 70)
        self.bounds.print_info()
        print(f"Scanner positions: {len(self.scanner_positions)}")

        total_hits = 0

        for idx, scanner_pos in enumerate(self.scanner_positions, 1):
            print("\n" + "-" * 70)
            print(
                f"[{idx}/{len(self.scanner_positions)}] Scanning from {scanner_pos.name} "
                f"at ({scanner_pos.position.x:.2f}, {scanner_pos.position.y:.2f}, {scanner_pos.position.z:.2f})"
            )

            points, hits = self.scan_from_position(scanner_pos)
            total_hits += hits
            self.all_points.extend(points)

            print(f"  Rays with hits: {hits}")
            print(f"  Points kept: {len(points)}")

            if self.config['save_individual_scans']:
                individual_name = f"scan_{scanner_pos.name}.csv"
                individual_path = os.path.join(self.config['output_directory'], individual_name)
                self._save_points_csv(individual_path, points)
                print(f"  Saved individual scan: {individual_path}")

        print("\n" + "=" * 70)
        print("SCAN COMPLETE")
        print(f"Total ray hits: {total_hits}")
        print(f"Total exported points: {len(self.all_points)}")
        print("=" * 70)

        return self.all_points

    def _csv_fieldnames(self):
        """Build CSV header in a stable order based on enabled options."""

        fields = ['x', 'y', 'z', 'class_label', 'is_anomaly', 'class_id', 'object_name']

        if self.config['include_distance']:
            fields.append('distance')

        if self.config['include_normals']:
            fields.extend(['normal_x', 'normal_y', 'normal_z'])

        if self.config['include_intensity']:
            fields.append('intensity')

        if self.config['include_scan_id']:
            fields.append('scan_id')

        return fields

    def _save_points_csv(self, output_path, points):
        """Write points to CSV with a deterministic header."""

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fieldnames = self._csv_fieldnames()

        def _write_csv(path_to_write):
            with open(path_to_write, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for p in points:
                    row = {k: p.get(k, '') for k in fieldnames}
                    writer.writerow(row)

        try:
            _write_csv(output_path)
            return output_path
        except PermissionError:
            # Common when the CSV is open in Excel or another viewer.
            base, ext = os.path.splitext(output_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fallback_path = f"{base}_{timestamp}{ext}"
            print(f"  WARNING: File locked, writing to fallback: {fallback_path}")
            _write_csv(fallback_path)
            return fallback_path

    def export_combined(self):
        """Export all collected points to one combined CSV."""

        output_path = os.path.join(
            self.config['output_directory'],
            self.config['output_filename']
        )
        return self._save_points_csv(output_path, self.all_points)


def run_multi_angle_scan(config):
    """Entrypoint for running the multi-angle scanner in Blender."""

    scanner = MultiAngleScanner(config)
    scanner.scan_all_positions()
    output_path = scanner.export_combined()

    print("\nDone.")
    print(f"Combined output: {output_path}")


if __name__ == "__main__":
    run_multi_angle_scan(SCAN_CONFIG)