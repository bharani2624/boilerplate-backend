# Unauthenticated liveness check. Why it's here: Render (and any uptime monitor) needs a
# cheap endpoint that doesn't require a JWT to confirm the process is up — this is also
# what you'd curl to wake up a free-tier Render instance that's spun down from idling.

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}
