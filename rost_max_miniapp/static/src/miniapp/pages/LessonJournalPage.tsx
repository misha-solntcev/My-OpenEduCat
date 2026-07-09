import React from 'react';
import { Flex, Typography } from '@maxhub/max-ui';
import { apiGet, apiPost } from '../api';

interface Student {
  id: number;
  name: string;
  grade?: string;
}

interface StudentsResponse {
  students: Student[];
}

interface LessonJournalPageProps {
  lessonId: number;
  lessonTitle: string;
  onBack: () => void;
}

export const LessonJournalPage: React.FC<LessonJournalPageProps> = ({ lessonId, lessonTitle, onBack }) => {
  const [students, setStudents] = React.useState<Student[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    apiGet<StudentsResponse>(`/rost_max/api/lesson/${lessonId}/students`)
      .then(data => {
        setStudents(data.students || []);
      })
      .catch(() => setStudents([]))
      .finally(() => setLoading(false));
  }, [lessonId]);

  const handleSetGrade = (studentId: number, currentGrade: string) => {
    const grades = ['', '5', '4', '3', '2', 'Н'];
    const nextIndex = (grades.indexOf(currentGrade) + 1) % grades.length;
    const nextGrade = grades[nextIndex];

    setStudents(prev => prev.map(s => s.id === studentId ? { ...s, grade: nextGrade } : s));
    apiPost('/rost_max/api/set_grade', { student_id: studentId, lesson_id: lessonId, grade: nextGrade });
  };

  if (loading) {
    return (
      <Flex direction="column" gap={16} style={{ width: '100%' }}>
        <Flex align="center" gap={12}>
          <button onClick={onBack} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#007aff', padding: '4px 8px 4px 0' }}>
            ⬅
          </button>
          <Typography.Title level={4} style={{ margin: 0, fontWeight: 700 }}>
            {lessonTitle}
          </Typography.Title>
        </Flex>
        <div style={{ textAlign: 'center', padding: '40px' }}>Загрузка...</div>
      </Flex>
    );
  }

  return (
    <Flex direction="column" gap={16} style={{ width: '100%', paddingBottom: '80px' }}>
      <Flex align="center" gap={12}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#007aff', padding: '4px 8px 4px 0' }}>
          ⬅
        </button>
        <Typography.Title level={4} style={{ margin: 0, fontWeight: 700 }}>
          {lessonTitle}
        </Typography.Title>
      </Flex>

      <div style={{ backgroundColor: 'var(--background-surface-card)', borderRadius: '12px', border: '1px solid var(--border-neutral-subtle)', overflow: 'hidden' }}>
        {students.map((student, index) => (
          <div 
            key={student.id}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between', 
              padding: '12px 16px',
              borderBottom: index < students.length - 1 ? '1px solid var(--border-neutral-subtle)' : 'none'
            }}
          >
            <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-default)' }}>
              {index + 1}. {student.name}
            </span>

            <button
              onClick={() => handleSetGrade(student.id, student.grade || '')}
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                border: 'none',
                backgroundColor: 
                  student.grade === '5' ? '#34c75920' : 
                  student.grade === '4' ? '#34c75910' : 
                  student.grade === '3' ? '#ff950015' :
                  student.grade === '2' ? '#ff3b3015' :
                  student.grade === 'Н' ? '#ff3b3030' : 'var(--background-neutral-subtle, #f2f2f7)',
                color: 
                  student.grade === '5' || student.grade === '4' ? '#34c759' : 
                  student.grade === '3' ? '#ff9500' : 
                  student.grade === '2' || student.grade === 'Н' ? '#ff3b30' : 'var(--text-muted)',
                fontWeight: 700,
                fontSize: '15px',
                cursor: 'pointer'
              }}
            >
              {student.grade || '—'}
            </button>
          </div>
        ))}
      </div>
    </Flex>
  );
};