import logging
from datetime import datetime, timedelta

from django.utils import timezone

logger = logging.getLogger("superuser")

EXPIRY = 60 * 30  # 30 minutes

MAX_CONCURRENT_PRIVILEGES = 5


def apply_temporary_superuser_access(request, slug):
    if not isinstance(slug, str) or not slug.strip():
        raise ValueError("Invalid slug")

    remove_expired_temporary_superuser_access(request)
    if has_temporary_superuser_access(request, slug):
        return

    elevated_privileges = request.session.get("elevated_privileges", [])
    if len(elevated_privileges) >= MAX_CONCURRENT_PRIVILEGES:
        raise ValueError("Maximum number of concurrent privileges exceeded")

    logger.info(f"Applying temporary superuser access for '{request.user.email}' to '{slug}'")
    expire = timezone.now() + timedelta(seconds=EXPIRY)
    elevated_privileges.append((slug, int(expire.timestamp())))
    request.session["elevated_privileges"] = elevated_privileges


def has_temporary_superuser_access(request, slug):
    elevated_privileges = request.session.get("elevated_privileges", [])
    now = int(timezone.now().timestamp())
    has_access = any(team == slug and expire > now for team, expire in elevated_privileges)
    if not has_access:
        remove_temporary_superuser_access(request, slug)
    return has_access


def remove_temporary_superuser_access(request, slug):
    """This removes access to the specific team and also expired access."""

    elevated_privileges = request.session.get("elevated_privileges", [])
    now = int(timezone.now().timestamp())
    request.session["elevated_privileges"] = [
        (team, expire) for team, expire in elevated_privileges if team != slug or expire <= now
    ]


def remove_expired_temporary_superuser_access(request):
    elevated_privileges = request.session.get("elevated_privileges", [])
    now = int(timezone.now().timestamp())
    request.session["elevated_privileges"] = [(team, expire) for team, expire in elevated_privileges if expire > now]


def get_temporary_superuser_access(request):
    remove_expired_temporary_superuser_access(request)
    return {slug: datetime.fromtimestamp(expire) for slug, expire in request.session.get("elevated_privileges", [])}
