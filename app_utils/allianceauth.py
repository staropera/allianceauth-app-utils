import re
from functools import partial
from typing import List

from django.contrib.auth.models import Permission, User

from allianceauth.notifications import notify
from allianceauth.tests.auth_utils import AuthUtils
from allianceauth.views import NightModeRedirectView

from ._app_settings import APPUTILS_ADMIN_NOTIFY_TIMEOUT
from .django import users_with_permission
from .helpers import throttle


def notify_admins(message: str, title: str, level: str = "info") -> None:
    """Send notification to all admins.

    Args:
        message: Message text
        title: Message title
        level: Notification level of the message.
    """
    try:
        perm = Permission.objects.get(codename="logging_notifications")
    except Permission.DoesNotExist:
        users = User.objects.filter(is_superuser=True)
    else:
        users = users_with_permission(perm)
    for user in users:
        notify(user, title=title, message=message, level=level)


def notify_admins_throttled(
    message_id: str,
    message: str,
    title: str,
    level: str = "info",
    timeout: int = None,
):
    """Send notification to all admins, but limits the freqency
    for sending messages with the same message ID, e.g. to once per day.

    If this function is called during a timeout the notification will simply be ignored.

    Args:
        message_id: ID representing this message
        message: Message text
        title: Message title
        level: Notification level of the message.
        timeout: Time between each notification, e.g. 86400 = once per day.\
            When not provided uses system default,\
            which is 86400 and can also be set via this Django setting:\
            APP_UTILS_NOTIFY_THROTTLED_TIMEOUT
    """
    if not timeout:
        timeout = APPUTILS_ADMIN_NOTIFY_TIMEOUT
    throttle(
        func=partial(notify_admins, message, title, level),
        context_id=message_id,
        timeout=timeout,
    )


def notify_throttled(
    message_id: str,
    user: User,
    title: str,
    message: str,
    level: str = "info",
    timeout: int = None,
):
    """Send notification to user, but limits the freqency
    for sending messages with the same message ID, e.g. to once per day.

    If this function is called during a timeout the notification will simply be ignored.

    Args:
        message_id: ID representing this message
        title: Message title
        message: Message text
        level: Notification level of the message.
        timeout: Time between each notification, e.g. 86400 = once per day.\
            When not provided uses system default,\
            which is 86400 and can also be set via this Django setting:\
            APP_UTILS_NOTIFY_THROTTLED_TIMEOUT
    """
    if not timeout:
        timeout = APPUTILS_ADMIN_NOTIFY_TIMEOUT
    throttle(
        func=partial(notify, user, title, message, level),
        context_id=message_id,
        timeout=timeout,
    )


def is_night_mode(request) -> bool:
    """Returns True if the current user session is in night mode, else False"""
    return NightModeRedirectView.night_mode_state(request)


def create_fake_user(
    character_id: int,
    character_name: str,
    corporation_id: int = None,
    corporation_name: str = None,
    corporation_ticker: str = None,
    alliance_id: int = None,
    alliance_name: str = None,
    permissions: List[str] = None,
) -> User:
    """Create a fake user incl. main character and (optional) permissions.

    Will use default corporation and alliance if not set.
    """
    username = re.sub(r"[^\w\d@\.\+-]", "_", character_name)
    user = AuthUtils.create_user(username)
    if not corporation_id:
        corporation_id = 2001
        corporation_name = "Wayne Technologies Inc."
        corporation_ticker = "WTE"
    if corporation_id == 2001:
        alliance_id = 3001
        alliance_name = "Wayne Enterprises"
    AuthUtils.add_main_character_2(
        user=user,
        name=character_name,
        character_id=character_id,
        corp_id=corporation_id,
        corp_name=corporation_name,
        corp_ticker=corporation_ticker,
        alliance_id=alliance_id,
        alliance_name=alliance_name,
    )
    if permissions:
        perm_objs = [AuthUtils.get_permission_by_name(perm) for perm in permissions]
        user = AuthUtils.add_permissions_to_user(perms=perm_objs, user=user)
    return user
