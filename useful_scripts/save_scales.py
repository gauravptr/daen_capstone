import bpy

print("=" * 60)
print("   APPLYING ALL OBJECT SCALES")
print("=" * 60)

# Don't apply to these
PRESERVE = ['Plane', 'Camera', 'Light', 'TextureField']

applied = 0
skipped = 0

for obj in bpy.data.objects:
    # Skip preserved objects
    if any(preserve in obj.name for preserve in PRESERVE):
        print(f"  ⏭️  Skipped: {obj.name}")
        skipped += 1
        continue
    
    # Skip non-mesh objects
    if obj.type != 'MESH':
        skipped += 1
        continue
    
    # Skip scan results
    if any(prefix in obj.name for prefix in ['noise_values', 'real_values', 'PathMarker', 'ScanPath']):
        skipped += 1
        continue
    
    # Store original scale for logging
    original_scale = obj.scale.copy()
    
    # Select and apply scale
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    try:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        print(f"  ✅ Applied scale to: {obj.name} (was {original_scale.x:.3f})")
        applied += 1
    except Exception as e:
        print(f"  ⚠️  Could not apply scale to {obj.name}: {e}")

print(f"\n{'='*60}")
print(f"   COMPLETE!")
print(f"{'='*60}")
print(f"  ✅ Applied: {applied}")
print(f"  ⏭️  Skipped: {skipped}")
print(f"\n💾 Now SAVE your file!")