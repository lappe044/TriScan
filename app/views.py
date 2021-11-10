from flask import render_template, request, redirect, make_response
from app import app
from app.database import *


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

                if role == 'Student':

                    student_name = user["firstName"]
                    print(student_name)
                    return render_template('student.html', student_name=student_name)

                if role == 'Faculty':

                    faculty_name = user["lastName"]
                    print(faculty_name)
                    return render_template('faculty.html', faculty_name=faculty_name)

    response = make_response(redirect('/login'))
    response.set_cookie('Authorization', '', max_age=0)
    return response

@app.route("/logout")
def logout():

    return render_template("/login.html")