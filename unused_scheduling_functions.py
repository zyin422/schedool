def solve_recursive(ctx: SchedulingContext, section_index: int = 0) -> bool:
    """
    Phase 3: Recursive backtracking solver over ctx.all_sections (already prioritized).
    This assigns teachers only (rooms are assumed assigned and recorded in ctx.room_schedule).
    Returns True if a full assignment is found, False if unsolvable with current domains.
    """
    # BASE CASE: all sections processed
    if section_index >= len(ctx.all_sections):
        return True

    section = ctx.all_sections[section_index]
    # locate the period this section was assigned to
    period = next((p for p in ctx.periods if section in p.assigned_sections), None)
    if period is None:
        # section has no period assigned -> cannot proceed
        return False
    p_id = period.period_id

    # Try every valid teacher for this section (order from precomputed domain)
    for teacher in ctx.valid_teachers.get(section.section_id, []):
        # teacher must be free in this period and below max load
        if ctx.teacher_schedule[teacher.name][p_id] is None and ctx.teacher_load[teacher.name] < teacher.max_sections:
            # Choose
            section.assigned_teacher = teacher
            ctx.teacher_schedule[teacher.name][p_id] = section
            ctx.teacher_load[teacher.name] += 1

            # Recurse
            if solve_recursive(ctx, section_index + 1):
                return True

            # Backtrack
            section.assigned_teacher = None
            ctx.teacher_schedule[teacher.name][p_id] = None
            ctx.teacher_load[teacher.name] -= 1

    # No teacher led to a solution for this section -> fail
    return False

def assign_sections_to_periods(sections, periods, classroom_types):
    # assign sections to periods (round-robin by classroom type priority)
    period_idx = 0
    for c_type in classroom_types:
        for section in sections:
            if section.required_classroom_type != c_type:
                continue
            periods[period_idx % len(periods)].assigned_sections.append(section)
            period_idx += 1


def assign_classrooms_to_sections(periods, classrooms, classroom_types, ctx: SchedulingContext):
    """
    Assign rooms using precomputed ctx.valid_rooms and update ctx.room_schedule
    so room availability is tracked in the SchedulingContext scoreboard.
    """
    for p in periods:
        used_room_names = set()
        for section in p.assigned_sections:
            # iterate only over rooms known to be compatible for this section
            for room in ctx.valid_rooms.get(section.section_id, []):
                # skip if this room already used in this period
                if room.name in used_room_names:
                    continue
                # respect scoreboard (should be None if free)
                if ctx.room_schedule.get(room.name, {}).get(p.period_id) is not None:
                    used_room_names.add(room.name)
                    continue
                # assign
                section.assigned_classroom = room
                ctx.room_schedule[room.name][p.period_id] = section
                used_room_names.add(room.name)
                break


def assign_teachers_to_sections(ctx: SchedulingContext):
    # assign teachers using precomputed domains and the scoreboard
    for p in ctx.periods:
        for section in p.assigned_sections:
            # skip if already assigned
            if section.assigned_teacher:
                # ensure scoreboard reflects this pre-assignment if necessary
                teacher = section.assigned_teacher
                if isinstance(teacher, Teacher):
                    ctx.teacher_schedule[teacher.name][p.period_id] = section
                    ctx.teacher_load[teacher.name] += 1
                continue

            # 1) Try to assign any qualified teacher who is free in this period and below max load
            for t in ctx.valid_teachers[section.section_id]:
                if ctx.teacher_schedule[t.name][p.period_id] is None and ctx.teacher_load[t.name] < t.max_sections:
                    section.assigned_teacher = t
                    ctx.teacher_schedule[t.name][p.period_id] = section
                    ctx.teacher_load[t.name] += 1
                    break

            if section.assigned_teacher:
                continue

            # 2) Swap logic (single-level): for each qualified teacher who is busy in this period,
            #    inspect their conflicting section and try to find an alternate who is free this period.
            for qt in ctx.valid_teachers[section.section_id]:
                # only consider teachers who are actually busy in this period
                conflicting_section = ctx.teacher_schedule[qt.name][p.period_id]
                if conflicting_section is None:
                    continue

                # look for an alternate for the conflicting_section
                for alt in ctx.valid_teachers[conflicting_section.section_id]:
                    if alt.name == qt.name:
                        continue
                    # alternate must be free in this period and below max load
                    if ctx.teacher_schedule[alt.name][p.period_id] is None and ctx.teacher_load[alt.name] < alt.max_sections:
                        # perform swap:
                        # assign alt -> conflicting_section
                        conflicting_section.assigned_teacher = alt
                        ctx.teacher_schedule[alt.name][p.period_id] = conflicting_section
                        ctx.teacher_load[alt.name] += 1

                        # free qt for this period (remove their assignment)
                        ctx.teacher_schedule[qt.name][p.period_id] = None
                        ctx.teacher_load[qt.name] -= 1

                        # assign qt -> blocked section
                        section.assigned_teacher = qt
                        ctx.teacher_schedule[qt.name][p.period_id] = section
                        ctx.teacher_load[qt.name] += 1

                        # stop after first successful single-level swap
                        break

                if section.assigned_teacher:
                    break

            if not section.assigned_teacher:
                # Could not assign or swap — leave unassigned and warn
                print(f"⚠️ Unassigned after swap attempts: {section.section_id} in period {p.period_id}")
