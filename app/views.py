from flask import render_template, request, redirect, make_response, jsonify, send_file, url_for, abort
from app import app
from app.database import *
from werkzeug.utils import secure_filename
import math
import gridfs
from itertools import zip_longest


@app.route("/", methods=['GET', 'POST'])
def login():
    if request.method == "POST":

        req = request.form

        if 'email' in req.keys() and 'password' in req.keys():

            uid = compare_credentials(req['email'], req['password'])
            if uid is not None:

                session = generate_session_token(uid)

                response = make_response(redirect('/dashboard'))
                response.set_cookie('Authorization', session, max_age=60 * 60 * 24)
                return response

            else:
                # FLASH USER WITH INCORRECT LOGIN DETAILS ERROR HERE.
                return redirect('/')

    if request.method == 'GET':
        if 'Authorization' in request.cookies.keys():
            return redirect(url_for('dashboard_page'))

    return render_template('login.html')


@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":

        req = request.form

        if 'f_name' in req.keys() and 'l_name' in req.keys() and 'email' in req.keys() and 'password' in req.keys() and 'profession' in req.keys():

            if email_exists(req['email']) is False:

                uid = create_user(req['f_name'], req['l_name'], req['email'], req['password'], req['profession'])
                session = generate_session_token(uid)

                response = make_response(redirect('/dashboard'))
                response.set_cookie('Authorization', session, max_age=60 * 60 * 24)
                return response

    return render_template("/create_account.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        req = request.form

        if 'email' in req.keys() and 'new_pass' in req.keys():
            if email_exists(req['email']):
                update_password(req['email'], req['new_pass'])
                return redirect('/')

    return render_template("/forgot_pass.html")


@app.route("/dashboard")
def dashboard_page():
    if 'Authorization' in request.cookies.keys():
        uid = get_uid_from_session(request.cookies['Authorization'])

        if uid is not None:

            user = get_user_from_uid(uid)

            role = get_role_from_uid(uid)
            if role is not None:

                courses = get_courses(uid)

                if role == 'Student':

                    student_name = user["firstName"]
                    return render_template('student.html', student_name=student_name, courses=courses)

                if role == 'Faculty':

                    faculty_name = user["lastName"]
                    return render_template('faculty.html', faculty_name=faculty_name, courses=courses)

    response = make_response(redirect('/login'))
    response.set_cookie('Authorization', '', max_age=0)
    return response

@app.route("/logout")
def logout():

    return render_template("/login.html")


@app.route("/categories")
def categories():

    return render_template("/categories.html")


@app.route("/course/<courseId>/reports")
def list_reports(courseId):
    uid = get_uid_from_session(request.cookies['Authorization'])
    role = get_role_from_uid(uid)
    if uid is not None:
        if role == 'Student':
            courseSection = get_course_section(courseId)
            courseName = get_course_name(courseId)
            assignments = get_assignments(uid, courseId)
            return render_template("/report_list_by_student.html", assignments=assignments, course=courseSection, courseId=courseId, courseName=courseName, zip=zip)
        if role == 'Faculty':
            students = get_students(courseId)
            course = get_course_section(courseId)
            categories = get_categories(courseId)
            return render_template("/report_list_by_category.html", course=course, students=students, categories=categories, courseId=courseId, zip=zip)

@app.route("/reports/<student_name>")
def reports(student_name):
    uid = get_uid_from_session(request.cookies['Authorization'])
    if uid is not None:
        courses = get_courses(uid)
        reports = []
        assignmentsList =[]
        submissions= []
        for course in courses:
            assignments = get_assignments(uid, course["courseId"])
            previousAssignment = assignments['previous']
            for assign in previousAssignment:
                most_recent_submission = list(mongo.db.submissions.find({'uid': uid, 'assignmentId': assign['assignmentId']}).sort('_id', -1))
                if len(most_recent_submission) > 0:
                    most_recent_submission = most_recent_submission[0]
                    report = mongo.db.reports.find_one({'submissionId': most_recent_submission['submissionId']})
                    permitted_users = report['reportPermittedUsers']
                    for p in permitted_users:
                        if p == uid:
                            reports.append(report)
                            submissions.append(assign)
                            assignment = mongo.db.assignments.find_one({'assignmentId': assign['assignmentId']})
                            print(assignment)
                            assignmentsList.append(assignment)
    try:
        return render_template("/report.html", courses=courses, student_name=student_name, reports=reports, zip=zip, submissions = submissions, assignment=assignmentsList)
    except:
        return redirect('/dashboard') #there if it fails to actually run

#can maybe add faculty functionality to this? check for role then render
@app.route("/reports/<student_name>/<reportId>")
def generated_reports(reportId, student_name):
    uid = get_uid_from_session(request.cookies['Authorization'])
    if uid is not None:
        role = get_role_from_uid(uid)
        if role == 'Student':
            report = mongo.db.reports.find_one({'reportId': reportId})
            file = report['files']
            errors = report['grammarErrors']
            scores = report['scoring']
            return render_template("generated_report.html", file = file, errors = errors, scores =scores, name=student_name)
        if role == 'Faculty':
            report = mongo.db.reports.find_one({'reportId': reportId})
            file = report['files']
            errors = report['grammarErrors']
            scores = report['scoring']
            return render_template("generated_report_faculty.html", file = file, errors = errors, scores =scores, name=student_name)


@app.route("/reports/<student_name>/all/<courseId>")
def generate_student_course_reports(courseId, student_name):
    return render_template("report_list_by_student", name=student_name, zip=zip)

@app.route("/reports/<courseId>/<category>")
def generate_category_reports(courseId, student_name):
    return render_template("report_list_by_category.html", name=student_name, zip=zip)

@app.route("/course/<courseId>/students")
def student_roster(courseId):
    students = get_students(courseId)
    return render_template("/student_roster.html", courseId=courseId, students=students)


@app.route("/course/<courseId>")
def list_courses(courseId):
    uid = get_uid_from_session(request.cookies['Authorization'])
    role = get_role_from_uid(uid)
    if uid is not None:
        if role == 'Student':
            course = get_course_section(courseId)
            assignments = get_assignments(uid, courseId)
            print(courseId)
            return render_template("/class.html", assignments=assignments, course=course, courseId=courseId, url_root=request.base_url.replace('//', '\\\\').split('/')[0].replace('\\\\', '//'))
        if role == 'Faculty':
            students = get_students(courseId)
            course = get_course_section(courseId)
            categories = get_categories(courseId)
            return render_template("/faculty_course_view.html", course=course, students=students, categories=categories, courseId=courseId)

app.config["ALLOWED_FILE_EXTENSIONS"] = ["PDF", "DOC", "DOCX"]

# Function that checks for file extensions
# return True if file extensions is allowed
#return False if no file extensions were given or file extensions not allowed
def allowed_file(filename):

    if not "." in filename:
        return False

    # take the first element from the right and store in the extension var
    ext = filename.split(".", 1)[1]

    # compare ext with allowed_file_extensions
    if ext.upper() in app.config["ALLOWED_FILE_EXTENSIONS"]:
        return True
    else:
        return False

    
@app.route("/course/<courseId>/add-person", methods=["POST", "GET"])
def add_person(courseId):
    if request.method == "POST":

        req = request.form
        print(req)
        if 'name' in req.keys() and 'profession' in req.keys():

            uid = get_uid_from_name(req['name'])
            if uid is not None:
                add_to_roster(courseId, uid)
            else:
                print("User is not registered")
    return redirect('/course/'+courseId)

@app.route("/course/<courseId>/add-category", methods=["POST", "GET"])
def add_category(courseId):
    if request.method == "POST":

        req = request.form
       
        if 'category' in req.keys():

            if courseId is not None:
            
                update_categories(courseId, req['category'])
    return redirect('/course/'+courseId)

@app.route("/course/<courseId>/delete-person/<uid>", methods=["POST", "GET"])
def delete_from_roster(courseId, uid):
    delete_user_from_roster(courseId, uid)
    return redirect('/course/'+courseId)

@app.route("/upload-file/<courseId>", methods=["GET", "POST"])
def upload_file(courseId):

    if request.method == "POST":

        if 'Authorization' in request.cookies.keys():
            uid = get_uid_from_session(request.cookies['Authorization'])

            if request.files and uid is not None:

                # Get the file object
                file = request.files["file"]

                if file.filename == "":
                    print("File must have a filename")

                    return redirect('/course/'+courseId)

                elif not allowed_file(file.filename):
                    print("The file extensions is not allowed")

                    return redirect('/course/'+courseId)
                else:
                    # extra step to secure the file
                    filename = secure_filename(file.filename)
                    assignmentId = request.form['assignmentId']
                    if len(assignmentId) > 0 and len(courseId) > 0:
                        file_content = file.read()
                        print(filename)
                        print(courseId)
                        print(assignmentId)

                        submissionId = str(uuid.uuid4())

                        file_data = upload_file_to_database(filename, file_content, file, courseId, submissionId, assignmentId, uid)
                        print(file_data)

                        submissions_object = {
                            'submissionId': submissionId,
                            'uid': uid,
                            'courseId': courseId,
                            'assignmentId': assignmentId,
                            'files': [file_data['fileId']],  # allowed for possibility to add multiple files in db. maybe out of scope?
                            'submittedAt': math.ceil(time.time()) + (60 * 60 * 24 * 7),
                            'references': []  # doesn't store any references... maybe we add that as input in form?
                        }
                        mongo.db.submissions.insert_one(submissions_object)

    return redirect('/course/'+courseId)

@app.route('/upload', methods=["POST"])
def upload():
    for file in request.files:
        print(file)
        upload_file(file, request.files[file])
    return None


@app.route('/messages', methods=['GET'])
def messages():
    if 'Authorization' in request.cookies.keys():
        uid = get_uid_from_session(request.cookies['Authorization'])
        if uid is not None:
            most_recent_chat = get_most_recent_chat(uid)
            if most_recent_chat is not None:
                return redirect('/messages/'+most_recent_chat)
            else:
                return redirect('/messages/new')


@app.route('/messages/<chatId>', methods=['GET'])
def get_chat(chatId):
    if 'Authorization' in request.cookies.keys():
        uid = get_uid_from_session(request.cookies['Authorization'])
        if uid is not None:
            return render_template('messages.html', uid=uid, chatId=chatId, url_root=request.base_url.replace('//', '\\\\').split('/')[0].replace('\\\\', '//'))

@app.route("/messages/<chatId>/add_chat", methods=["POST", "GET"])
def add_chat(chatId):
    if request.method == "POST":

        req = request.form
       
        if 'chat_name' in req.keys() and 'person_name' in req.keys():
            creatorUid = get_uid_from_session(request.cookies['Authorization'])
            uid = get_uid_from_name(req['person_name'])
            if uid is not None:
                create_chat_with_user(uid, creatorUid, req['chat_name'])
    return redirect('/messages/'+chatId)

@app.route('/messages/<chatId>/json', methods=['POST'])
def get_json_chat(chatId):
    data = request.json
    messages = load_messages(chatId, 10000, data['before'], data['after'])
    return jsonify(messages)


@app.route('/chats/<chatId>/json', methods=['GET'])
def get_chat_data(chatId):
    chat = load_chat_data(chatId)
    return jsonify(chat)


@app.route('/chats/json', methods=['GET'])
def get_side_chats():
    if 'Authorization' in request.cookies.keys():
        uid = get_uid_from_session(request.cookies['Authorization'])
        if uid is not None:
            recent_chats = get_recent_chats(uid)
            return jsonify(recent_chats)


@app.route('/messages/<chatId>/send', methods=['POST'])
def user_sent_message(chatId):
    if 'Authorization' in request.cookies.keys():
        uid = get_uid_from_session(request.cookies['Authorization'])
        if uid is not None:
            data = request.form
            send_message(uid, chatId, data['message'], [])
            return redirect(url_for('get_chat', chatId=chatId))


@app.route('/images/profile_pictures/<uid>')
def get_profile_picture(uid):
    user_to_get = get_user_from_uid(uid)
    if user_to_get['profilePicture'] is not None:
        file = get_file(user_to_get['profilePicture'])
        if file is not None:
            return send_file('static/images/default_profile_picture.jpg', mimetype='image/gif')
            # NO WAY TO ACTUALLY SET PFP IN THE CODE SO USELESS TO CHECK AS OF RN, NOT HARD TO IMPLEMENT LATER
            # MOVING ON TO KEEP PROGRESS.
        else:
            return send_file('static/images/default_profile_picture.jpg', mimetype='image/gif')


@app.route('/download/<fileId>', methods=['GET'])
def download_file(fileId):
    file_name = mongo.db.files.find_one({'fileId': fileId})
    if file_name is None:
        # is likely submission id
        submission_data = mongo.db.submissions.find_one({'submissionId': fileId})
        if submission_data is not None:
            fileId = submission_data['files'][0]
            print(fileId)
            file_name = mongo.db.files.find_one({'fileId': fileId})
            file_name = mongo.db.files.find_one({'fileId': fileId})
            print(file_name)
        else:
            abort(404)
    file_data = mongo.db.fs.files.find_one({'filename': fileId})

    if file_data is None or file_name is None:
        abort(404)

    fs = gridfs.GridFS(mongo.db)

    file_binary = fs.get(file_data['_id']).read()

    response = make_response(file_binary)
    response.headers.set('Content-Disposition', 'attachment', filename=f'{file_name["fileName"]}')

    return response
