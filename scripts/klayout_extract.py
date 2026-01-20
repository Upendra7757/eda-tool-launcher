import os
import json
import pya
import traceback

print("DEBUG: Starting KLayout")

gds_path  = os.environ.get("KLAYOUT_GDS")
png_path  = os.environ.get("KLAYOUT_PNG")
meta_path = os.environ.get("KLAYOUT_META")

if not gds_path:
    raise RuntimeError("KLAYOUT_GDS not set")

try:
    # -------------------------
    # Load layout
    # -------------------------
    layout = pya.Layout()
    layout.read(gds_path)

    top = layout.top_cell()
    if not top:
        raise RuntimeError("No top cell found")

    # -------------------------
    # Render PNG
    # -------------------------
    if png_path:
        view = pya.LayoutView()
        view.load_layout(gds_path, 0)
        view.max_hier()
        view.save_image(png_path, 2000, 2000)

    # -------------------------
    # Write metadata
    # -------------------------
    if meta_path:
        meta = {
            "cells": layout.cells(),
            "layers": layout.layers(),
            "top_cell": top.name
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    print("KLayout extraction completed successfully")

except Exception as e:
    print("ERROR:", str(e))
    traceback.print_exc()

