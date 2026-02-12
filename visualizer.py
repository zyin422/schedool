def show_schedule_by_period(periods, teachers):
    print("\n" + "="*100)
    print("SCHEDULE BY PERIOD".center(100))
    print("="*100)
    
    for p in periods:
        print(f"\n{p.period_id}")
        print("-" * 100)
        
        for section in p.assigned_sections:
            classroom = section.assigned_classroom.name if section.assigned_classroom else "⚠️ NO ROOM"
            
            if section.assigned_teacher:
                teacher_name = section.assigned_teacher.name
                print(f"  {classroom:<15} │ {section.section_id:<20} │ {teacher_name}")
            else:
                # Find qualified teachers for this section
                qualified_teachers = [t for t in teachers if section.class_name in t.subjects]
                
                print(f"  {classroom:<15} │ {section.section_id:<20} │ ⚠️ NO TEACHER")
                if qualified_teachers:
                    print(f"      ↳ {len(qualified_teachers)} qualified teacher(s):")
                    for t in qualified_teachers:
                        print(f"         - {t.name}: teaching {t.assigned_count}/{t.max_sections} sections")
                else:
                    print(f"      ↳ ❌ No qualified teachers available for '{section.class_name}'")


def show_schedule_by_classroom(periods, sections):
    print("\n" + "="*100)
    print("SCHEDULE BY CLASSROOM".center(100))
    print("="*100)
    
    all_classrooms = set()
    for section in sections:
        if section.assigned_classroom:
            all_classrooms.add(section.assigned_classroom.name)
    
    for classroom_name in sorted(all_classrooms):
        print(f"\n{classroom_name}")
        print("-" * 100)
        
        for p in periods:
            section = next((s for s in p.assigned_sections 
                          if s.assigned_classroom and s.assigned_classroom.name == classroom_name), None)
            if section:
                teacher = section.assigned_teacher.name if section.assigned_teacher else "⚠️ NO TEACHER"
                print(f"  {p.period_id:<12} │ {section.section_id:<20} │ {teacher}")
            else:
                print(f"  {p.period_id:<12} │ {'[Free]':<20} │")


def show_teacher_utilization(sections):
    print("\n" + "="*100)
    print("TEACHER UTILIZATION")
    print("-" * 100)
    
    teacher_loads = {}
    for section in sections:
        if section.assigned_teacher:
            teacher = section.assigned_teacher
            name = teacher.name
            if name not in teacher_loads:
                teacher_loads[name] = {
                    'assigned': 0, 
                    'max': teacher.max_sections,
                    'subjects': teacher.subjects
                }
            teacher_loads[name]['assigned'] += 1
    
    for name, load in sorted(teacher_loads.items()):
        pct = (load['assigned'] / load['max']) * 100
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        subjects = ", ".join(sorted(load['subjects']))
        
        print(f"  {name:<20} {bar} {load['assigned']}/{load['max']} ({pct:.0f}%) | {subjects}")


def show_classroom_utilization(periods):
    print("\n" + "="*100)
    print("CLASSROOM UTILIZATION")
    print("-" * 100)
    
    room_usage = {}
    for p in periods:
        for section in p.assigned_sections:
            if section.assigned_classroom:
                room = section.assigned_classroom.name
                room_usage[room] = room_usage.get(room, 0) + 1
    
    for room, count in sorted(room_usage.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * count + "░" * (len(periods) - count)
        print(f"  {room:<20} {bar} {count}/{len(periods)}")


def show_summary(sections):
    print("\n" + "="*100)
    print("SUMMARY")
    print("-" * 100)
    
    total_sections = len(sections)
    assigned_sections = len([s for s in sections if s.is_fully_assigned()])
    print(f"  ✓ Fully assigned: {assigned_sections}/{total_sections}")
    print(f"  ✗ Unassigned: {total_sections - assigned_sections}/{total_sections}")
    
    unassigned = [s for s in sections if not s.is_fully_assigned()]
    if unassigned:
        print("\n⚠️  UNASSIGNED SECTIONS:")
        print("-" * 100)
        for s in unassigned:
            missing = []
            if not s.assigned_teacher: missing.append("teacher")
            if not s.assigned_classroom: missing.append("classroom")
            print(f"  - {s.section_id:<20} needs: {', '.join(missing)}")


def visualize_schedule(periods, sections, teachers):
    show_schedule_by_period(periods, teachers)
    # show_schedule_by_classroom(periods, sections)
    show_teacher_utilization(sections)
    # show_classroom_utilization(periods)
    show_summary(sections)