import pya

# -------------------------------
# Create a new layout
# -------------------------------
layout = pya.Layout()
layout.dbu = 0.001  # 1 nm database unit

# -------------------------------
# Create top cell
# -------------------------------
top = layout.create_cell("TOP")

# -------------------------------
# Create a layer (Layer 1 / Datatype 0)
# -------------------------------
layer_index = layout.layer(1, 0)

# -------------------------------
# Draw geometry (example rectangle)
# Units are in DBU (nanometers here)
# -------------------------------
width_um = 10
height_um = 5

box = pya.Box(
    0,
    0,
    int(width_um * 1000),
    int(height_um * 1000),
)

top.shapes(layer_index).insert(box)

# -------------------------------
# Save the GDS
# -------------------------------
output_gds = "generated_design.gds"
layout.write(output_gds)

print(f"GDS created successfully: {output_gds}")
