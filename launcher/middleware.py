import time
from django.shortcuts import redirect
from django.contrib.auth import logout

class IdleTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        # 🚫 Ignore noise requests
        IGNORE_PATHS = (
            "/static/",
            "/login/",
            "/logout/",
            "/favicon.ico",
            "/.well-known/",
        )

        if request.path.startswith(IGNORE_PATHS):
            return self.get_response(request)

        now = int(time.time())
        last = request.session.get("last_activity")

        # 🧠 First request after login
        if last is None:
            request.session["last_activity"] = now
            return self.get_response(request)

        # ⏱️ Enforce idle timeout
        if now - last > 600:  # 10 minutes
            logout(request)
            request.session.flush()
            return redirect("login")

        # ✅ Update activity ONLY on real page hits
        request.session["last_activity"] = now

        return self.get_response(request)
