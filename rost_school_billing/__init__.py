from . import models

FORM_FIELDS = (
    'child_name', 'child_gender', 'child_birth_date', 'child_course_id',
    'child_current_school', 'child_interests', 'child_medical',
    'child_address', 'personal_data_consent',
)


def post_init_hook(env):
    """Разрешить поля анкеты ученика к записи из веб-форм сайта
    (website form builder по умолчанию блокирует все поля)."""
    env.cr.execute(
        "UPDATE ir_model_fields SET website_form_blacklisted=false "
        "WHERE model='crm.lead' AND name IN %s", [FORM_FIELDS])
