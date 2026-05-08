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
    run_scheduler
)
from visualizer import visualize_schedule

app = Flask(__name__)
app.secret_key = 'schedool-secret-key-change-in-production'

# Store last results in memory
last_schedule_result = {
    'output': '',
    'success': False,
    'priority_order': []
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


def run_scheduler_and_capture_output(classroom_types, classrooms, class_list, classes, teachers, periods, sections=None):
    """Run the scheduler and capture the output"""
    import sys
    from io import StringIO

    old_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = captured_output

    priority_order = []
    try:
        run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods, sections, priority_order)
        visualize_schedule(periods, sections, teachers)
    finally:
        sys.stdout = old_stdout

    output = captured_output.getvalue()
    fully_assigned = sum(1 for s in sections if s.is_fully_assigned())
    success = fully_assigned == len(sections)

    return output, success, priority_order


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
        
        # Run single schedule
        output, success = run_scheduler_and_capture_output(
            classroom_types, classrooms, class_list, classes, teachers, periods, sections
        )
        
        last_schedule_result['output'] = output
        last_schedule_result['success'] = success
        
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
    return redirect(url_for('index'))


@app.route('/clear_preassignments', methods=['POST'])
def clear_preassignments():
    """Clear all pre-assignments"""
    session['preassignments'] = []
    flash('All pre-assignments cleared', 'success')
    return redirect(url_for('index'))



@app.route('/set_preassignments', methods=['POST'])
def set_preassignments():
    """Store pre-assignments for sections"""
    try:
        # Get form data
        section_ids = request.form.getlist('sections')
        teacher_names = request.form.getlist('teachers')
        classroom_names = request.form.getlist('classrooms')
        
        # Validate
        if not section_ids:
            flash('Please select at least one section for pre-assignment.', 'error')
            return redirect(url_for('index'))
        
        # Build pre-assignments list
        preassignments = []
        for i, section_id in enumerate(section_ids):
            teacher_name = teacher_names[i] if i < len(teacher_names) and teacher_names[i] else None
            classroom_name = classroom_names[i] if i < len(classroom_names) and classroom_names[i] else None
            
            # Only add if there's at least one pre-assignment
            if teacher_name or classroom_name:
                preassignments.append({
                    'section': section_id,
                    'teacher': teacher_name,
                    'classroom': classroom_name
                })
        
        # Store in session
        session['preassignments'] = preassignments
        flash(f'Saved {len(preassignments)} pre-assignment(s)!', 'success')
        
    except Exception as e:
        flash(f'Error saving pre-assignments: {str(e)}', 'error')
    
    return redirect(url_for('index'))



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
        
        flash('Data loaded! You can now run the scheduler.', 'success')
        
        if action == 'run':
            output, success, priority_order = run_scheduler_and_capture_output(
                classroom_types, classrooms, class_list, classes, teachers, periods, sections
            )
            last_schedule_result['output'] = output
            last_schedule_result['success'] = success
            last_schedule_result['priority_order'] = priority_order
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
    
    try:
        # Reconstruct scheduler objects from stored data
        classrooms = [Classroom(name=c['name'], size=c['size'], purposes=set(c['purposes'])) for c in session.get('stored_classrooms', [])]
        classes = [Class(name=c['name'], num_sections=c['num_sections'], required_classroom_type=c['required_classroom_type']) for c in session.get('stored_classes', [])]
        teachers = [Teacher(name=t['name'], subjects=set(t['subjects']), max_sections=t['max_sections'], assigned_count=0) for t in session.get('stored_teachers', [])]
        periods = [Period(period_id=p['period_id']) for p in session.get('stored_periods', [])]
        classroom_types = set(session.get('stored_classroom_types', []))
        class_list = [c['name'] for c in session.get('stored_classes', [])]
        
        # Get pre-assignments from session
        preassignments = session.get('preassignments', [])
        
        # Create lookup dictionaries for teachers and classrooms
        teacher_dict = {t.name: t for t in teachers}
        classroom_dict = {c.name: c for c in classrooms}
        
        # Generate sections with pre-assignments
        sections = []
        order = 0
        for cls in classes:
            for i in range(cls.num_sections):
                section_id = f"{cls.name}-{i+1}"

                # Check if this section has pre-assignments
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
                    preassigned_classroom=preassigned_classroom,
                    order=order
                ))
                order += 1
        
        output, success, priority_order = run_scheduler_and_capture_output(
            classroom_types, classrooms, class_list, classes, teachers, periods, sections
        )
        last_schedule_result['output'] = output
        last_schedule_result['success'] = success
        last_schedule_result['priority_order'] = priority_order
        return redirect(url_for('results'))
    
    except Exception as e:
        import traceback
        flash(f'Error running scheduler: {str(e)}', 'error')
        print(f"DEBUG ERROR: {traceback.format_exc()}")
        return redirect(url_for('index'))


if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
