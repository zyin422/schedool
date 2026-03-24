"""
Flask web interface for the school scheduler with soft constraints support.
"""
import os
import csv
import io
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
from scheduler import (
    Classroom, Class, Teacher, Section, Period,
    run_scheduler, generate_multiple_schedules
)
from visualizer import visualize_schedule
from constraints import Constraint, get_constraint_display_name, get_constraint_parameters_schema
from scoring import calculate_score, rank_schedules, get_top_n_schedules

app = Flask(__name__)
app.secret_key = 'schedool-secret-key-change-in-production'

# Store last results in memory
last_schedule_result = {
    'output': '',
    'success': False,
    'top_schedules': [],
    'constraints': []
}


def parse_csv_file(file_content):
    """Parse CSV content and return list of dictionaries"""
    reader = csv.DictReader(io.StringIO(file_content))
    data = []
    for row in reader:
        cleaned_row = {k.strip(): v.strip() for k, v in row.items()}
        data.append(cleaned_row)
    return data


def load_data_from_csv(classrooms_csv, classes_csv, teachers_csv, periods_csv):
    """Load scheduler data from CSV file contents"""
    # Parse classrooms
    classrooms = []
    classroom_data = parse_csv_file(classrooms_csv)
    for row in classroom_data:
        purposes = set(p.strip() for p in row['purposes'].split(','))
        classrooms.append(Classroom(
            name=row['name'],
            size=int(row['size']),
            purposes=purposes
        ))
    
    # Parse classes
    classes = []
    class_data = parse_csv_file(classes_csv)
    for row in class_data:
        classes.append(Class(
            name=row['name'],
            num_sections=int(row['num_sections']),
            required_classroom_type=row['required_classroom_type']
        ))
    
    # Parse teachers
    teachers = []
    teacher_data = parse_csv_file(teachers_csv)
    for row in teacher_data:
        subjects = set(s.strip() for s in row['subjects'].split(','))
        teachers.append(Teacher(
            name=row['name'],
            subjects=subjects,
            max_sections=int(row['max_sections']),
            assigned_count=0
        ))
    
    # Parse periods
    periods = []
    period_data = parse_csv_file(periods_csv)
    for row in period_data:
        periods.append(Period(period_id=row['period_id']))
    
    # classroom_types is derived from unique purposes
    classroom_types = set()
    for c in classrooms:
        classroom_types.update(c.purposes)
    
    # class_list is just a list of class names
    class_list = [c.name for c in classes]
    
    return classroom_types, classrooms, class_list, classes, teachers, periods


def run_scheduler_and_capture_output(classroom_types, classrooms, class_list, classes, teachers, periods):
    """Run the scheduler and capture the output"""
    import sys
    from io import StringIO
    
    old_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = captured_output
    
    try:
        sections = run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods)
        visualize_schedule(periods, sections, teachers)
    finally:
        sys.stdout = old_stdout
    
    output = captured_output.getvalue()
    fully_assigned = sum(1 for s in sections if s.is_fully_assigned())
    success = fully_assigned == len(sections)
    
    return output, success


def run_multiple_schedules_with_constraints(classroom_types, classrooms, class_list, classes, teachers, periods, constraints, num_schedules=50):
    """Generate multiple schedules, score them, return top 3"""
    import sys
    from io import StringIO
    
    # Generate multiple schedules
    schedule_results = generate_multiple_schedules(
        classroom_types, classrooms, class_list, classes, teachers, periods, num_schedules
    )
    
    scored_schedules = []
    
    for schedule_data in schedule_results:
        # Capture output for this schedule
        old_stdout = sys.stdout
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            visualize_schedule(schedule_data['periods'], schedule_data['sections'], schedule_data['teachers'])
        finally:
            sys.stdout = old_stdout
        
        output = captured_output.getvalue()
        
        # Score the schedule
        score_result = calculate_score(schedule_data['periods'], schedule_data['sections'], constraints)
        
        scored_schedules.append({
            'seed': schedule_data['seed'],
            'sections': schedule_data['sections'],
            'periods': schedule_data['periods'],
            'teachers': schedule_data['teachers'],
            'output': output,
            'score': score_result
        })
    
    # Rank and get top 3
    top_3 = get_top_n_schedules(scored_schedules, 3)
    
    return top_3


@app.route('/')
def index():
    """Main page with upload form"""
    return render_template('index.html')


@app.route('/run', methods=['POST'])
def run_scheduler_web():
    """Run the scheduler with uploaded CSV files"""
    global last_schedule_result
    
    if 'classrooms' not in request.files or 'classes' not in request.files:
        flash('Please upload both classrooms and classes CSV files', 'error')
        return redirect(url_for('index'))
    
    classrooms_file = request.files['classrooms']
    classes_file = request.files['classes']
    teachers_file = request.files.get('teachers')
    periods_file = request.files.get('periods')
    
    generate_multiple = request.form.get('generate_multiple') == 'on'
    
    default_teachers = """name,subjects,max_sections
Teacher-Math,Math,5
Teacher-English,English,5
Teacher-Science,Science,5
Teacher-Art,Art,5"""
    
    default_periods = """period_id
P1
P2
P3
P4
P5"""
    
    try:
        classroom_types, classrooms, class_list, classes, teachers, periods = load_data_from_csv(
            classrooms_file.read().decode('utf-8'),
            classes_file.read().decode('utf-8'),
            teachers_file.read().decode('utf-8') if teachers_file and teachers_file.filename else default_teachers,
            periods_file.read().decode('utf-8') if periods_file and periods_file.filename else default_periods
        )        # Store data for constraint management
        session["available_teachers"] = [t.name for t in teachers]
        session["available_rooms"] = [c.name for c in classrooms]
        session["available_classes"] = [c.name for c in classes]
        session["available_periods"] = [p.period_id for p in periods]
        
        if generate_multiple:
            # Get constraints from session
            constraints_data = session.get('constraints', [])
            constraints = [Constraint.from_dict(c) for c in constraints_data]
            
            # Run multiple schedules with scoring
            top_schedules = run_multiple_schedules_with_constraints(
                classroom_types, classrooms, class_list, classes, teachers, periods, constraints
            )
            
            last_schedule_result['top_schedules'] = top_schedules
            last_schedule_result['constraints'] = constraints_data
            
            return redirect(url_for('results_multi'))
        else:
            # Run single schedule (original behavior)
            output, success = run_scheduler_and_capture_output(
                classroom_types, classrooms, class_list, classes, teachers, periods
            )
            
            last_schedule_result['output'] = output
            last_schedule_result['success'] = success
            last_schedule_result['top_schedules'] = []
            
            return redirect(url_for('results'))
        
    except Exception as e:
        flash(f'Error running scheduler: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/results')
def results():
    """Display single scheduler result"""
    return render_template('results.html', 
                          output=last_schedule_result['output'],
                          success=last_schedule_result['success'])


@app.route('/results_multi')
def results_multi():
    """Display multiple scheduler results with scores"""
    return render_template('results_multi.html',
                          top_schedules=last_schedule_result['top_schedules'],
                          constraints=last_schedule_result['constraints'])


@app.route('/constraints', methods=['GET', 'POST'])
def manage_constraints():
    """Add and manage soft constraints"""
    if request.method == 'POST':
        constraint_type = request.form.get('constraint_type')
        weight = int(request.form.get('weight', 5))
        applies_to = request.form.get('applies_to')
        
        # Build parameters based on constraint type
        parameters = {}
        
        if constraint_type == 'teacher_morning_pref':
            parameters['preferred_periods'] = request.form.getlist('preferred_morning')
        elif constraint_type == 'teacher_afternoon_pref':
            parameters['preferred_periods'] = request.form.getlist('preferred_afternoon')
        elif constraint_type == 'room_unavailable':
            parameters['blocked_period'] = request.form.get('blocked_period')
        elif constraint_type == 'max_consecutive':
            parameters['max_consecutive'] = int(request.form.get('max_consecutive', 3))
        
        constraint = Constraint(
            constraint_type=constraint_type,
            weight=weight,
            applies_to=applies_to,
            parameters=parameters
        )
        
        # Add to session
        constraints = session.get('constraints', [])
        constraints.append(constraint.to_dict())
        session['constraints'] = constraints
        
        flash(f'Added constraint: {get_constraint_display_name(constraint_type)}', 'success')
    
    # Get teachers, rooms, classes for dropdown population
    teachers = session.get('available_teachers', [])
    rooms = session.get('available_rooms', [])
    classes = session.get('available_classes', [])
    
    return render_template('constraints.html',
                          constraints=session.get('constraints', []),
                          teachers=teachers,
                          rooms=rooms,
                          classes=classes)


@app.route('/constraints/remove/<constraint_id>')
def remove_constraint(constraint_id):
    """Remove a constraint"""
    constraints = session.get('constraints', [])
    constraints = [c for c in constraints if c.get('id') != constraint_id]
    session['constraints'] = constraints
    
    flash('Constraint removed', 'success')
    return redirect(url_for('manage_constraints'))


@app.route('/constraints/clear')
def clear_constraints():
    """Clear all constraints"""
    session['constraints'] = []
    flash('All constraints cleared', 'success')
    return redirect(url_for('manage_constraints'))


@app.route('/set_data', methods=['POST'])
def set_data_for_constraints():
    """Store teacher/room/class data for constraint form dropdowns"""
    classroom_types, classrooms, class_list, classes, teachers, periods = load_data_from_csv(
        request.form.get('classrooms'),
        request.form.get('classes'),
        request.form.get('teachers'),
        request.form.get('periods')
    )
    
    session['available_teachers'] = [t.name for t in teachers]
    session['available_rooms'] = [c.name for c in classrooms]
    session['available_classes'] = [c.name for c in classes]
    
    return redirect(url_for('manage_constraints'))



@app.route('/upload_data', methods=['POST'])
def upload_data():
    """Upload CSV files and store data in session"""
    global last_schedule_result
    
    if 'classrooms' not in request.files or 'classes' not in request.files:
        flash('Please upload both classrooms and classes CSV files', 'error')
        return redirect(url_for('index'))
    
    classrooms_file = request.files['classrooms']
    classes_file = request.files['classes']
    teachers_file = request.files.get('teachers')
    periods_file = request.files.get('periods')
    
    action = request.form.get('action', 'upload')
    
    default_teachers = """name,subjects,max_sections
Teacher-Math,Math,5
Teacher-English,English,5
Teacher-Science,Science,5
Teacher-Art,Art,5"""
    
    default_periods = """period_id
P1
P2
P3
P4
P5"""
    
    try:
        classroom_types, classrooms, class_list, classes, teachers, periods = load_data_from_csv(
            classrooms_file.read().decode('utf-8'),
            classes_file.read().decode('utf-8'),
            teachers_file.read().decode('utf-8') if teachers_file and teachers_file.filename else default_teachers,
            periods_file.read().decode('utf-8') if periods_file and periods_file.filename else default_periods
        )
        
        # Store data objects in session (serializable versions of scheduler objects)
        # Store as dicts so they can be reconstructed
        session['stored_classrooms'] = [
            {'name': c.name, 'size': c.size, 'purposes': list(c.purposes)}
            for c in classrooms
        ]
        session['stored_classes'] = [
            {'name': c.name, 'num_sections': c.num_sections, 'required_classroom_type': c.required_classroom_type}
            for c in classes
        ]
        session['stored_teachers'] = [
            {'name': t.name, 'subjects': list(t.subjects), 'max_sections': t.max_sections}
            for t in teachers
        ]
        session['stored_periods'] = [{'period_id': p.period_id} for p in periods]
        session['stored_classroom_types'] = list(classroom_types)
        
        # Also store display-friendly data for UI
        session['available_teachers'] = [t.name for t in teachers]
        session['available_rooms'] = [c.name for c in classrooms]
        session['available_classes'] = [c.name for c in classes]
        session['available_periods'] = [p.period_id for p in periods]
        
        flash('Data loaded! You can now manage constraints or run the scheduler.', 'success')
        
        if action == 'run':
            generate_multiple = request.form.get('generate_multiple') == 'on'
            constraints_data = session.get('constraints', [])
            constraints = [Constraint.from_dict(c) for c in constraints_data]
            
            if generate_multiple:
                top_schedules = run_multiple_schedules_with_constraints(
                    classroom_types, classrooms, class_list, classes, teachers, periods, constraints
                )
                last_schedule_result['top_schedules'] = top_schedules
                last_schedule_result['constraints'] = constraints_data
                return redirect(url_for('results_multi'))
            else:
                output, success = run_scheduler_and_capture_output(
                    classroom_types, classrooms, class_list, classes, teachers, periods
                )
                last_schedule_result['output'] = output
                last_schedule_result['success'] = success
                return redirect(url_for('results'))
        
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/run_scheduler', methods=['POST'])
def run_scheduler_stored():
    """Run the scheduler using stored data from session"""
    global last_schedule_result
    
    # Check if data is stored in session
    if not session.get('stored_classes'):
        flash('No data stored. Please upload CSV files first.', 'error')
        return redirect(url_for('index'))
    
    generate_multiple = request.form.get('generate_multiple') == 'on'
    
    try:
        # Reconstruct scheduler objects from stored data
        classrooms = [Classroom(name=c['name'], size=c['size'], purposes=set(c['purposes'])) for c in session.get('stored_classrooms', [])]
        classes = [Class(name=c['name'], num_sections=c['num_sections'], required_classroom_type=c['required_classroom_type']) for c in session.get('stored_classes', [])]
        teachers = [Teacher(name=t['name'], subjects=set(t['subjects']), max_sections=t['max_sections'], assigned_count=0) for t in session.get('stored_teachers', [])]
        periods = [Period(period_id=p['period_id']) for p in session.get('stored_periods', [])]
        classroom_types = set(session.get('stored_classroom_types', []))
        class_list = [c['name'] for c in session.get('stored_classes', [])]
        
        # Get constraints from session
        constraints_data = session.get('constraints', [])
        constraints = [Constraint.from_dict(c) for c in constraints_data]
        
        if generate_multiple:
            top_schedules = run_multiple_schedules_with_constraints(
                classroom_types, classrooms, class_list, classes, teachers, periods, constraints
            )
            last_schedule_result['top_schedules'] = top_schedules
            last_schedule_result['constraints'] = constraints_data
            return redirect(url_for('results_multi'))
        else:
            output, success = run_scheduler_and_capture_output(
                classroom_types, classrooms, class_list, classes, teachers, periods
            )
            last_schedule_result['output'] = output
            last_schedule_result['success'] = success
            last_schedule_result['top_schedules'] = []
            return redirect(url_for('results'))
    
    except Exception as e:
        flash(f'Error running scheduler: {str(e)}', 'error')
        return redirect(url_for('index'))


if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
