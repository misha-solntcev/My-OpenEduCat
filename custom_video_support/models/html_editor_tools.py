import logging
import re
from odoo.addons.html_editor import tools
from odoo import _
from werkzeug.urls import url_encode

_logger = logging.getLogger(__name__)

# Регулярки для базового распознавания платформы
REGEX_RUTUBE = r'rutube\.ru/(?:video|play/embed)/([a-zA-Z0-9]+)'
REGEX_VK_DOMAIN = r'(?:vk\.com|vkvideo\.ru)'

_orig_get_video_source_data = tools.get_video_source_data
_orig_get_video_url_data = tools.get_video_url_data

def get_video_source_data(video_url):
    if not video_url: return None

    # Сначала стандартные платформы
    source = _orig_get_video_source_data(video_url)
    if source: return source

    # 1. Rutube
    rutube_match = re.search(REGEX_RUTUBE, video_url)
    if rutube_match:
        return ('rutube', rutube_match[1], rutube_match)

    # 2. VK (Более надежный поиск параметров)
    if re.search(REGEX_VK_DOMAIN, video_url):
        oid = vid = v_hash = None

        # Пытаемся найти oid и id (формат iframe)
        oid_m = re.search(r'oid=(-?\d+)', video_url)
        id_m = re.search(r'id=(\d+)', video_url)
        # Или формат ссылки video-123_456
        link_m = re.search(r'video(-?\d+)_(\d+)', video_url)
        # Ищем hash (если есть)
        hash_m = re.search(r'hash=([a-z0-9]+)', video_url)

        if oid_m and id_m:
            oid, vid = oid_m[1], id_m[1]
        elif link_m:
            oid, vid = link_m[1], link_m[2]

        if oid and vid:
            v_hash = hash_m[1] if hash_m else ""
            video_id = f"{oid}_{vid}"
            if v_hash: video_id += f"_{v_hash}"            
            return ('vk', video_id, None)

    return None

def get_video_url_data(video_url, **kwargs):
    source = get_video_source_data(video_url)
    if source:
        platform, video_id, _ = source
        if platform in ['rutube', 'vk']:
            params = {}
            if kwargs.get('autoplay'): params['autoplay'] = 1

            if platform == 'rutube':
                embed_url = f'https://rutube.ru/play/embed/{video_id}'
            else:
                parts = video_id.split('_')
                # Формируем чистый URL для iframe
                embed_url = f'https://vk.com/video_ext.php?oid={parts[0]}&id={parts[1]}'
                if len(parts) > 2 and parts[2]:
                    params['hash'] = parts[2]

            if params:
                embed_url = f"{embed_url}&{url_encode(params)}" if '?' in embed_url else f"{embed_url}?{url_encode(params)}"

            return {'platform': platform, 'embed_url': embed_url, 'video_id': video_id, 'params': params}

    return _orig_get_video_url_data(video_url, **kwargs)

tools.get_video_source_data = get_video_source_data
tools.get_video_url_data = get_video_url_data
