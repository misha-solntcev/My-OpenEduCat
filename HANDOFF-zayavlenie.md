# Заявление о приёме — веб-форма (as-built)

## Итог (20.11.2026)

Реализовано заявление о приёме по персональной ссылке — **не** survey
и **не** форма на `op.admission`, как в исходном плане ниже.

- Модель-носитель: **`crm.lead`** — лид существует с начала воронки,
  заказ и приёмка ссылаются на него (`sale_order_id.opportunity_id`),
  файлы не дублируются.
- Доступ: **персональная ссылка** `/zayavlenie/<token>` по токену,
  срок 7 дней от выдачи; публичной страницы в меню сайта нет.
- UI анкеты — **на подтверждённом заказе** (state='sale'): related-поля
  статуса через `opportunity_id`, кнопки «Отправить анкету» /
  «Открыть анкету» / «Новая ссылка», цветные alert-полосы
  (info/success/warning) под шапкой. На лиде и приёмке анкеты-UI нет.
- Обязательные документы: **СНИЛС**, **медстраховой полис**; опционально
  «Другие документы» (несколько) и комментарий. PDF/JPG/PNG/HEIC,
  до 10 МБ на файл, 50 МБ на форму.
- Три согласия (перс. данные, психсопровождение, условия договора).
- Код: `controllers/main.py` (GET форма / POST submit / GET doc по
  токену) + `views/website_templates.xml` (рукописная разметка **без**
  класса `s_website_form` — он вешает JS-виджет сниппета) в
  `rost_school_billing`; depends +`website`, +`sale_crm`.
- Вложения — `ir.attachment` с `rost_doc_type` (snils/policy/
  birth_cert/passport/consent/other); скачивание только своим роутом
  по токену (`/web/content` анониму отвечает 403, все обращения к
  вложениям в публичном контроллере — через sudo).
- При зачислении документы **переезжают** (смена res_model/res_id):
  snils/policy/birth_cert/other → `op.student`, passport/consent →
  `op.parent` (`op.student.rost_adopt_zayavlenie_documents` + override
  `enroll_student` в billing; заявитель сохраняется ДО super()).
- «Созданной» ссылки нет: токен выдаётся кнопкой «Отправить анкету»
  (письмо родителю через composer), «Новая ссылка» перевыпускает
  токен; без ссылки кнопка «Открыть анкету» даёт notification.

Проверено на test4 20.11.2026: HTTP E2E анонимной сессией (32 проверки:
валидация, файлы, замена СНИЛС, 404 на чужие вложения, просрочка),
перенос при зачислении в savepoint, кнопочные методы, вёрстка в
браузере. Коммиты `45a2499`, `81e22bc`.

## Сохранённые наработки по опросу

- Ветка: **`misha-solntcev/survey-zayavlenie`**, commit `c08ac31`.
- Модули: `rost_school_admission_survey`, `survey_question_type_binary`
  (вендоренный OCA PR #232 для 18.0 + `ru.po`).
- В БД `test4` опрос установлен; ответы: 5 — чистый бланк, 8 — демо
  с файлами, 11 — черновик для проверки загрузки.
- Ветку не трогать. Вернуться можно в любой момент.

## Инфраструктура

- Odoo 18, контейнер `odoo-dev-odoo-1`, БД `test4`.
- Контейнер монтирует `/home/nnm/odoo-dev/addons` как `/mnt/extra-addons`.
- Установка/обновление:
  `docker exec odoo-dev-odoo-1 odoo -c /etc/odoo/odoo.conf -d test4 -u rost_school_billing --stop-after-init --no-http`,
  после изменений Python — `docker restart odoo-dev-odoo-1`.
- Подробный E2E-рецепт и ловушки — references/billing-architecture.md
  скилла odoo-dev, раздел «Заявление о приёме по персональной ссылке».
