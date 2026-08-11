# -*- coding: utf-8 -*-
"""
Хелперы для rost_max_miniapp: восстановление Odoo-сессии из заголовка
X-Session-Id. Используется как fallback для MAX WebView, где cookie
могут не сохраняться из-за SameSite/CSP ограничений cross-site контекста.

Механизм:
1. MAX WebView сохраняет session_id в localStorage после логина
2. SPA передаёт session_id в заголовке X-Session-Id каждом API-запросе
3. Хелпер проверяет: если cookie session_id отсутствует, но
   есть X-Session-Id — пытается восстановить сессию
"""

from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

# Имя cookie session_id в Odoo по умолчанию
SESSION_COOKIE_NAME = 'session_id'


def restore_session_if_needed():
    """Проверяет X-Session-Id заголовок и пытается восстановить сессию.

    Если пользователь уже аутентифицирован через cookie — ничего не делает.
    Если cookie отсутствует, но есть X-Session-Id — пытаемся загрузить
    сессию с этим ID.

    Возвращает True, если сессия была восстановлена.
    """
    # Если уже есть валидная сессия — ничего не делаем
    if request.session and request.session.uid:
        return False

    # Проверяем X-Session-Id заголовок (fallback для MAX WebView)
    session_id = request.httprequest.headers.get('X-Session-Id')
    if not session_id:
        return False

    try:
        # Пытаемся загрузить сессию по переданному session_id
        # Используем внутренний метод Odoo для загрузки сессии
        request.session.sid = session_id
        request.session._pstore = None  # сбрасываем кэш
        request.session.load()
        if request.session.uid:
            _logger.debug(
                "Session restored from X-Session-Id header for uid=%s, sid=%s",
                request.session.uid, session_id,
            )
            return True
    except Exception as e:
        _logger.warning("Failed to restore session from X-Session-Id: %s", e)

    return False
