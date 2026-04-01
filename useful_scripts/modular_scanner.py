"""
SCRIPT 2: MODULAR POINT CLOUD SCANNER
=====================================
Purpose: Scan any annotated Blender scene and export point cloud with class labels.

How to use:
1. First run Script 1 to annotate your scene
2. Modify the SCANNER_CONFIG settings below
3. Run this script in Blender's Scripting tab
4. Check the output CSV file

Prerequisites:
- Scene must have objects with "class_label" custom property
- Run Script 1 first if objects aren't annotated
"""

import bpy
import csv
import os
import math
from mathutils import Vector
from datetime import datetime

# =============================================================================
# CONFIGURATION - MODIFY THIS FOR YOUR SCAN
# =============================================================================

SCANNER_CONFIG = {
    # === OUTPUT SETTINGS ===
    # Where to save the point cloud CSV
    'output_directory': r"C:\Users\grsha\Desktop\DAEN 460\scenes\annotation_test",
    'output_filename': "pointcloud_{timestamp}.csv",  # {timestamp} will be replaced
    
    # === SCANNER POSITION ===
    # Option 1: Use a specific object as scanner origin
    'use_object_as_scanner': True,
    'scanner_object_name': "Scanner_Camera",  # Name of camera/empty to use
    
    # Option 2: Use fixed position (if use_object_as_scanner is False)
    'scanner_position': (0, 0, 5),
    'scanner_rotation_deg': (90, 0, 0),  # Pointing down
    
    # === SCAN PARAMETERS ===
    'fov_horizontal': 60.0,      # Horizontal field of view (degrees)
    'fov_vertical': 60.0,        # Vertical field of view (degrees)
    'resolution_horizontal': 0.5, # Horizontal resolution (degrees per ray)
    'resolution_vertical': 0.5,   # Vertical resolution (degrees per ray)
    'max_distance': 20.0,        # Maximum scan distance (meters)
    
    # === SCAN DIRECTION ===
    # 'DOWN' = Scan downward (-Z)
    # 'FORWARD' = Scan forward (-Y in Blender)
    # 'CAMERA' = Use camera/object orientation
    'scan_direction': 'DOWN',
    
    # === DATA OPTIONS ===
    'include_normals': True,      # Include surface normal vectors
    'include_distance': True,     # Include distance from scanner
    'include_object_name': True,  # Include source object name
    'include_intensity': True,    # Include simulated intensity (based on angle)
    
    # === FILTERING ===
    # Only scan objects with these class labels (empty = scan all)
    'include_classes': [],  # e.g., ['anomaly', 'rock', 'background']
    # Skip objects with these class labels
    'exclude_classes': [],  # e.g., ['unknown']
}

# =============================================================================
# SCANNER CLASS
# =============================================================================

class ModularPointCloudScanner:
    """
    A modular LiDAR/Sonar scanner that works with any annotated Blender scene.
    """
    
    def __init__(self, config):
        """Initialize scanner with configuration."""
        self.config = config
        self.points = []
        self.stats = {
            'total_rays': 0,
            'hits': 0,
            'misses': 0,
            'filtered': 0,
            'by_class': {},
            'by_object': {},
        }
        
        # Setup scanner position and orientation
        self._setup_scanner()
        
        # Calculate ray grid
        self.steps_h = int(config['fov_horizontal'] / config['resolution_horizontal']) + 1
        self.steps_v = int(config['fov_vertical'] / config['resolution_vertical']) + 1
        self.stats['total_rays'] = self.steps_h * self.steps_v
    
    def _setup_scanner(self):
        """Setup scanner position and orientation."""
        config = self.config
        
        if config['use_object_as_scanner']:
            # Get scanner object
            scanner_obj = bpy.data.objects.get(config['scanner_object_name'])
            if scanner_obj:
                self.position = scanner_obj.matrix_world.translation.copy()
                self.rotation_matrix = scanner_obj.matrix_world.to_3x3()
                print(f"Using object '{scanner_obj.name}' as scanner")
                print(f"  Position: {tuple(round(c, 2) for c in self.position)}")
            else:
                print(f"WARNING: Scanner object '{config['scanner_object_name']}' not found!")
                print("Falling back to fixed position.")
                self._setup_fixed_position()
        else:
            self._setup_fixed_position()
    
    def _setup_fixed_position(self):
        """Setup scanner with fixed position."""
        config = self.config
        self.position = Vector(config['scanner_position'])
        
        # Create rotation matrix from euler angles
        from mathutils import Euler
        rotation_euler = Euler((
            math.radians(config['scanner_rotation_deg'][0]),
            math.radians(config['scanner_rotation_deg'][1]),
            math.radians(config['scanner_rotation_deg'][2])
        ))
        self.rotation_matrix = rotation_euler.to_matrix()
        print(f"Using fixed position: {tuple(self.position)}")
    
    def _get_ray_direction(self, h_angle_rad, v_angle_rad):
        """
        Calculate ray direction based on scan direction setting.
        
        Args:
            h_angle_rad: Horizontal angle in radians
            v_angle_rad: Vertical angle in radians
        
        Returns:
            Normalized direction vector
        """
        scan_dir = self.config['scan_direction']
        
        if scan_dir == 'DOWN':
            # Primary direction is -Z (down)
            local_dir = Vector((
                math.sin(h_angle_rad),
                math.sin(v_angle_rad),
                -math.cos(h_angle_rad) * math.cos(v_angle_rad)
            ))
        elif scan_dir == 'FORWARD':
            # Primary direction is -Y (forward in Blender)
            local_dir = Vector((
                math.sin(h_angle_rad),
                -math.cos(h_angle_rad) * math.cos(v_angle_rad),
                math.sin(v_angle_rad)
            ))
        elif scan_dir == 'CAMERA':
            # Use object's local -Z axis
            local_dir = Vector((
                math.sin(h_angle_rad) * math.cos(v_angle_rad),
                math.sin(v_angle_rad),
                -math.cos(h_angle_rad) * math.cos(v_angle_rad)
            ))
            local_dir = self.rotation_matrix @ local_dir
        else:
            # Default to down
            local_dir = Vector((
                math.sin(h_angle_rad),
                math.sin(v_angle_rad),
                -math.cos(h_angle_rad) * math.cos(v_angle_rad)
            ))
        
        return local_dir.normalized()
