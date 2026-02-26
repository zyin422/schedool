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