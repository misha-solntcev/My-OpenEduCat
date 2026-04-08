{
    'name': 'Custom Video Support (VK, Rutube)',
    'version': '18.0.1.0',
    'license': 'LGPL-3',
    'author': 'Demyanenko Matvey, Michail Solntcev',
    'depends': ['html_editor', 'web_editor'],
    'data': [],
    'assets': {
        'html_editor.assets': [
            'custom_video_support/static/src/utils/url_patch.js',
            'custom_video_support/static/src/main/media/media_dialog/video_selector_patch.js',
            'custom_video_support/static/src/main/media/media_dialog/video_selector.xml',
        ],
        'web.assets_backend': [
            'custom_video_support/static/src/utils/url_patch.js',
            'custom_video_support/static/src/main/media/media_dialog/video_selector_patch.js',
            'custom_video_support/static/src/main/media/media_dialog/video_selector.xml',
        ],
        'web.assets_frontend': [
            'custom_video_support/static/src/utils/url_patch.js',
            'custom_video_support/static/src/main/media/media_dialog/video_selector_patch.js',
            'custom_video_support/static/src/main/media/media_dialog/video_selector.xml',
        ],
    },
    'installable': True,
}

