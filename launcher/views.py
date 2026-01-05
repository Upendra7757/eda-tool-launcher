import os
import re
import uuid
import shutil
import subprocess

from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from .services import execute_tool_run
from .models import ToolRun, Tool
from django.utils import timezone

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets
from launcher.models import ToolRun

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

"""
def category_page(request, slug):
    category = get_object_or_404(Category, slug=slug)
    tools = category.tools.filter(visible=True).order_by("name")
    return render(request, "launcher/category.html", {
        "category": category,
        "tools": tools
    })
"""

def category_page(request, slug):
    category = get_object_or_404(Category, slug=slug)
    tools = category.tools.filter(visible=True).order_by("name")

    return render(request, "launcher/category.html", {
        "category": category,
        "tools": tools,
        "active_category": category.slug,   # ⭐ KEY LINE
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
"""
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
"""


# =====================================================
# UPLOAD WRAPPER (VERILATOR)
# =====================================================
"""
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
"""


# =====================================================
# DESKTOP LAUNCH (WSL SAFE)
# =====================================================


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
"""

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
from django.utils import timezone
from .models import ToolRun

@csrf_exempt
def launch_tool(request):

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=400)

    tool = get_object_or_404(Tool, slug="verilator")

    try:
        # Run actual simulation here
        stdout = "simulation output"
        stderr = ""

        run = execute_tool_run(
            tool=tool,
            user=request.user if request.user.is_authenticated else None,
            input_file=request.FILES.get("file").name if request.FILES else None,
            stdout=stdout,
            stderr=stderr,
            status="success"
        )

        return JsonResponse({
            "ok": True,
            "run_id": run.id,
            "stdout": stdout,
            "stderr": stderr
        })

    except Exception as e:
        run = execute_tool_run(
            tool=tool,
            user=request.user if request.user.is_authenticated else None,
            status="failed",
            stderr=str(e)
        )
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

"""
from .models import ToolRun

"""
@csrf_exempt
def klayout_run(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=400)

    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"ok": False, "error": "No GDS uploaded"}, status=400)

    tool = get_object_or_404(Tool, slug="klayout")

    run = ToolRun.objects.create(
        tool=tool,
        user=request.user if request.user.is_authenticated else None,
        input_file=upload.name,
        status="running"
    )

    try:
        base = settings.BASE_DIR
        upload_dir = os.path.join(base, "uploads", "klayout")
        os.makedirs(upload_dir, exist_ok=True)

        filename = f"{uuid.uuid4().hex}_{upload.name}"
        full_path = os.path.join(upload_dir, filename)

        with open(full_path, "wb") as f:
            for chunk in upload.chunks():
                f.write(chunk)

        run.status = "success"
        run.completed_at = timezone.now()
        run.save()

        return JsonResponse({
            "ok": True,
            "run_id": run.id,
            "message": "GDS uploaded successfully",
            "path": full_path
        })

    except Exception as e:
        run.status = "failed"
        run.stderr = str(e)
        run.completed_at = timezone.now()
        run.save()

        return JsonResponse({"ok": False, "error": str(e)}, status=500)
"""
"""
@csrf_exempt
def klayout_run(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=400)

    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"ok": False, "error": "No GDS uploaded"}, status=400)

    upload_dir = os.path.join(settings.BASE_DIR, "uploads", "klayout")
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}_{upload.name}"
    full_path = os.path.join(upload_dir, filename)

    with open(full_path, "wb") as f:
        for chunk in upload.chunks():
            f.write(chunk)

    # Convert Windows path → WSL path
    wsl_path = "/mnt/c" + full_path.replace("C:", "").replace("\\", "/")

    # IMPORTANT: -e = Editor mode
    subprocess.Popen(
        ["wsl", "bash", "-lc", f"klayout -e '{wsl_path}'"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return JsonResponse({
        "ok": True,
        "message": "GDS opened in KLayout editor",
    })
"""
def view_run_logs(request, run_id):
    run = get_object_or_404(ToolRun, id=run_id)

    return render(
        request,
        "launcher/run_detail.html",   # ✅ matches your folder
        {
            "run": run
        }
    )

from django.utils import timezone
from .models import ToolRun, LayoutMetadata

@csrf_exempt
def klayout_run(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=400)

    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"ok": False, "error": "No GDS uploaded"}, status=400)

    run_dir = os.path.join(settings.BASE_DIR, "runs", uuid.uuid4().hex)
    os.makedirs(run_dir, exist_ok=True)

    gds_path = os.path.join(run_dir, upload.name)
    with open(gds_path, "wb") as f:
        for chunk in upload.chunks():
            f.write(chunk)

    run = ToolRun.objects.create(
        tool=Tool.objects.get(slug="klayout"),
        user=request.user if request.user.is_authenticated else None,
        input_file=upload.name,
        run_dir=run_dir,
        status="running",
    )

    wsl_gds = "/mnt/c" + gds_path.replace("C:", "").replace("\\", "/")
    wsl_run = "/mnt/c" + run_dir.replace("C:", "").replace("\\", "/")

    subprocess.Popen([
        "wsl", "bash", "-lc",
        f"klayout -e '{wsl_gds}' && "
        f"klayout -b -r scripts/klayout_extract.py '{wsl_gds}' '{wsl_run}'"
    ])

    return JsonResponse({
        "ok": True,
        "run_id": run.id,
        "message": "Opened in KLayout + metadata generation started"
    })



# launcher/views.py
"""
@api_view(["POST"])
def run_tool(request, slug):
    tool = get_object_or_404(Tool, slug=slug)

    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"ok": False, "error": "No file uploaded"}, status=400)

    uploads_dir = os.path.join(settings.BASE_DIR, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}_{upload.name}"
    full_path = os.path.join(uploads_dir, filename)

    with open(full_path, "wb") as f:
        for chunk in upload.chunks():
            f.write(chunk)

    try:
        result = execute_tool_run(
            tool=tool,
            user=request.user if request.user.is_authenticated else None,
            upload_filename=filename,
        )
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

    return JsonResponse({
        "ok": True,
        **result
    })
"""

def logs_page(request):
    runs = ToolRun.objects.order_by("-created_at")[:50]
    return render(request, "launcher/logs.html", {"runs": runs})

def logs_home(request):
    """
    Landing page for logs.
    """
    recent_runs = ToolRun.objects.order_by("-created_at")[:20]

    return render(request, "launcher/logs_home.html", {
        "recent_runs": recent_runs
    })


def logs_by_scope(request, scope):
    """
    Logs filtered by scope:
    simulation | layout | runs | errors
    """

    qs = ToolRun.objects.order_by("-created_at")

    if scope == "simulation":
        qs = qs.filter(tool__slug="verilator")

    elif scope == "layout":
        qs = qs.filter(tool__slug="klayout")

    elif scope == "errors":
        qs = qs.filter(status="failed")

    elif scope == "runs":
        pass  # all runs

    else:
        return HttpResponse("Invalid log scope", status=404)

    return render(request, "launcher/logs_list.html", {
        "scope": scope,
        "runs": qs[:50]
    })

import subprocess

def run_bash(command, cwd=None, timeout=300):
    """
    Execute a shell command and return (stdout, stderr)
    """
    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        text=True
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        stderr += "\n[ERROR] Command timed out"

    return stdout, stderr

def windows_to_wsl(path):
    path = path.replace("\\", "/")
    if path[1:3] == ":/":
        drive = path[0].lower()
        return f"/mnt/{drive}{path[2:]}"
    return path



from django.utils import timezone

def execute_verilator_run(*, tool, user, upload_path):
    from django.utils import timezone
    import os

    run = ToolRun.objects.create(
        tool=tool,
        user=user,
        input_file=os.path.basename(upload_path),
        status="running"
    )

    try:
        wsl_file = windows_to_wsl(upload_path)

        cmd = f"verilator --lint-only {wsl_file}"

        stdout, stderr = run_bash(
            f"wsl bash -lc '{cmd}'"
        )

        run.stdout = stdout
        run.stderr = stderr
        run.status = "success" if not stderr else "failed"

    except Exception as e:
        run.stderr = str(e)
        run.status = "failed"

    run.completed_at = timezone.now()
    run.save()

    return run


@api_view(["POST"])
def run_tool(request, slug):
    tool = get_object_or_404(Tool, slug=slug)
    upload = request.FILES.get("file")

    if not upload:
        return Response({"ok": False, "error": "No file uploaded"}, status=400)

    uploads_dir = os.path.join(settings.BASE_DIR, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}_{upload.name}"
    full_path = os.path.join(uploads_dir, filename)

    with open(full_path, "wb") as f:
        for chunk in upload.chunks():
            f.write(chunk)

    run = execute_verilator_run(
        tool=tool,
        user=request.user if request.user.is_authenticated else None,
        upload_path=full_path
    )

    return Response({
        "ok": run.status == "success",
        "run_id": run.id,
        "stdout": run.stdout,
        "stderr": run.stderr,
        "status": run.status
    })
def view_run_logs(request, run_id):
    run = get_object_or_404(ToolRun, id=run_id)

    return render(
        request,
        "launcher/run_detail.html",   # ✅ CORRECT PATH
        {"run": run}
    )
"""
def view_run_logs(request, run_id):
    run = get_object_or_404(
        ToolRun.objects.select_related("tool", "user"),
        id=run_id
    )

    return render(request, "launcher/logs/run_detail.html", {
        "run": run
    })
"""
def download_run_logs(request, run_id):
    run = get_object_or_404(ToolRun, id=run_id)

    content = f"""
========================================
EDA TOOL RUN LOG
========================================

Tool      : {run.tool.name}
Status    : {run.status}
Started   : {run.created_at}
Completed : {run.completed_at or "Running"}

----------------------------------------
STDOUT
----------------------------------------
{run.stdout or "No STDOUT"}

----------------------------------------
STDERR
----------------------------------------
{run.stderr or "No STDERR"}
"""

    response = HttpResponse(content, content_type="text/plain")
    response["Content-Disposition"] = (
        f'attachment; filename="{run.tool.slug}_run_{run.id}.log"'
    )
    return response