import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# ============================================================
# CONFIGURATION
# ============================================================

output_folder = r"C:\Users\grsha\Desktop\DAEN 460\output"

# ============================================================
# FUNCTION: READ LAS FILES
# ============================================================

def read_las_file(filepath):
    """Read LAS file and return points and labels"""
    try:
        import laspy
        
        las = laspy.read(filepath)
        
        # Get XYZ coordinates
        points = np.vstack([las.x, las.y, las.z]).T
        
        # Get classification/labels if available
        labels = None
        if hasattr(las, 'classification'):
            labels = np.array(las.classification)
        
        print(f"✅ LAS: {os.path.basename(filepath)}")
        print(f"   Points: {len(points):,}")
        print(f"   X range: {points[:,0].min():.2f} to {points[:,0].max():.2f}")
        print(f"   Y range: {points[:,1].min():.2f} to {points[:,1].max():.2f}")
        print(f"   Z range: {points[:,2].min():.2f} to {points[:,2].max():.2f}")
        
        if labels is not None:
            unique_labels = np.unique(labels)
            print(f"   Labels: {unique_labels}")
        
        return points, labels
        
    except Exception as e:
        print(f"❌ Error reading LAS file: {e}")
        return None, None

# ============================================================
# FUNCTION: READ HDF5 FILES
# ============================================================

def read_hdf5_file(filepath):
    """Read HDF5 file and return points and labels"""
    try:
        import h5py
        
        with h5py.File(filepath, 'r') as f:
            print(f"\n📂 HDF5: {os.path.basename(filepath)}")
            print(f"   Keys: {list(f.keys())}")
            
            # Try to find point data
            points = None
            labels = None
            
            # Common key names for points
            point_keys = ['points', 'xyz', 'coordinates', 'data', 'x']
            label_keys = ['labels', 'classification', 'class', 'material', 'partID']
            
            # Recursively print structure
            def print_structure(name, obj):
                print(f"   - {name}: {type(obj).__name__}", end="")
                if hasattr(obj, 'shape'):
                    print(f" {obj.shape}", end="")
                if hasattr(obj, 'dtype'):
                    print(f" [{obj.dtype}]", end="")
                print()
            
            f.visititems(print_structure)
            
            # Try to extract points
            for key in f.keys():
                data = f[key][:]
                if isinstance(data, np.ndarray):
                    if len(data.shape) == 2 and data.shape[1] >= 3:
                        points = data[:, :3]
                        print(f"\n   Found points in '{key}': {points.shape}")
                        break
                    elif len(data.shape) == 1 and key.lower() == 'x':
                        # Separate X, Y, Z arrays
                        if 'y' in f.keys() and 'z' in f.keys():
                            x = f['x'][:]
                            y = f['y'][:]
                            z = f['z'][:]
                            points = np.vstack([x, y, z]).T
                            print(f"\n   Combined X,Y,Z arrays: {points.shape}")
                            break
            
            if points is not None:
                print(f"   Points: {len(points):,}")
                print(f"   X range: {points[:,0].min():.2f} to {points[:,0].max():.2f}")
                print(f"   Y range: {points[:,1].min():.2f} to {points[:,1].max():.2f}")
                print(f"   Z range: {points[:,2].min():.2f} to {points[:,2].max():.2f}")
            
            return points, labels
            
    except Exception as e:
        print(f"❌ Error reading HDF5 file: {e}")
        return None, None

# ============================================================
# FUNCTION: READ CSV FILES
# ============================================================

def read_csv_file(filepath):
    """Read CSV file and return points and labels"""
    try:
        import pandas as pd
        
        df = pd.read_csv(filepath)
        
        print(f"\n📄 CSV: {os.path.basename(filepath)}")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Rows: {len(df):,}")
        
        # Get XYZ
        x_col = 'x' if 'x' in df.columns else df.columns[0]
        y_col = 'y' if 'y' in df.columns else df.columns[1]
        z_col = 'z' if 'z' in df.columns else df.columns[2]
        
        points = df[[x_col, y_col, z_col]].values
        
        # Get labels
        labels = None
        for col in ['material', 'partID', 'label', 'class', 'classification']:
            if col in df.columns:
                labels = df[col].values
                print(f"   Label column: {col}")
                print(f"   Unique labels: {df[col].nunique()}")
                print(f"   Labels: {df[col].unique()[:10]}...")
                break
        
        print(f"   X range: {points[:,0].min():.2f} to {points[:,0].max():.2f}")
        print(f"   Y range: {points[:,1].min():.2f} to {points[:,1].max():.2f}")
        print(f"   Z range: {points[:,2].min():.2f} to {points[:,2].max():.2f}")
        
        return points, labels
        
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return None, None

# ============================================================
# FUNCTION: VISUALIZE POINT CLOUD
# ============================================================

def visualize_points(points, labels=None, title="Point Cloud", max_points=50000):
    """Visualize point cloud using matplotlib"""
    
    if points is None or len(points) == 0:
        print("❌ No points to visualize")
        return
    
    # Subsample if too many points
    if len(points) > max_points:
        idx = np.random.choice(len(points), max_points, replace=False)
        points = points[idx]
        if labels is not None:
            labels = labels[idx]
        print(f"📊 Subsampled to {max_points:,} points for visualization")
    
    fig = plt.figure(figsize=(14, 5))
    
    # 3D View
    ax1 = fig.add_subplot(131, projection='3d')
    
    if labels is not None and not isinstance(labels[0], str):
        scatter = ax1.scatter(points[:,0], points[:,1], points[:,2], 
                             c=labels, cmap='tab10', s=0.5)
        plt.colorbar(scatter, ax=ax1, label='Class')
    else:
        ax1.scatter(points[:,0], points[:,1], points[:,2], 
                   c=points[:,2], cmap='viridis', s=0.5)
    
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_zlabel('Z (m)')
    ax1.set_title(f'{title}\n3D View ({len(points):,} points)')
    
    # Top-down view (XY)
    ax2 = fig.add_subplot(132)
    
    if labels is not None and not isinstance(labels[0], str):
        scatter = ax2.scatter(points[:,0], points[:,1], c=labels, cmap='tab10', s=0.5)
    else:
        ax2.scatter(points[:,0], points[:,1], c=points[:,2], cmap='viridis', s=0.5)
    
    ax2.set_xlabel('X (m)')
    ax2.set_ylabel('Y (m)')
    ax2.set_title('Top-Down View (XY)')
    ax2.set_aspect('equal')
    
    # Side view (XZ)
    ax3 = fig.add_subplot(133)
    
    if labels is not None and not isinstance(labels[0], str):
        scatter = ax3.scatter(points[:,0], points[:,2], c=labels, cmap='tab10', s=0.5)
    else:
        ax3.scatter(points[:,0], points[:,2], c=points[:,2], cmap='viridis', s=0.5)
    
    ax3.set_xlabel('X (m)')
    ax3.set_ylabel('Z (m)')
    ax3.set_title('Side View (XZ)')
    
    plt.tight_layout()
    plt.show()

# ============================================================
# FUNCTION: VISUALIZE WITH OPEN3D (INTERACTIVE)
# ============================================================

def visualize_open3d(points, labels=None):
    """Interactive 3D visualization with Open3D"""
    try:
        import open3d as o3d
        
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        
        if labels is not None and not isinstance(labels[0], str):
            # Color by label
            colors = plt.cm.tab10(labels % 10)[:, :3]
            pcd.colors = o3d.utility.Vector3dVector(colors)
        else:
            # Color by height
            z_normalized = (points[:,2] - points[:,2].min()) / (points[:,2].max() - points[:,2].min() + 1e-6)
            colors = plt.cm.viridis(z_normalized)[:, :3]
            pcd.colors = o3d.utility.Vector3dVector(colors)
        
        print("\n🎮 Open3D Controls:")
        print("   - Left mouse: Rotate")
        print("   - Middle mouse: Pan")
        print("   - Scroll: Zoom")
        print("   - Q: Quit")
        
        o3d.visualization.draw_geometries([pcd], window_name="Point Cloud Viewer")
        
    except ImportError:
        print("⚠️  Open3D not installed. Using matplotlib instead.")
        visualize_points(points, labels)

# ============================================================
# MAIN: FIND AND LOAD FILES
# ============================================================

print("=" * 60)
print("       POINT CLOUD FILE VIEWER")
print("=" * 60)

print(f"\n📁 Scanning folder: {output_folder}\n")

# Find all relevant files
las_files = []
hdf_files = []
csv_files = []

if os.path.exists(output_folder):
    for f in os.listdir(output_folder):
        filepath = os.path.join(output_folder, f)
        if f.endswith('.las'):
            las_files.append(filepath)
        elif f.endswith('.hdf') or f.endswith('.h5') or f.endswith('.hdf5'):
            hdf_files.append(filepath)
        elif f.endswith('.csv'):
            csv_files.append(filepath)

print(f"📊 Found files:")
print(f"   LAS files: {len(las_files)}")
print(f"   HDF5 files: {len(hdf_files)}")
print(f"   CSV files: {len(csv_files)}")

# ============================================================
# LOAD AND COMBINE ALL DATA
# ============================================================

all_points = []
all_labels = []

# Read LAS files
print("\n" + "=" * 60)
print("       READING LAS FILES")
print("=" * 60)

for filepath in las_files[:5]:  # Limit to first 5
    points, labels = read_las_file(filepath)
    if points is not None:
        all_points.append(points)
        if labels is not None:
            all_labels.append(labels)

# Read HDF5 files
print("\n" + "=" * 60)
print("       READING HDF5 FILES")
print("=" * 60)

for filepath in hdf_files[:5]:  # Limit to first 5
    points, labels = read_hdf5_file(filepath)
    if points is not None:
        all_points.append(points)
        if labels is not None:
            all_labels.append(labels)

# Read CSV files
print("\n" + "=" * 60)
print("       READING CSV FILES")
print("=" * 60)

for filepath in csv_files[:5]:  # Limit to first 5
    points, labels = read_csv_file(filepath)
    if points is not None:
        all_points.append(points)
        if labels is not None:
            all_labels.append(labels)

# ============================================================
# COMBINE AND VISUALIZE
# ============================================================

if all_points:
    combined_points = np.vstack(all_points)
    combined_labels = np.concatenate(all_labels) if all_labels and len(all_labels) == len(all_points) else None
    
    print("\n" + "=" * 60)
    print("       COMBINED DATA")
    print("=" * 60)
    print(f"\n📊 Total points: {len(combined_points):,}")
    print(f"   X range: {combined_points[:,0].min():.2f} to {combined_points[:,0].max():.2f}")
    print(f"   Y range: {combined_points[:,1].min():.2f} to {combined_points[:,1].max():.2f}")
    print(f"   Z range: {combined_points[:,2].min():.2f} to {combined_points[:,2].max():.2f}")
    
    if combined_labels is not None:
        unique, counts = np.unique(combined_labels, return_counts=True)
        print(f"\n📊 Label distribution:")
        for u, c in zip(unique, counts):
            print(f"   Class {u}: {c:,} points ({c/len(combined_labels)*100:.1f}%)")
    
    # Visualize
    print("\n🎨 Visualizing...")
    
    # Try Open3D first, fallback to matplotlib
    try:
        visualize_open3d(combined_points, combined_labels)
    except:
        visualize_points(combined_points, combined_labels, "Combined Point Cloud")
else:
    print("\n❌ No point cloud data found!")