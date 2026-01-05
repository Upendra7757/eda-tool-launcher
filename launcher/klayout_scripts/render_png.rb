import pya, sys

app = pya.Application.instance()
mw = app.main_window()
mw.load_layout(sys.argv[1], 0)
mw.save_image(sys.argv[2], 800, 800)
