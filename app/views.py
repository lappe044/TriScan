from flask import Flask, render_template, request, redirect

from app import app


@app.route("/", methods=['GET', 'POST'])
def login():

    if request.method == "POST":

        req = request.form

        email = req["email"]
        password = req["password"]

        flag = True

        # check email and password in database
        if(flag):
            redirect("/student")
        else:
            redirect("/faculty")

        print(email, password)



    # if email is associate with student, render template '/student'
    # if email is associate with faculty, render template '/faculty'

    return render_template("/login.html")


@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":

        req = request.form

        first_name = req["f_name"]
        last_name = req["l_name"]
        email = req["email"]
        password = req["password"]
        profession = req["profession"]

        print(first_name,last_name,email,password, profession)

        redirect("/") # value is the route 

    return render_template("/create_account.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        req = request.form

        email = req["email"]
        new_password = req["new_pass"]

        print(email,new_password)

    # update the user's old password to new password

        redirect('/')
    
    return render_template("/forgot_pass.html")


@app.route("/student")
def student_page():

    return render_template("/student.html")

@app.route("/faculty")
def faculty_page():

    return render_template("/faculty.html")