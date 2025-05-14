from io import BytesIO
from datetime import datetime, timedelta
from flask import Flask, render_template, flash, redirect, session, url_for, request, Response,send_file
from forms import SignupForm, LoginForm
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
import csv




app = Flask(__name__)
app.config["SECRET_KEY"] = "007"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app_user.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True

db = SQLAlchemy(app)

class PatientFile(db.Model):
    __tablename__ = "patient_file"

    patient_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    gender = db.Column(db.String(), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # Foreign key linking to the DoctorFile
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor_file.doctor_id'), nullable=True)

    # Relationship with treatment (one patient can have many treatments)
    treatment = db.relationship("TreatmentFile", backref="patient", lazy=True)

    # Relationship with Upload (one patient can have many uploads)
    uploads = db.relationship("Upload", backref="patient", lazy=True)


class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(50))
    time = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(db.LargeBinary)

    # Foreign key linking to PatientFile
    patient_id = db.Column(db.Integer, db.ForeignKey('patient_file.patient_id'), nullable=False)

class TreatmentFile(db.Model):
    __tablename__ = "treatment_file"

    treatment_id = db.Column(db.Integer, primary_key=True)
    diagnosis = db.Column(db.String(200), nullable=False)  # Corrected 'diagonis' to 'diagnosis'
    report_path = db.Column(db.String(200), nullable=False)

    patient_id = db.Column(db.Integer, db.ForeignKey('patient_file.patient_id'), nullable=False)

class AdminFile(db.Model):
    __tablename__ = "admin_file"

    admin_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)  # Changed to String
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=False)

class DoctorFile(db.Model):
    __tablename__ = "doctor_file"

    doctor_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.Integer, unique=True, nullable=False)
    specialist = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # Relationship to patients (One doctor can have many patients)
    patients = db.relationship("PatientFile", backref="doctor", lazy=True)


class AppointmentFile(db.Model):
    __tablename__ = "appointment_file"

    appointment_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient_file.patient_id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor_file.doctor_id'), nullable=False)
    appointment_time = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(200), nullable=True)

    # Relationships
    patient = db.relationship("PatientFile", backref="appointments", lazy=True)
    doctor = db.relationship("DoctorFile", backref="appointments", lazy=True)





@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")

@app.route('/generate_csv')
def generate_csv():
    # Create a CSV in memory
    output = []
    output.append(['Name', 'Score'])
    output.append(['Alice', 95])
    output.append(['Bob', 89])
    
    # Convert list to CSV
    response = Response(
        '\n'.join([','.join(map(str, row)) for row in output]),
        mimetype='text/csv'
    )
    response.headers["Content-Disposition"] = "attachment;filename=report.csv"
    return response

@app.route("/sign", methods=["GET", "POST"])
def sign():
    form = SignupForm()  
    if form.validate_on_submit():
        # Check if the email is already registered
        existing_user = PatientFile.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for('log'))
        
        # Hash the password and create a new user
        hashed_password = generate_password_hash(form.password.data)
        new_user = PatientFile(name=form.name.data, email=form.email.data, age=form.age.data, gender = form.gender.data, password=hashed_password)

        # Add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        flash("Sign up Successful! You can now log in.", "success")
        return redirect(url_for("log"))  # Redirect to login after signup

    return render_template("LOG-SIGN/signup.html", form=form)




@app.route('/login', methods=["GET", "POST"])
def log():
    form = LoginForm()
    if form.validate_on_submit():
        # Check the email in all user types
        admin = AdminFile.query.filter_by(email=form.email.data).first()
        patient = PatientFile.query.filter_by(email=form.email.data).first()
        doctor = DoctorFile.query.filter_by(email=form.email.data).first()

        # Check for Admin Login
        if admin and check_password_hash(admin.password, form.password.data):
            session['user_id'] = admin.admin_id
            session['user_type'] = "administrator"
            admin.last_login = datetime.now()
            db.session.commit()  # Save last_login

            flash("Login Successful!", "success")
            return redirect(url_for("administrator"))

        # Check for Patient Login
        elif patient and check_password_hash(patient.password, form.password.data):
            session['user_id'] = patient.patient_id
            session['user_type'] = "patient"

            flash("Login Successful!", "success")
            return redirect(url_for("pat", patient_id = patient.patient_id))

        # Check for Doctor Login
        elif doctor and check_password_hash(doctor.password, form.password.data):
            session['user_id'] = doctor.doctor_id
            session['user_type'] = "doctor"

            flash("Login Successful!", "success")
            return redirect(url_for("doc", doctor_id = doctor.doctor_id))

        # Invalid Credentials
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template('LOG-SIGN/login.html', form=form)





@app.route("/forgetPassword")
def forget():
    return render_template("forgetpassword.html")

@app.route("/administrator")
def administrator():
    return render_template("ADMIN/administrator.html")




@app.route("/doctor/<int:doctor_id>")
def doc(doctor_id):
    doctor = DoctorFile.query.get_or_404(doctor_id)
    appointments = AppointmentFile.query.filter_by(doctor_id=doctor_id).all()
    return render_template("DOCTOR/doctor.html", doctor=doctor, appointments=appointments)

@app.route("/doctor/<int:doctor_id>/profile")
def doc_profile(doctor_id):
    doctor = DoctorFile.query.get_or_404(doctor_id)
    return render_template('DOCTOR/doctor_profile.html', doctor = doctor)

@app.route("/doctor/<int:doctor_id>/patients")
def doctorsPatients(doctor_id):
    doctor = DoctorFile.query.get_or_404(doctor_id)
    # Get today's start and end times
    start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    
    # Filter appointments for today
    appointments = AppointmentFile.query.filter(
        AppointmentFile.doctor_id == doctor_id,
        AppointmentFile.appointment_time >= start_of_day,
        AppointmentFile.appointment_time < end_of_day
    ).all()

    return render_template(
        "DOCTOR/doctorspatients.html",
        doctor=doctor,
        appointments=appointments
    )

@app.route('/appointment_form/<int:id>', methods=['GET'])
def appointment_form(id):
    if request.method == "POST":
        patient_id = id
        doctor_id = request.form.get('doctor_id')
        appointment_time = request.form.get('appointment_time')
        description = request.form.get('description')

        # Check if the patient exists in the database
        patient = PatientFile.query.get(patient_id)
        if not patient:
            flash('Invalid patient ID. Patient not found.', 'danger')
            return redirect(url_for('home'))

        # Check if the doctor exists in the database
        doctor = DoctorFile.query.get(doctor_id)
        if not doctor:
            flash('Invalid doctor ID. Doctor not found.', 'danger')
            return redirect(url_for('pat'))

        # Create an appointment object
        try:
            new_appointment = AppointmentFile(
                patient_id=patient_id,
                doctor_id=doctor_id,
                appointment_time=datetime.strptime(appointment_time, '%Y-%m-%dT%H:%M'),
                description=description
            )

            # Add to the database
            db.session.add(new_appointment)
            db.session.commit()

            flash('Appointment booked successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while booking the appointment: {str(e)}', 'danger')
    return render_template('DOCTOR/appointment.html')

@app.route('/book_appointment/<int:id>', methods=['POST'])
def book_appointment(id):
    if request.method == "POST":
        patient_id = id
        doctor_id = request.form.get('doctor_id')
        appointment_time = request.form.get('appointment_time')
        description = request.form.get('description')

        # Check if the patient exists in the database
        patient = PatientFile.query.get(patient_id)
        if not patient:
            flash('Invalid patient ID. Patient not found.', 'danger')
            return redirect(url_for('home'))

        # Check if the doctor exists in the database
        doctor = DoctorFile.query.get(doctor_id)
        if not doctor:
            flash('Invalid doctor ID. Doctor not found.', 'danger')
            return redirect(url_for('pat'))

        # Create an appointment object
        try:
            new_appointment = AppointmentFile(
                patient_id=patient_id,
                doctor_id=doctor_id,
                appointment_time=datetime.strptime(appointment_time, '%Y-%m-%dT%H:%M'),
                description=description
            )

            # Add to the database
            db.session.add(new_appointment)
            db.session.commit()

            flash('Appointment booked successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while booking the appointment: {str(e)}', 'danger')

        return redirect(url_for('pat', patient_id=patient_id))


@app.route("/allPatients/<int:doctor_id>")
def allPatients(doctor_id):
    doctor = DoctorFile.query.get_or_404(doctor_id)

    # Fetch distinct patients who have appointments with this doctor
    patients = PatientFile.query.join(AppointmentFile).filter(
        AppointmentFile.doctor_id == doctor_id
    ).distinct().all()

    return render_template(
        "DOCTOR/totalPatient.html",
        doctor=doctor,
        patients=patients
    )


@app.route("/receptionist")
def reception():
    return render_template("receptionist.html")






@app.route("/patient/<int:patient_id>")
def pat(patient_id):
    patient = PatientFile.query.get_or_404(patient_id)
    return render_template("patient.html", patient= patient)






@app.route("/addAdmin", methods=["GET", "POST"])
def addAdmin():
    if request.method == "POST":
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        role = request.form.get('role', '')
        phone = request.form.get('phone', '')
        is_active = bool(request.form.get('is_active', '0'))  # Default to inactive

        # Validate required fields
        if not (name and email and password and role and phone):
            flash("All fields are required.", "danger")
            return redirect(url_for('addAdmin'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Add new admin to the database
        new_admin = AdminFile(
            name=name,
            email=email,
            password=hashed_password,
            role=role,
            phone=int(phone),
            is_active=is_active,
            last_login=datetime.utcnow()
        )
        try:
            db.session.add(new_admin)
            db.session.commit()
            flash("Admin added successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "danger")

    # Retrieve all admins to display on the page
    admins = AdminFile.query.all()
    return render_template("ADMIN/add_admin.html", admins=admins)


@app.route('/manageAdmin', methods=['GET', 'POST'])
def manage_admin():
    if request.method == 'POST':
        action = request.form['action']

        if action.startswith('edit_'):
            admin_id = int(action.split('_')[1])
            admin = AdminFile.query.get(admin_id)

            # Update admin details
            admin.name = request.form[f'name_{admin_id}']
            admin.email = request.form[f'email_{admin_id}']
            admin.role = request.form[f'role_{admin_id}']
            admin.phone = request.form[f'phone_{admin_id}']
            admin.is_active = bool(int(request.form[f'is_active_{admin_id}']))

            db.session.commit()
            flash('Admin details updated successfully!', 'success')

        elif action.startswith('delete_'):
            admin_id = int(action.split('_')[1])
            admin = AdminFile.query.get(admin_id)

            # Delete the selected admin
            db.session.delete(admin)
            db.session.commit()
            flash('Admin deleted successfully!', 'success')

        return redirect('/manageAdmin')

    # GET request: Fetch all admins from the database
    admins = AdminFile.query.all()
    return render_template('Admin/admin_management.html', admins=admins)






@app.route('/addDoctor', methods=['GET', 'POST'])
def add_doctor():
    if request.method == 'POST':
        # Get data from the form
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        specialist = request.form['specialist']


        hashed_password = generate_password_hash(password)

        # Create a new doctor record
        new_doctor = DoctorFile(
            name=name,
            email=email,
            password=hashed_password,
            phone=phone,
            specialist=specialist
        )
        db.session.add(new_doctor)
        db.session.commit()
        flash('Doctor added successfully!', 'success')

        return redirect('/addDoctor')

    # Retrieve all doctors from the database
    doctors = DoctorFile.query.all()
    return render_template('ADMIN/add_doctor.html', doctors=doctors)



@app.route('/manageDoctor', methods=['GET', 'POST'])
def manage_doctor():
    if request.method == 'POST':
        # Get action from the form submission
        action = request.form['action']

        if action.startswith('edit_'):
            doctor_id = int(action.split('_')[1])
            doctor = DoctorFile.query.get(doctor_id)

            # Update the doctor information
            doctor.name = request.form[f'name_{doctor_id}']
            doctor.email = request.form[f'email_{doctor_id}']
            doctor.phone = request.form[f'phone_{doctor_id}']
            doctor.specialist = request.form[f'specialist_{doctor_id}']

            db.session.commit()
            flash('Doctor information updated successfully!', 'success')

        elif action.startswith('delete_'):
            doctor_id = int(action.split('_')[1])
            doctor = DoctorFile.query.get(doctor_id)

            # Delete the doctor from the database
            db.session.delete(doctor)
            db.session.commit()
            flash('Doctor deleted successfully!', 'success')

        return redirect('/manageDoctor')

    # GET request: Fetch all doctors from the database
    doctors = DoctorFile.query.all()
    return render_template('ADMIN/doctor_management.html', doctors=doctors)

@app.route('/upload/<int:patient_id>', methods=['GET', 'POST'])
def upload_file(patient_id):
    patient = PatientFile.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            return "No file uploaded!", 400
        
        upload = Upload(filename=file.filename, data=file.read(), patient_id=patient_id)
        db.session.add(upload)
        db.session.commit()
        return f'File {file.filename} uploaded for patient {patient.name}'

    return render_template("index.html", patient_id=patient_id, patient_name=patient.name)


@app.route('/patient_files/<int:patient_id>')
def patient_files(patient_id):
    patient = PatientFile.query.get_or_404(patient_id)

    files = patient.uploads 
    return render_template(
        "patient_files.html", 
        patient=patient, 
        files=files
    )

@app.route('/download/<int:file_id>')
def download_file(file_id):
    file = Upload.query.get_or_404(file_id)
    return send_file(BytesIO(file.data), as_attachment=True, download_name=file.filename)

@app.route('/report/<int:doc_id>/<int:id>')
def generate(id, doc_id):
    patient = PatientFile.query.get_or_404(id)
    doctor = DoctorFile.query.get_or_404(doc_id)
    return render_template("genrate_report.html", patient= patient, doctor = doctor)

if __name__ == "__main__":
    app.run(debug=True)
