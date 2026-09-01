# -*- coding: utf-8 -*-
"""
Хелперы для rost_max_miniapp: восстановление Odoo-сессии из заголовка
X-Session-Id. Используется как fallback для веб-версии MAX (iframe на
web.max.ru), где браузер блокирует сторонние cookie и session_id кука
не сохраняется.

Механизм:
1. SPA сохраняет session_id в localStorage после логина
2. SPA передаёт session_id в заголовке X-Session-Id в каждом API-запросе
3. Хелпер проверяет: если сессия запроса анонимна, но есть X-Session-Id —
   загружает сохранённую сессию из session store и подменяет данные
   текущей сессии.
"""

import logging

from odoo.http import request, root

_logger = logging.getLogger(__name__)


def restore_session_if_needed():
    """Поднимает сессию из session store по заголовку X-Session-Id.

    Odoo 18: у Session нет load(); сессии живут в root.session_store
    (FilesystemSessionStore). Если сессия запроса уже аутентифицирована
    (cookie дошла) — ничего не делаем. Иначе грузим сессию по sid из
    заголовка и копируем её данные в текущую сессию запроса.

    Возвращает True, если сессия была восстановлена.
    """
    # Если уже есть валидная сессия — ничего не делаем
    if request.session and request.session.uid:
        return False

    session_id = request.httprequest.headers.get('X-Session-Id')
    if not session_id:
        return False

    # Формат ключа в Odoo 18: 84 символа base64url
    if not root.session_store.is_valid_key(session_id):
        _logger.debug("X-Session-Id has invalid format, skipping restore")
        return False

    try:
        stored = root.session_store.get(session_id)
        if not stored or not stored.get('uid'):
            return False

        # Копируем данные сохранённой сессии (uid, db, context,
        # is_timetable_user, spa_csrf_token...) в сессию запроса.
        request.session.clear()
        request.session.update(stored)
        request.session.sid = session_id
        request.session.db = stored.get('db') or request.session.db

        # ВАЖНО: clear() взводит session.should_rotate (защита от session
        # fixation). В конце запроса Odoo тогда создаёт НОВЫЙ sid, а старый
        # (хранящийся в localStorage клиента и в соседних параллельных
        # запросах) удаляется из store -> следующий restore падает, юзер
        # молча становится гостем ("Занятий не найдено"). Гасим ротацию:
        # сессия уже аутентифицирована, повторная ротация здесь не нужна.
        request.session.should_rotate = False

        # Пересобираем env под восстановленного пользователя — он был
        # создан для анонимной сессии при старте запроса.
        import odoo
        request.env = odoo.api.Environment(
            request.env.cr, request.session.uid, request.session.context
        )

        _logger.info(
            "Session restored from X-Session-Id for uid=%s",
            request.session.uid,
        )
        return True
    except Exception:
        _logger.exception("Failed to restore session from X-Session-Id")

    return False
