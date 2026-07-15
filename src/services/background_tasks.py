"""Fire-and-forget work that shouldn't make a request wait on it.

Why this file exists: some work (logging an event, sending a notification, calling a
slow third-party API) doesn't need to finish before the response goes back to the
client. FastAPI's built-in BackgroundTasks (from Starlette — no extra dependency, no
broker/worker process to run) executes a function after the response is sent, in the
same process. That's the right amount of infrastructure for a hackathon boilerplate on
a single instance.

This is NOT a durable job queue: if the process restarts before a background task
runs, that task is lost, and there's no retry. If a builder-round problem statement
needs tasks to survive a restart, run on a schedule, or retry on failure, that's the
point where you'd introduce a real queue (Celery/RQ/arq + Redis) instead of this —
don't reach for that ahead of time.

Usage pattern (see src/api/routes/auth_routes.py):

    from fastapi import BackgroundTasks
    from src.services.background_tasks import log_login_event

    @router.post("/google")
    async def login_with_google(body: ..., background_tasks: BackgroundTasks):
        ...
        background_tasks.add_task(log_login_event, user_id=str(user.id), email=user.email)
        return ...

Functions passed to add_task can be sync or async — FastAPI runs sync ones in the
background-task thread pool and awaits async ones directly, either way without
blocking the response that already went out.
"""

import logging

logger = logging.getLogger("background_tasks")


def log_login_event(user_id: str, email: str) -> None:
    """Example background task: record a login without delaying the auth response.
    Replace with something real (e.g. an analytics event, a welcome email trigger)."""
    logger.info("login user_id=%s email=%s", user_id, email)


def log_promo_applied(user_id: str, code: str) -> None:
    """Optional background log when a promo is successfully applied to a cart."""
    logger.info("promo_applied user_id=%s code=%s", user_id, code)
