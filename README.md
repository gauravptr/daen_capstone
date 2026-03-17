# DAEN Capstone: Blender Sonar Point Cloud Generation

This repository contains the Blender scenes, scanning utilities, and exported point cloud datasets used for the DAEN 460 capstone workflow.

## Project Overview

The project simulates underwater scanning in Blender (with blAInder tooling), then exports point cloud outputs in common formats for downstream analysis and visualization.

The workflow is:

1. Build or edit a scene in Blender.
2. Validate that objects are scannable.
3. Generate and preview a scan path.
4. Run batch scanning across path positions.
5. Merge scan outputs into combined point clouds.

## Repository Structure

`scenes/`
- Contains the source Blender scene files used to generate synthetic scan data.
- Example: `test1.blend`

`output/`
- Contains generated point cloud and scan outputs from Blender scanning runs.
- Includes formats such as `.ply`, `.xyz`, `.las`, `.csv`, and `.hdf5`.
- Key files include:
	- `combined_full_scan.ply`
	- `combined_full_scan.xyz`
	- `underwater_scene_scan.ply`
	- `underwater_scene_scan.xyz`

`useful_scripts/`
- Contains Blender Python scripts (stored as `.txt` files) that support scan setup and post-processing.
- Script summary:
	- `scan_readiness_check.txt`: Checks scene objects for scan-readiness (mesh type, visibility, material validity).
	- `50x50_boat_path.txt`: Generates a boat/camera scan path and scan positions across a 50 m x 50 m area.
	- `full_batch_scan.txt`: Executes scanning at all generated path positions.
	- `combine_scans.txt`: Combines all detected scan points into consolidated `.ply` and `.xyz` files.

`documents and stuf/`
- Supporting project planning and course documentation.

`test.ipynb`
- Notebook for quick point cloud checks and visualization (Open3D + Matplotlib).

## How to Use the Blender Scripts

1. Open a scene from `scenes/` in Blender.
2. Open the Scripting workspace.
3. Load and run scripts from `useful_scripts/` in this order:
	 1. `scan_readiness_check.txt`
	 2. `50x50_boat_path.txt`
	 3. `full_batch_scan.txt`
	 4. `combine_scans.txt`
4. Check generated outputs in `output/`.

Note: These scripts are Blender Python scripts and are meant to run inside Blender's Python environment (`bpy`).

## Data Notes

- `output/` may contain large files.
- Blender source files in `scenes/` can exceed standard GitHub size limits.
- Very large assets should be managed with Git LFS if they need to be versioned.

## Visualization

You can visualize point clouds using:

- Blender
- Open3D (Python)
- Matplotlib (for quick 3D scatter previews)

The included notebook `test.ipynb` provides a starting point for loading and plotting `.ply` and `.xyz` data.

## License

This repository includes a `LICENSE` file. See `LICENSE` for terms.