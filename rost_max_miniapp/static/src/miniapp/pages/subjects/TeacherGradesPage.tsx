/**
 * Вкладка «Оценки» учителя (мокап design/teacher-grades-mockup.html).
 * Три экрана с внутренним переключением панелей (тот же паттерн, что
 * TeacherHomeworkPage), данные — одним эндпоинтом /api/teacher/grades:
 *
 *   1. Мои пары            — список своих предметов (админ — вся школа)
 *   2. Ученики пары        — тап по паре
 *   3. Карточка ученика    — все предметы ученика; свой предмет кликабелен,
 *                           чужие приглушены и помечены «только чтение»
 *
 * Четвёртый экран (детализация предмета) — переиспользуемый SubjectGradesPage
 * ученика, туда ведёт коллбэк onOpenSubject.
 *
 * Оценку отсюда НЕ ставим: просмотр только, правка — в журнале урока.
 */
import React from 'react';
import {
  Panel, PanelHeader, PanelHeaderBack, PanelHeaderContent, Div, Spinner, Button,
  Caption, Text, Box, SegmentedControl, IconButton,
} from '@vkontakte/vkui';
import { Icon24Filter } from '@vkontakte/icons';
import { apiGet } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { SubjectAvatar } from '@/shared/components/SubjectIcon';
import { ChipFilterModal, FilterChipRow } from '@/shared/components/ChipFilterModal';
import type { ChipFilters, ChipFilterSection } from '@/shared/components/ChipFilterModal';
import { PairCard, StudentRow, SubjectCard, fmtAvg } from '@/shared/components/TeacherGradeCards';
import type {
  TeacherPairsResponse, TeacherPairStudentsResponse, TeacherStudentResponse,
  TeacherPair,
} from '@/shared/lib/types';

type View = 'pairs' | 'students' | 'student';

/** Переключатель четверти — как у ученика (SegmentedControl). */
const QuarterBar: React.FC<{
  quarters: { q: number; name: string }[];
  value: number;
  onChange: (q: number) => void;
}> = ({ quarters, value, onChange }) => {
  if (quarters.length < 2) return null;
  return (
    <Box padding="m" style={{ paddingBottom: 0 }}>
      <SegmentedControl
        value={String(value)}
        onChange={v => onChange(Number(v))}
        options={quarters.map(q => ({ value: String(q.q), label: q.name }))}
      />
    </Box>
  );
};

const Loading: React.FC = () => (
  <Div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
    <Spinner size="l" />
  </Div>
);

export const TeacherGradesPage: React.FC<{
  id: string;
  /** Открыть детализацию предмета выбранного ученика (переиспользуем
   *  экран ученика SubjectGradesPage). */
  onOpenSubject?: (
    subjectId: number, subjectName: string, studentId: number, studentName: string,
  ) => void;
}> = ({ id, onOpenSubject }) => {
  const addToast = useToast();
  const [view, setView] = React.useState<View>('pairs');
  // Пара, из которой пришли к ученику: пригодятся, когда ученик вернётся
  // на экран 2 по прямой ссылке (например, из «назад» в детализации).
  const [, setLastPair] = React.useState<TeacherPair | null>(null);
  const [quarter, setQuarter] = React.useState<number | null>(null);
  const [data, setData] = React.useState<TeacherPairsResponse | null>(null);
  const [detail, setDetail] = React.useState<TeacherPairStudentsResponse | null>(null);
  const [student, setStudent] = React.useState<TeacherStudentResponse | null>(null);
  const [loading, setLoading] = React.useState(true);

  // Фильтры «Моих пар» (мокап design/grades-filters.html, утверждён
  // 2026-10-14): ИЛИ внутри секции, И между; пустой Set = «все».
  // Опции и счётчики — из самих пар, ось «Учителя» только у админа —
  // его список вся школа, у учителя свои пары и так.
  const [filters, setFilters] = React.useState<ChipFilters>({});
  const [filtersOpen, setFiltersOpen] = React.useState(false);
  // Зеркало черновика шторки: секции пересчитываются по НЕ применённому
  // выбору — фасетное сужение видно прямо в открытой шторке, не после «Ок».
  const [sheetDraft, setSheetDraft] = React.useState<ChipFilters>({});
  const isAdminRole = data?.role === 'admin';

  const sheetSections: ChipFilterSection[] = React.useMemo(() => {
    const pairs = data?.pairs ?? [];
    // Фасетный поиск (вариант A, Миша 2026-10-14): опции секции считаются
    // по парам, проходящим фильтры ДРУГИХ секций — несовместимую
    // комбинацию («5 А» + «Алгебра») собрать нельзя. Выбранные значения
    // остаются в списке даже с нулевым счётчиком, иначе их нельзя снять,
    // не сняв сначала соседнюю секцию.
    const KEYS = isAdminRole
      ? ['batches', 'subjects', 'faculties'] as const
      : ['batches', 'subjects'] as const;
    const HEADERS: Record<string, string> = {
      batches: 'Классы', subjects: 'Предметы', faculties: 'Учителя',
    };
    const FIELD: Record<string, (p: TeacherPair) => string> = {
      batches: p => p.batch, subjects: p => p.subject, faculties: p => p.faculty,
    };
    return KEYS.map(key => {
      const source = pairs.filter(p => KEYS
        .filter(k => k !== key)
        .every(k => {
          const sel = sheetDraft[k];
          return !sel?.size || sel.has(FIELD[k](p));
        }));
      const sel = sheetDraft[key];
      const uniq = [...new Set([
        ...source.map(FIELD[key]),
        ...(sel?.size ? [...sel] : []), // выбранное не пропадает из шторки
      ])].sort((a, b) => a.localeCompare(b, 'ru', { numeric: true }));
      return {
        key, header: HEADERS[key],
        options: uniq.map(v => ({
          value: v, count: source.filter(p => FIELD[key](p) === v).length,
        })),
      };
    }).filter(s => s.options.length > 0);
  }, [data, sheetDraft, isAdminRole]);

  // Чипы над лентой строятся по ПРИМЕНЁННОМУ фильтру (порядок фиксированный).
  const chipKeys = isAdminRole
    ? ['batches', 'subjects', 'faculties']
    : ['batches', 'subjects'];
  const filterActive = chipKeys.some(k => (filters[k]?.size ?? 0) > 0);

  const filteredPairs = React.useMemo(() => {
    const pairs = data?.pairs ?? [];
    return pairs.filter(p =>
      (!filters.batches?.size || filters.batches.has(p.batch))
      && (!filters.subjects?.size || filters.subjects.has(p.subject))
      && (!filters.faculties?.size || filters.faculties.has(p.faculty)));
  }, [data, filters]);

  const removeFilter = (kind: string, v: string) =>
    setFilters(prev => {
      const next = new Set(prev[kind] ?? []);
      next.delete(v);
      return { ...prev, [kind]: next };
    });

  const resetFilters = () => setFilters({});

  const loadPairs = React.useCallback(async (q: number | null) => {
    setLoading(true);
    try {
      const res = await apiGet<TeacherPairsResponse>(
        q ? `/rost_max/api/teacher/grades?quarter=${q}` : '/rost_max/api/teacher/grades');
      setData(res);
      setQuarter(res.quarter);
    } catch {
      setData(null);
      addToast('Не удалось загрузить оценки', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  const loadStudents = React.useCallback(async (q: number, pair: TeacherPair) => {
    setLoading(true);
    try {
      const res = await apiGet<TeacherPairStudentsResponse>(
        `/rost_max/api/teacher/grades?quarter=${q}`
        + `&batch_id=${pair.batch_id}&subject_id=${pair.subject_id}`);
      setDetail(res);
      setLastPair(pair);
      setView('students');
    } catch {
      setDetail(null);
      addToast('Не удалось загрузить учеников', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  const loadStudent = React.useCallback(async (q: number, studentId: number) => {
    setLoading(true);
    try {
      const res = await apiGet<TeacherStudentResponse>(
        `/rost_max/api/teacher/grades?quarter=${q}&student_id=${studentId}`);
      setStudent(res);
    } catch {
      setStudent(null);
      addToast('Не удалось загрузить ученика', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  React.useEffect(() => { loadPairs(quarter); }, [loadPairs, quarter]);

  // --- содержимое --------------------------------------------------------
  const body = (() => {
    if (loading) return <Loading />;

    if (view === 'pairs') {
      if (!data) {
        return (
          <Div style={{ padding: 12 }}>
            <Button mode="outline" stretched onClick={() => loadPairs(quarter)}>Повторить</Button>
          </Div>
        );
      }
      if (data.pairs.length === 0) {
        return (
          <Box padding="m">
            <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
              За выбранную четверть уроков нет.
            </Caption>
          </Box>
        );
      }
      if (filteredPairs.length === 0) {
        return (
          <Box padding="m">
            <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
              Нет пар по выбранным фильтрам.
            </Caption>
          </Box>
        );
      }
      return (
        <Box padding="m" style={{ paddingTop: 10 }}>
          {filteredPairs.map(pair => (
            <PairCard
              key={`${pair.batch_id}-${pair.subject_id}`}
              pair={pair}
              onOpen={() => quarter && loadStudents(quarter, pair)}
            />
          ))}
        </Box>
      );
    }

    if (view === 'students') {
      if (!detail) return <Loading />;
      return (
        <Box padding="m">
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            {[
              { label: 'Уроков', value: String(detail.pair.total_classes) },
              { label: 'Посещаемость', value: `${Math.round(detail.pair.attendance_rate)}%` },
              { label: 'Средний балл', value: fmtAvg(detail.pair.average_mark) },
            ].map(item => (
              <div key={item.label} style={{
                flex: 1, background: 'var(--vkui--color_background_content)',
                borderRadius: 12, padding: 11, textAlign: 'center',
                boxShadow: '0 1px 3px rgba(0,0,0,.08)',
              }}>
                <Caption style={{
                  display: 'block', fontSize: 11, color: 'var(--vkui--color_text_secondary)',
                }}>
                  {item.label}
                </Caption>
                <Text weight="2" style={{ display: 'block', fontSize: 21, lineHeight: 1.1, marginTop: 5 }}>
                  {item.value}
                </Text>
              </div>
            ))}
          </div>
          {detail.students.length === 0 ? (
            <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
              Журнал этой пары пока не заполнен.
            </Caption>
          ) : detail.students.map(st => (
            <StudentRow
              key={st.id}
              student={st}
              onOpen={() => {
                setView('student');
                quarter && loadStudent(quarter, st.id);
              }}
            />
          ))}
        </Box>
      );
    }

    // экран карточки ученика
    if (!student) return <Loading />;
    if (student.subjects.length === 0) {
      return (
        <Box padding="m">
          <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
            За четверть у ученика нет оценок.
          </Caption>
        </Box>
      );
    }
    return (
      <Box padding="m">
        <Caption style={{ display: 'block', marginBottom: 8, color: 'var(--vkui--color_text_secondary)' }}>
          Мой предмет — можно открыть. Остальные — посмотреть, оценку не поставить.
        </Caption>
        {student.subjects.map(sub => (
          <SubjectCard
            key={sub.subject_id}
            subject={sub}
            onOpen={() => onOpenSubject?.(
              sub.subject_id, sub.name, student.student.id, student.student.name)}
          />
        ))}
      </Box>
    );
  })();

  return (
    <Panel id={id}>
      {view === 'pairs' && (
        <>
          <Box padding="m" style={{ paddingBottom: 0 }}>
            <Text weight="2" style={{ fontSize: 17 }}>Мои пары</Text>
          </Box>
          {data && (
            <QuarterBar
              quarters={data.quarters}
              value={quarter ?? data.quarter}
              onChange={setQuarter}
            />
          )}
          {/* Фильтры над лентой (мокап grades-filters.html): иконка слева,
              при активных фильтрах — подсвечена + чипы с «Сбросить». */}
          <Div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px 0' }}>
            <IconButton
              label="Фильтры"
              aria-expanded={filtersOpen}
              style={{
                color: filterActive
                  ? 'var(--vkui--color_text_accent)'
                  : 'var(--vkui--color_text_secondary)',
                flexShrink: 0, borderRadius: 12,
                border: '1px solid var(--vkui--color_separator_primary)',
                background: filterActive
                  ? 'var(--vkui--color_background_secondary)'
                  : undefined,
              }}
              onClick={() => {
                setSheetDraft(filters);
                setFiltersOpen(true);
              }}
            >
              <Icon24Filter />
            </IconButton>
            <FilterChipRow
              chips={chipKeys.flatMap(k =>
                [...(filters[k] ?? [])].map(v => ({ kind: k, v })))}
              onRemove={removeFilter}
              onReset={resetFilters}
            />
          </Div>
        </>
      )}
      {view === 'students' && detail && (
        <PanelHeader
          before={<PanelHeaderBack onClick={() => { setView('pairs'); }}>
            Назад
          </PanelHeaderBack>}
        >
          <PanelHeaderContent
            before={<SubjectAvatar subject={detail.pair.subject} color={detail.pair.subject_color} size={30} />}
            subtitle={detail.pair.faculty || undefined}
          >
            {detail.pair.subject}
          </PanelHeaderContent>
        </PanelHeader>
      )}
      {view === 'student' && student && (
        <PanelHeader
          before={<PanelHeaderBack onClick={() => { setStudent(null); setView('students'); }}>
            Назад
          </PanelHeaderBack>}
        >
          {student.student.name}
        </PanelHeader>
      )}
      {body}

      {/* Шторка фильтров «Моих пар» — общий ChipFilterModal
          (ModalPage рендерится в AppRoot-портал, поверх таббара). */}
      <ChipFilterModal
        open={filtersOpen}
        id="grades-pairs-filters"
        emptyText="За выбранную четверть пар нет — фильтровать нечего."
        sections={sheetSections}
        value={sheetDraft}
        footerOrder="cancel-first"
        onClose={() => setFiltersOpen(false)}
        onDraftChange={setSheetDraft}
        onApply={f => {
          setFilters(f);
          setFiltersOpen(false);
        }}
      />
    </Panel>
  );
};
