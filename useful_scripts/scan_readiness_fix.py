import bpy

"""
OBJECT SCANNER READINESS FIX
============================
Fixes common reasons objects are skipped by range scanner style pipelines:
- Object hidden in viewport/render or hidden in the active view layer
- Collection disabled/excluded for the active view layer
- Mesh has no material slots or no valid material
- Empty material slots
- TEX_IMAGE nodes that reference invalid/empty images

Run this script in Blender's Scripting workspace.
"""

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

IGNORE_PREFIXES = [
	"real_values",
	"noise_values",
	"ScanPath",
	"PathMarker",
	"Camera",
	"Light",
]

AUTO_UNHIDE_OBJECTS = True
AUTO_UNHIDE_COLLECTIONS = True
AUTO_FIX_MATERIALS = True
AUTO_FIX_TEXTURE_NODES = True


def should_ignore_object(obj):
	if obj.type in {"CAMERA", "LIGHT", "EMPTY", "ARMATURE"}:
		return True

	for prefix in IGNORE_PREFIXES:
		if obj.name.startswith(prefix):
			return True

	return False


def ensure_fallback_material():
	mat_name = "ScanReady_DefaultMaterial"
	mat = bpy.data.materials.get(mat_name)
	if mat is None:
		mat = bpy.data.materials.new(name=mat_name)
		mat.use_nodes = True

		bsdf = mat.node_tree.nodes.get("Principled BSDF")
		if bsdf is not None:
			bsdf.inputs["Base Color"].default_value = (0.7, 0.7, 0.7, 1.0)
			bsdf.inputs["Metallic"].default_value = 0.0
			bsdf.inputs["Roughness"].default_value = 0.5

	return mat


def ensure_fallback_image():
	image_name = "ScanReady_Fallback_1x1"
	image = bpy.data.images.get(image_name)
	if image is None:
		image = bpy.data.images.new(name=image_name, width=1, height=1, alpha=True)
		image.generated_color = (0.5, 0.5, 0.5, 1.0)
	return image


def walk_layer_collections(layer_collection):
	yield layer_collection
	for child in layer_collection.children:
		yield from walk_layer_collections(child)


def unhide_collections_active_view_layer(report):
	view_layer = bpy.context.view_layer
	changed = 0

	for layer_col in walk_layer_collections(view_layer.layer_collection):
		if layer_col.exclude:
			layer_col.exclude = False
			changed += 1
		if layer_col.hide_viewport:
			layer_col.hide_viewport = False
			changed += 1

	report["collections_unhidden"] = changed


def fix_object_visibility(obj, report):
	if not AUTO_UNHIDE_OBJECTS:
		return

	if obj.hide_viewport:
		obj.hide_viewport = False
		report["object_unhide_viewport"] += 1

	if obj.hide_render:
		obj.hide_render = False
		report["object_unhide_render"] += 1

	# hidden state in active view layer
	if obj.hide_get():
		obj.hide_set(False)
		report["object_unhide_layer"] += 1


def fix_material_slots(obj, fallback_mat, report):
	if obj.type != "MESH":
		return

	if not AUTO_FIX_MATERIALS:
		return

	# Ensure at least one slot exists.
	if len(obj.material_slots) == 0:
		obj.data.materials.append(fallback_mat)
		report["materials_added"] += 1
		return

	# Fill empty slots and ensure at least one valid material is present.
	has_valid_material = False
	for slot in obj.material_slots:
		if slot.material is None:
			slot.material = fallback_mat
			report["empty_slots_filled"] += 1
		else:
			has_valid_material = True

	if not has_valid_material:
		obj.material_slots[0].material = fallback_mat
		report["materials_added"] += 1


def fix_invalid_texture_nodes(report):
	if not AUTO_FIX_TEXTURE_NODES:
		return

	fallback_image = ensure_fallback_image()

	for mat in bpy.data.materials:
		if mat is None or mat.node_tree is None:
			continue

		for node in mat.node_tree.nodes:
			if node.type != "TEX_IMAGE":
				continue

			image = node.image
			invalid = (
				image is None
				or getattr(image, "pixels", None) is None
				or len(image.pixels) == 0
			)

			if invalid:
				node.image = fallback_image
				report["invalid_tex_nodes_fixed"] += 1


def main():
	print("=" * 68)
	print("OBJECT SCANNER READINESS FIX")
	print("=" * 68)

	report = {
		"objects_checked": 0,
		"objects_ignored": 0,
		"non_mesh_seen": 0,
		"object_unhide_viewport": 0,
		"object_unhide_render": 0,
		"object_unhide_layer": 0,
		"collections_unhidden": 0,
		"materials_added": 0,
		"empty_slots_filled": 0,
		"invalid_tex_nodes_fixed": 0,
	}

	if AUTO_UNHIDE_COLLECTIONS:
		unhide_collections_active_view_layer(report)

	fallback_mat = ensure_fallback_material()

	for obj in bpy.data.objects:
		if should_ignore_object(obj):
			report["objects_ignored"] += 1
			continue

		report["objects_checked"] += 1

		if obj.type != "MESH":
			report["non_mesh_seen"] += 1

		fix_object_visibility(obj, report)
		fix_material_slots(obj, fallback_mat, report)

	fix_invalid_texture_nodes(report)

	print("\nFix summary:")
	print(f"  Objects checked: {report['objects_checked']}")
	print(f"  Objects ignored: {report['objects_ignored']}")
	print(f"  Non-mesh objects seen: {report['non_mesh_seen']}")
	print(f"  Collections unhidden/excluded fixed: {report['collections_unhidden']}")
	print(f"  Objects unhidden in viewport: {report['object_unhide_viewport']}")
	print(f"  Objects unhidden in render: {report['object_unhide_render']}")
	print(f"  Objects unhidden in view layer: {report['object_unhide_layer']}")
	print(f"  Default materials added: {report['materials_added']}")
	print(f"  Empty material slots filled: {report['empty_slots_filled']}")
	print(f"  Invalid texture nodes fixed: {report['invalid_tex_nodes_fixed']}")

	print("\nDone. Run scan_readiness_check.py again to verify readiness.")


if __name__ == "__main__":
	main()
