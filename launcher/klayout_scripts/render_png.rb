layout = RBA::Layout.new
layout.read(ARGV[0])

view = RBA::LayoutView.new
view.load_layout(layout)
view.max_hier()

img = view.get_image(1200, 1200)
img.save("preview.png")
