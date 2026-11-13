# -*- coding: utf-8 -*-
"""Движок генерации документов школы (.docx по шаблонам реестра).

Общий контекст токенов для всех шаблонов: company_*, student_*,
parent_*, contract_*, doc_* — шаблон использует любой набор.
"""
import re
from io import BytesIO

from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _

MONTHS_GEN = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
              'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
MONTHS_NOM = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
              'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']
SUMMER_MONTHS = (6, 7, 8)  # июнь-август — летние месяцы графика


def fmt_amount(value):
    """525000 -> '525 000' (пробел-разделитель разрядов)."""
    return f'{int(round(value)):,}'.replace(',', ' ')


def amount_words(value):
    """525000 -> 'пятьсот двадцать пять тысяч'."""
    from num2words import num2words
    return num2words(int(round(value)), lang='ru')


def date_iso(d):
    return d.strftime('%d.%m.%Y') if d else ''


def date_quoted(d):
    """date(2026, 8, 18) -> '«18» августа 2026 г.'"""
    if not d:
        return ''
    return f'«{d.day}» {MONTHS_GEN[d.month - 1]} {d.year} г.'


def month_year_gen(d):
    """date(2026, 9, 1) -> 'сентября 2026'."""
    return f'{MONTHS_GEN[d.month - 1]} {d.year}'


def _guess_gender(name):
    """Пол по отчеству (для склонения директора: Виктора/Елены)."""
    parts = (name or '').split()
    if len(parts) >= 3 and parts[2].lower().endswith(('вна', 'чна', 'кна')):
        return 'female'
    return 'male'


def fio_case(full_name, case, gender='male'):
    """Склонение ФИО через petrovich; не ФИО возвращается как есть."""
    from petrovich import Case, Gender as PGender, Petrovich
    parts = (full_name or '').strip().split()
    if len(parts) != 3:
        return full_name or ''
    g = PGender.FEMALE if gender == 'female' else PGender.MALE
    last, first, middle = parts
    try:
        p = Petrovich()
        return ' '.join([
            p.lastname(last, case, g),
            p.firstname(first, case, g),
            p.middlename(middle, case, g),
        ])
    except Exception:
        return full_name


def fio_gen(full_name, gender='male'):
    """Родительный падеж: 'Батцель Ратмир Александрович' ->
    'Батцеля Ратмира Александровича'."""
    from petrovich import Case
    return fio_case(full_name, Case.GENITIVE, gender)


def fio_acc(full_name, gender='male'):
    """Винительный падеж (в лице кого)."""
    from petrovich import Case
    return fio_case(full_name, Case.ACCUSATIVE, gender)


def fio_short(full_name):
    """'Батцель Елена Александровна' -> 'Батцель Е.А.'"""
    parts = (full_name or '').strip().split()
    if len(parts) == 3:
        return f'{parts[0]} {parts[1][0]}.{parts[2][0]}.'
    return full_name or ''


def render_docx(template_bytes, context):
    """Заполнить .docx-шаблон (docxtpl). Недостающий токен = ошибка,
    чтобы испорченный/неполный контекст не дал молча кривой документ."""
    from docxtpl import DocxTemplate
    from jinja2 import Environment, StrictUndefined

    env = Environment(undefined=StrictUndefined, autoescape=True)
    doc = DocxTemplate(BytesIO(template_bytes))
    doc.render(context, jinja_env=env)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def action_generate_doc(self):
    """Открыть мастер генерации документа по этой записи.

    Подключается к моделям присваиванием (action_generate_doc =
    doc_engine.action_generate_doc): наследование-список с абстрактным
    mixin сдвигает setup-порядок моделей и ломает One2many.
    """
    self.ensure_one()
    return {
        'type': 'ir.actions.act_window',
        'name': _('Сгенерировать документ'),
        'res_model': 'rost.doc.generate.wizard',
        'view_mode': 'form',
        'target': 'new',
        'context': {
            'default_res_model': self._name,
            'default_res_id': self.id,
        },
    }


def _rost_company_ctx(self):
    company = self.env.company
    director = company.rost_director_name or ''
    return {
        'company_name': company.name or '',
        'company_director_full': director,
        'company_director_acc': fio_acc(director, _guess_gender(director)),
        'company_director_short': company.rost_director_short or '',
        'company_director_basis': company.rost_director_basis or '',
        'company_phone': company.phone or '',
    }


def _rost_student_ctx(self, student):
    """Токены student_* (общие: подписка/ученик/приёмка)."""
    keys = ['student_name', 'student_name_gen', 'student_learner_gen',
            'student_birth_iso', 'student_class']
    if not student:
        return dict.fromkeys(keys, '')
    gender = getattr(student, 'gender', '') or 'male'
    course = student._get_billing_course_detail().course_id
    m = re.search(r'\d+', course.name or '') if course else None
    return {
        'student_name': student.name or '',
        'student_name_gen': fio_gen(student.name, gender),
        'student_learner_gen': ('ученицы' if gender == 'female'
                                else 'ученика'),
        'student_birth_iso': date_iso(student.birth_date),
        'student_class': m.group(0) if m else (course.name or ''),
    }


def _rost_parent_ctx(self, parent, relationship=''):
    """Токены parent_* + род фраз (именуемый/ая, являющийся/аяся).

    parent — запись op.parent: личные данные в SIS (решение 12.11.2026),
    телефон/почта — стандартные поля контакта. None -> пустые токены.
    """
    keys = ['parent_name', 'parent_short', 'parent_birth_iso',
            'parent_passport', 'parent_passport_issued_by',
            'parent_passport_issue_iso', 'parent_passport_dept_code',
            'parent_address_home', 'parent_address_reg',
            'parent_phone', 'parent_email']
    if parent:
        partner = parent.name
        ctx = {
            'parent_name': partner.name or '',
            'parent_short': fio_short(partner.name),
            'parent_birth_iso': date_iso(parent.birth_date),
            'parent_passport': parent.passport_number or '',
            'parent_passport_issued_by': parent.passport_issued_by or '',
            'parent_passport_issue_iso': date_iso(parent.passport_issue_date),
            'parent_passport_dept_code': parent.passport_dept_code or '',
            'parent_address_home': parent.address_home or '',
            'parent_address_reg': parent.address_reg or '',
            'parent_phone': partner.mobile or partner.phone or '',
            'parent_email': partner.email or '',
        }
    else:
        ctx = dict.fromkeys(keys, '')
    rel = (relationship or '').lower()
    female = not rel.startswith('отец')
    ctx['parent_relationship'] = relationship or ''
    ctx['parent_named'] = 'именуемая' if female else 'именуемый'
    ctx['parent_being'] = 'являющаяся' if female else 'являющийся'
    return ctx
