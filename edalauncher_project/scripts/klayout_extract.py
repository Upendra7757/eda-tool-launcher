import pya
import json
import sys

# --------------------------------------------------
# Read -rd parameters (key=value)
# --------------------------------------------------
params = {}
for arg in sys.argv:
    if "=" in arg:
        k, v = arg.split("=", 1)
        params[k.strip()] = v.strip()

gds_path = params.get("gds")
png_path = params.get("png")
meta_path = params.get("meta")

if not gds_path or not png_path or not meta_path:
    raise RuntimeError("Missing required -rd parameters")

# --------------------------------------------------
# Load GDS
# --------------------------------------------------
layout = pya.Layout()
layout.read(gds_path)

# --------------------------------------------------
# Generate PNG
# --------------------------------------------------
view = pya.LayoutView()
view.load_layout(gds_path, 0)
view.max_hier()
view.add_missing_layers()
view.save_image(png_path, 1200, 1200)

# --------------------------------------------------
# Generate Metadata
# --------------------------------------------------
metadata = {
    "cell_count": layout.cells(),
    "layers": [
        {
            "layer": li.layer,
            "datatype": li.datatype,
            "name": li.name
        }
        for li in layout.layer_infos()
    ]
}

with open(meta_path, "w") as f:
    json.dump(metadata, f, indent=2)

print("PNG + metadata generated successfully")
