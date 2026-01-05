from .models import ToolRun
import uuid
import subprocess
import os
import shutil
from django.conf import settings


def execute_tool_run(*, tool, user, upload_filename):
    base = settings.BASE_DIR
    run_id = uuid.uuid4()

    run_dir = os.path.join(base, "uploads", "runs", str(run_id))
    os.makedirs(run_dir, exist_ok=True)

    source = os.path.join(base, "uploads", upload_filename)
    shutil.copy(source, run_dir)

    log_file = os.path.join(run_dir, "run.log")

    run = ToolRun.objects.create(
        id=run_id,
        tool=tool,
        user=user,
        status="running",
        run_dir=run_dir,
    )

    cmd = ["python", "--version"]  # replace later

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout, stderr = proc.communicate()

    with open(log_file, "w") as f:
        f.write("STDOUT:\n" + (stdout or ""))
        f.write("\n\nSTDERR:\n" + (stderr or ""))

    run.status = "success" if proc.returncode == 0 else "failed"
    run.log_path = f"/uploads/runs/{run_id}/run.log"
    run.save()

    return {
        "ok": True,
        "stdout": stdout,
        "stderr": stderr,
        "log_path": run.log_path,
        "run_id": str(run_id),
    }
