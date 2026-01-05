"""
from django.urls import path
from . import views

urlpatterns = [

    path("", views.home, name="launcher-home"),

    path("category/<slug:slug>/", views.category_page, name="launcher-category"),

    path("tool/<slug:slug>/", views.tool_page, name="launcher-tool"),

    path("tool/<slug:slug>/run/", views.run_tool, name="launcher-run-tool"),

    path("launch-desktop/<slug:slug>/", views.launch_desktop, name="launcher-launch-desktop"),

    path("launch-web/<slug:slug>/", views.launch_web, name="launcher-launch-web"),

    path("klayout-run/", views.klayout_run, name="klayout-run"),

    path("uploads/<path:path>/", views.serve_upload, name="launcher-uploads"),


]
"""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="launcher-home"),
    path("category/<slug:slug>/", views.category_page, name="launcher-category"),
    path("tool/<slug:slug>/", views.tool_page, name="launcher-tool"),

    # Verilator
    path("tool/<slug:slug>/run/", views.run_tool, name="launcher-run-tool"),

    # KLayout Web Upload
    path("klayout-run/", views.klayout_run, name="klayout-run"),

    # Launchers
    path("launch-desktop/<slug:slug>/", views.launch_desktop, name="launcher-launch-desktop"),
    path("launch-web/<slug:slug>/", views.launch_web, name="launcher-launch-web"),

    # Uploaded files
    path("uploads/<path:path>/", views.serve_upload, name="launcher-uploads"),

    #path("open-cli/<str:workdir>/", views.open_cli, name="open-cli"),
    path("klayout-run/", views.klayout_run, name="klayout-run"),

    path("logs/", views.logs_page, name="launcher-logs"),

    path("logs/", views.logs_home,name="logs-home"),

    path("logs/<str:scope>/", views.logs_by_scope, name="logs-by-scope"),


    path("logs/<slug:scope>/",views.logs_by_scope,name="logs-by-scope"),

    path("logs/run/<int:run_id>/",views.view_run_logs,name="view-run-logs"),

    
    #path("logs/list/<slug:tool_slug>/",views.logs_list,name="logs-list"),

    path("logs/run/<int:run_id>/download/",views.download_run_logs,name="download-run-logs"),

]


