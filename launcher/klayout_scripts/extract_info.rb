import sys
import json
import os
import klayout.db as db
import klayout.lay as lay

gds_path = sys.argv[1]
out_dir = sys.argv[2]

layout = db.Layout()
layout.read(gds_path)

top = layout.top_cell()

metadata = {
    "cell_count": layout.cells(),
    "dbu": layout.dbu,
    "bbox": {
        "left": top.bbox().left,
        "right": top.bbox().right,
        "top": top.bbox().top,
        "bottom": top.bbox().bottom,
    },
    "layers": [
        f"{li.layer}/{li.datatype}" for li in layout.layer_infos()
    ]
}

# Write metadata
with open(os.path.join(out_dir, "metadata.json"), "w") as f:
    json.dump(metadata, f, indent=2)

# Render PNG
view = lay.LayoutView()
view.load_layout(gds_path)
view.max_hier()

png_path = os.path.join(out_dir, "preview.png")
view.save_image(png_path, 1200, 900)

print("OK")
