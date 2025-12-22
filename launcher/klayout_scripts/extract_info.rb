layout = RBA::Layout.new
layout.read(ARGV[0])

bbox = layout.bbox
cells = layout.cells.size

layers = []
layout.layer_indices.each do |i|
  li = layout.get_info(i)
  layers << "#{li.layer}/#{li.datatype}"
end

File.write("info.json", {
  bbox: {
    x1: bbox.left,
    y1: bbox.bottom,
    x2: bbox.right,
    y2: bbox.top
  },
  cells: cells,
  layers: layers
}.to_json)
