import os
import re
import uuid
import shutil
import subprocess

from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets

from .models import Category, Tool
from .serializers import ToolSerializer


# =====================================================
# API VIEWSET
# =====================================================

class ToolViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tool.objects.filter(visible=True).order_by("name")
    serializer_class = ToolSerializer


# =====================================================
# FRONTEND PAGES
# =====================================================

def home(request):
    categories = Category.objects.all().order_by("name")
    return render(request, "launcher/home.html", {
        "categories": categories
    })


def category_page(request, slug):
    category = get_object_or_404(Category, slug=slug)
    tools = category.tools.filter(visible=True).order_by("name")
    return render(request, "launcher/category.html", {
        "category": category,
        "tools": tools
    })


def tool_page(request, slug):
    """
    Entry page for any tool.
    Handles WEB redirects internally without breaking UI.
    """
    tool = get_object_or_404(Tool, slug=slug)

    mode = request.GET.get("mode")
    from_tool = request.GET.get("from")

    # -----------------------------
    # VERILATOR WEB WORKSPACE
    # -----------------------------
    if mode == "web" and tool.slug == "verilator":
        return render(request, "launcher/verilator.html", {
            "tool": tool,
            "envs": tool.envs.all(),
            "webmode": True,
            "launched_from": from_tool
        })

    # -----------------------------
    # KLAYOUT WEB WORKSPACE
    # -----------------------------
    if mode == "web" and tool.slug == "klayout":
        return render(request, "launcher/klayout_workspace.html", {
            "tool": tool,
            "webmode": True,
            "launched_from": from_tool
        })

    # -----------------------------
    # DEFAULT TOOL PAGE
    # -----------------------------
    return render(request, "launcher/tool.html", {
        "tool": tool,
        "envs": tool.envs.all()
    })


# =====================================================
# FILE SERVER (UPLOADS)
# =====================================================

def serve_upload(request, path):
    base = os.path.join(settings.BASE_DIR, "uploads")
    full = os.path.abspath(os.path.join(base, path))

    if not full.startswith(os.path.abspath(base)):
        return HttpResponse("Forbidden", status=403)

    if not os.path.exists(full):
        return HttpResponse("Not Found", status=404)

    return FileResponse(open(full, "rb"))


# =====================================================
# VERILATOR HELPERS
# =====================================================

def fix_verilog_module_name(file_path, new_name):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    module_pattern = re.compile(r"(\bmodule\s+)([A-Za-z_][A-Za-z0-9_]*)")
    match = module_pattern.search(text)

    if not match:
        return False

    text = module_pattern.sub(r"\1" + new_name, text, 1)

    if "verilator lint_off DECLFILENAME" not in text:
        text = (
            "/* verilator lint_off DECLFILENAME */\n"
            + text +
            "\n/* verilator lint_on DECLFILENAME */\n"
        )

    if not text.endswith("\n"):
        text += "\n"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    return True


def patch_sim_main(path, module_name):
    with open(path, "r") as f:
        txt = f.read()

    txt = txt.replace("VMODULE_NAME", f"V{module_name}")

    with open(path, "w") as f:
        f.write(txt)


# =====================================================
# VERILATOR COMPILE + RUN (WSL)
# =====================================================

@csrf_exempt
def launch_tool(request):
    if request.method != "POST":
        return Response({"ok": False, "error": "POST required"}, status=400)

    tool_id = request.data.get("tool_id")
    upload = request.data.get("upload")

    tool = get_object_or_404(Tool, id=tool_id)

    BASE = str(settings.BASE_DIR)
    win_uploads = os.path.join(BASE, "uploads")
    wsl_uploads = "/mnt/c" + BASE[2:].replace("\\", "/") + "/uploads"

    win_source = os.path.join(win_uploads, upload)
    if not os.path.exists(win_source):
        return Response({"ok": False, "error": "Uploaded file missing"}, status=404)

    folder = uuid.uuid4().hex
    win_workdir = os.path.join(win_uploads, folder)
    wsl_workdir = f"{wsl_uploads}/{folder}"
    os.makedirs(win_workdir, exist_ok=True)

    shutil.copy(win_source, win_workdir)

    module_name = f"top_{os.path.splitext(upload)[0]}"
    fix_verilog_module_name(os.path.join(win_workdir, upload), module_name)

    sim_src = os.path.join(BASE, "launcher", "verilator_assets", "sim_main.cpp")
    sim_dst = os.path.join(win_workdir, "sim_main.cpp")
    shutil.copy(sim_src, sim_dst)
    patch_sim_main(sim_dst, module_name)

    compile_cmd = (
        f"cd {wsl_workdir} && "
        f"verilator -Wall --Wno-EOFNEWLINE --trace --cc {upload} "
        f"--top-module {module_name} "
        f"--exe sim_main.cpp && "
        f"make -C obj_dir -f V{module_name}.mk V{module_name}"
    )

    run_cmd = f"cd {wsl_workdir} && ./obj_dir/V{module_name}"

    def run_bash(cmd):
        p = subprocess.Popen(
            ["wsl", "bash", "-lc", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = p.communicate()
        return out.decode(), err.decode()

    compile_out, compile_err = run_bash(compile_cmd)
    sim_out, sim_err = run_bash(run_cmd)

    vcd = None
    for f in os.listdir(win_workdir):
        if f.endswith(".vcd"):
            vcd = f"/uploads/{folder}/{f}"

    return Response({
        "ok": True,
        "stdout": compile_out + sim_out,
        "stderr": compile_err + sim_err,
        "vcd": vcd
    })


# =====================================================
# UPLOAD WRAPPER (VERILATOR)
# =====================================================

@api_view(["POST"])
def run_tool(request, slug):
    tool = get_object_or_404(Tool, slug=slug)
    upload = request.FILES.get("file")

    uploads_dir = os.path.join(settings.BASE_DIR, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    filename = None
    if upload:
        filename = f"{uuid.uuid4().hex}_{upload.name}"
        with open(os.path.join(uploads_dir, filename), "wb") as f:
            for chunk in upload.chunks():
                f.write(chunk)

    dummy = type("Dummy", (), {})()
    dummy.method = "POST"
    dummy.data = {"tool_id": tool.id, "upload": filename}

    resp = launch_tool(dummy)
    return JsonResponse(resp.data)


# =====================================================
# DESKTOP LAUNCH (WSL SAFE)
# =====================================================
"""
@csrf_exempt
def launch_desktop(request, slug):
    if request.method != "POST":
        return JsonResponse(
            {"ok": False, "error": "POST required"},
            status=400
        )

    tool = get_object_or_404(Tool, slug=slug)

    # Prefer Linux executable (WSL GUI tools)
    exe = tool.linux_executable_path or tool.windows_executable_path

    if not exe:
        return JsonResponse(
            {"ok": False, "error": "Executable path not configured"},
            status=400
        )

    # --------------------------------------------------
    # Tool-specific launch flags
    # --------------------------------------------------
    if tool.slug == "klayout":
        # Start KLayout in EDITOR MODE
        cmd = f"{exe} -e"
    else:
        # Default launch
        cmd = exe

    try:
        subprocess.Popen(
            ["wsl", "bash", "-lc", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        return JsonResponse({
            "ok": True,
            "message": f"{tool.name} launched successfully"
        })

    except Exception as e:
        return JsonResponse(
            {"ok": False, "error": str(e)},
            status=500
        )
"""


# =====================================================
# WEB LAUNCH (PER TOOL)
# =====================================================
"""
@csrf_exempt
def launch_web(request, slug):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=400)

    if slug == "verilator":
        return JsonResponse({
            "ok": True,
            "url": "/tool/verilator/?mode=web&from=launcher"
        })

    if slug == "klayout":
        return JsonResponse({
            "ok": True,
            "url": "/tool/klayout/?mode=web&from=launcher"
        })

    return JsonResponse({
        "ok": False,
        "error": "This tool has no Web Mode"
    })
"""

@csrf_exempt
def klayout_run(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=400)

    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"ok": False, "error": "No GDS file uploaded"}, status=400)

    base_dir = settings.BASE_DIR
    upload_dir = os.path.join(base_dir, "uploads", "klayout")
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}_{upload.name}"
    full_path = os.path.join(upload_dir, filename)

    with open(full_path, "wb") as f:
        for chunk in upload.chunks():
            f.write(chunk)

    wsl_path = "/mnt/c" + full_path.replace("C:", "").replace("\\", "/")

    subprocess.Popen(
        ["wsl", "bash", "-lc", f"klayout {wsl_path}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return JsonResponse({
        "ok": True,
        "message": "KLayout opened with GDS file"
    })


@csrf_exempt
def launch_web(request, slug):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=400)

    # Verilator → Web simulation workspace
    if slug == "verilator":
        return JsonResponse({
            "ok": True,
            "url": "/tool/verilator/?mode=web&from=launcher"
        })

    # KLayout → Web workspace (upload + desktop launch)
    if slug == "klayout":
        return JsonResponse({
            "ok": True,
            "url": "/tool/klayout/?mode=web&from=launcher"
        })

    return JsonResponse({
        "ok": False,
        "error": "This tool does not support Web Mode"
    }, status=400)

"""

@csrf_exempt
def klayout_run(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=400)

    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"ok": False, "error": "No GDS uploaded"}, status=400)

    base = settings.BASE_DIR
    upload_dir = os.path.join(base, "uploads", "klayout")
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}_{upload.name}"
    full_path = os.path.join(upload_dir, filename)

    with open(full_path, "wb") as f:
        for chunk in upload.chunks():
            f.write(chunk)

    return JsonResponse({
        "ok": True,
        "message": "GDS uploaded successfully",
        "path": full_path
    })
"""

@csrf_exempt
def launch_web(request, slug):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=400)

    if slug == "klayout":
        return JsonResponse({
            "ok": True,
            "url": "/tool/klayout/?mode=web"
        })

    if slug == "verilator":
        return JsonResponse({
            "ok": True,
            "url": "/tool/verilator/?mode=web"
        })

    return JsonResponse({"ok": False, "error": "No web mode"}, status=400)

"""
@csrf_exempt
def launch_desktop(request, slug):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=400)

    tool = get_object_or_404(Tool, slug=slug)

    exe = tool.linux_executable_path
    gds = request.POST.get("gds")

    if not exe:
        return JsonResponse({"ok": False, "error": "Linux executable not set"}, status=400)

    if gds:
        wsl_path = "/mnt/c" + gds.replace("C:", "").replace("\\", "/")
        cmd = f"{exe} {wsl_path}"
    else:
        cmd = exe

    subprocess.Popen(
        ["wsl", "bash", "-lc", cmd],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return JsonResponse({"ok": True, "message": "KLayout launched"})

"""

@csrf_exempt
def launch_desktop(request, slug):
    if request.method != "POST":
        return JsonResponse(
            {"ok": False, "error": "POST required"},
            status=400
        )

    tool = get_object_or_404(Tool, slug=slug)

    # Prefer Linux executable (WSL GUI tools)
    exe = tool.linux_executable_path or tool.windows_executable_path

    if not exe:
        return JsonResponse(
            {"ok": False, "error": "Executable path not configured"},
            status=400
        )

    # --------------------------------------------------
    # Tool-specific launch flags
    # --------------------------------------------------
    if tool.slug == "klayout":
        # Start KLayout in EDITOR MODE
        cmd = f"{exe} -e"
    else:
        # Default launch
        cmd = exe

    try:
        subprocess.Popen(
            ["wsl", "bash", "-lc", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        return JsonResponse({
            "ok": True,
            "message": f"{tool.name} launched successfully"
        })

    except Exception as e:
        return JsonResponse(
            {"ok": False, "error": str(e)},
            status=500
        )
