#!/usr/bin/env python3
"""Test script for pre-assignment feature."""

import sys
from scheduler import Classroom, Class, Teacher, Period, Section, run_scheduler

def test_preassignment_flow():
    classrooms = [
        Classroom('Room-101', 30, {'General'}),
        Classroom('Room-102', 30, {'General'}),
    ]
    classes = [
        Class('Math', 2, 'General'),
        Class('English', 2, 'General'),
    ]
    teachers = [
        Teacher('Teacher-Math', {'Math'}, 5, 0),
        Teacher('Teacher-English', {'English'}, 5, 0),
    ]
    periods = [Period('P1'), Period('P2'), Period('P3'), Period('P4'), Period('P5')]
    
    preassignments = [
        {'section': 'Math-1', 'teacher': 'Teacher-Math', 'classroom': None},
        {'section': 'English-1', 'teacher': None, 'classroom': 'Room-101'},
    ]
    
    teacher_dict = {t.name: t for t in teachers}
    classroom_dict = {c.name: c for c in classrooms}
    
    sections = []
    for cls in classes:
        for i in range(cls.num_sections):
            section_id = f"{cls.name}-{i+1}"
            preassigned_teacher = None
            preassigned_classroom = None
            
            for pa in preassignments:
                if pa['section'] == section_id:
                    if pa['teacher'] and pa['teacher'] in teacher_dict:
                        preassigned_teacher = teacher_dict[pa['teacher']]
                    if pa['classroom'] and pa['classroom'] in classroom_dict:
                        preassigned_classroom = classroom_dict[pa['classroom']]
                    break
            
            sections.append(Section(
                section_id=section_id,
                class_name=cls.name,
                required_classroom_type=cls.required_classroom_type,
                preassigned_teacher=preassigned_teacher,
                preassigned_classroom=preassigned_classroom
            ))
    
    print("Sections with pre-assignments:")
    for s in sections:
        pa_teacher = s.preassigned_teacher.name if s.preassigned_teacher else None
        pa_classroom = s.preassigned_classroom.name if s.preassigned_classroom else None
        print(f"  {s.section_id}: preassigned_teacher={pa_teacher}, preassigned_classroom={pa_classroom}")
    
    print("\nRunning scheduler...")
    result = run_scheduler({'General'}, classrooms, ['Math', 'English'], classes, teachers, periods, sections)
    
    print("\nFinal schedule:")
    for p in periods:
        if p.assigned_sections:
            print(f"\n{p.period_id}:")
            for s in p.assigned_sections:
                print(f"  {s.section_id}: teacher={s.assigned_teacher.name if s.assigned_teacher else 'UNASSIGNED'}, room={s.assigned_classroom.name if s.assigned_classroom else 'UNASSIGNED'}")
    
    print("\nVerifying pre-assignments:")
    errors = []
    for s in result:
        if s.section_id == 'Math-1':
            if s.preassigned_teacher and s.assigned_teacher != s.preassigned_teacher:
                errors.append(f"Math-1 teacher mismatch")
            elif s.preassigned_teacher:
                print(f"  ✓ Math-1 teacher: {s.assigned_teacher.name}")
        if s.section_id == 'English-1':
            if s.preassigned_classroom and s.assigned_classroom != s.preassigned_classroom:
                errors.append(f"English-1 classroom mismatch: expected {s.preassigned_classroom.name}, got {s.assigned_classroom.name if s.assigned_classroom else None}")
            elif s.preassigned_classroom:
                print(f"  ✓ English-1 classroom: {s.assigned_classroom.name}")
    
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  ✗ {e}")
        return False
    else:
        print("\n✓ All pre-assignments respected!")
        return True

if __name__ == '__main__':
    success = test_preassignment_flow()
    sys.exit(0 if success else 1)
