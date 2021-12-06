import io
import math
import os
import time
import uuid
from app.config import *
from hashlib import md5
import secrets
from gingerit.gingerit import GingerIt
import nltk
nltk.download('punkt')
from nltk.tokenize import sent_tokenize, wordpunct_tokenize
import PyPDF2
import textract


def get_hash(password):
    return md5(password.encode('utf-8')).hexdigest()


def compare_credentials(email, password):
    credentials = mongo.db.credentials.find_one({'email': email.lower()}, {'_id': 0})
    if credentials is not None:
        if get_hash(password) == credentials['passwordHash']:
            return credentials['uid']
    return None


def get_user_from_uid(uid):
    return mongo.db.users.find_one({'uid': uid}, {'_id': 0})


def generate_session_token(uid):

    session_token = secrets.token_hex(32)

    session = {
        'uid': uid,
        'token': session_token,
        'expiresAt': time.time()+(60*60*24)
    }

    mongo.db.sessions.insert_one(session)

    return session_token


def get_uid_from_session(token):
    session = mongo.db.sessions.find_one({'token': token})
    if session is not None:
        return session['uid']


def get_role_from_uid(uid):
    user = get_user_from_uid(uid)
    if user is not None and 'role' in user.keys():
        return user['role']


def email_exists(email):
    user = mongo.db.credentials.find_one({'email': email})
    return user is not None


def create_user(firstName, lastName, email, password, role):
    passwordHash = get_hash(password)
    uid = str(uuid.uuid4())

    if role.lower() == 'student':
        role = 'Student'
    elif role.lower() == 'faculty':
        role = 'Faculty'

    if role in ['Student', 'Faculty']:
        user = {
            'uid': uid,
            'role': role,
            'firstName': firstName,
            'lastName': lastName,
            'fullName': firstName+' '+lastName,
            'profilePicture': None
        }
        credentials = {
            'uid': uid,
            'email': email,
            'passwordHash': passwordHash
        }
        mongo.db.credentials.insert_one(credentials)
        mongo.db.users.insert_one(user)
        return uid


def update_password(email, password):
    mongo.db.credentials.update_one({'email': email.lower()}, {'$set': {'passwordHash': get_hash(password)}})


def get_courses(uid):
    return mongo.db.courses.find({"members": {"$all": [uid]}}, {'_id': 0, 'members': 0})


def get_uid_from_name(name):
    user = mongo.db.users.find_one({'fullName': name}, {'_id': 0})
    if user is not None:
        return user['uid']
    else:
        return None
    

def get_submissions(uid,assignmentId):
    submissions = list(mongo.db.submissions.find({"uid": uid, "assignmentId": assignmentId}))
    return submissions

def get_assignments(uid, courseid):
    assignments = mongo.db.assignments.find({"courseId": courseid})

    assignments_returnable = {}

    upcoming_coursework = []
    missed_coursework = []
    previous_coursework = []

    for assignment in assignments:

        dueAt_int = assignment['dueAt']
        assignment['dueAt'] = time.strftime("%D %H:%M", time.localtime(dueAt_int))

        submissions = list(mongo.db.submissions.find({"uid": uid, "assignmentId": assignment['assignmentId']}))
        if len(submissions) > 0:
            assignment['submissions'] = submissions
            assignment['submitted'] = True
            assignment['submissionId'] = submissions[-1]['submissionId']
            previous_coursework.append(assignment)
        else:
            if dueAt_int < time.time():
                missed_coursework.append(assignment)
            else:
                upcoming_coursework.append(assignment)

    previous_coursework += missed_coursework
    assignments_returnable['upcoming'] = upcoming_coursework
    # assignments_returnable['missed'] = missed_coursework
    assignments_returnable['previous'] = previous_coursework

    return assignments_returnable


#KEVIN PLEASE SEE IF YOU CAN GET THIS TO WORK worst case we use a text file instead of a pdf to show we can do something
def upload_file_to_database(file_name, file_contents, file_obj, courseId, submissionId, assignmentId, uid):
    fileId = str(uuid.uuid4())
    mongo.save_file(fileId, file_obj)

    file = {
        "fileId": fileId,
        "fileName": file_name
    }

    mongo.db.files.insert_one(file)

    # VERY BAD IMPLEMENTATION, BUT ANYTHING TO GET IT TO WORK...


    if file_name[-4:].lower() == '.doc' or file_name[-5:].lower() == '.docx':

        try:
            os.mkdir('temp_files')
        except:
            pass

        f = open(f'temp_files/{file_name}', 'wb')
        f.write(file_contents)
        f.flush()

        text = textract.process(f'temp_files/{file_name}').decode()


    elif file_name[-4:].lower() == '.pdf':

        file_binary = io.BytesIO(file_contents)

        # creating a pdf reader object
        pdfReader = PyPDF2.PdfFileReader(file_binary)
        print(pdfReader.numPages)

        text = ''

        for page in range(0, pdfReader.numPages):
            pageObj = pdfReader.getPage(page)
            text += '\n' + pageObj.extractText()


    tokenized_text = sent_tokenize(text)

    #MAKE REPORT
    reportId = str(uuid.uuid4())
    report = {
        'reportId': reportId,
        'submissionId': submissionId,
        'courseId': courseId,
        'assignmentId': assignmentId,
        'uid': uid,
        'files': fileId, # supposed to be an array, but we've got code that works with it already and i cba to break everything. and is also meant to be the highlighted version, but...
        'submittedAt': math.floor(time.time()),
        'references': [],
        'reportPermittedUsers': [uid], # need to make it so the teacher is in there, but for now only student can see right away.
        'grammarErrors': [],
        'scoring': {'plagiarism': 0, 'grammar': 0, 'similarities': 0}
    }
    mongo.db.reports.insert_one(report)

    # send each sentence to grammar checker
    for d in tokenized_text:
        grammar_check_file(d, reportId)

    return file


def get_file(fileId):
    file = mongo.db.files.find_one({'fileId': fileId})


# This LIBRARY WE'RE USING DOESN'T ALLOW FOR MORE THAN 300 CHARS PER REQUEST. WE NEED TO SPLIT THE TEXT BY SENTENCES / MAX 300 CHARS
def grammar_check_file(text, reportId):
    gingered_dict = GingerIt().parse(text)
    print(gingered_dict)
    for fix in gingered_dict['corrections']:
        mongo.db.reports.update_one({'reportId': reportId}, {'$push': {'grammarErrors': fix}})


def get_students(courseId):
    course = mongo.db.courses.find_one({"courseId": courseId})
    student_data = list(mongo.db.users.find({"uid": {"$in": course['members']}}, {'_id':0}))
    return student_data


def create_chat(userId):
    chatId = str(uuid.uuid4())
    sentAt = math.floor(time.time())
    mongo.db.chats.insert_one({'chatName': 'New Chat', 'chatId': chatId, 'lastMessageAt': sentAt, 'lastMessageId': None, 'members': [userId]})
    return chatId

#KEVIN PLEASE LOOK AT THIS
def create_chat_with_user(userId, creatorId, chatName):
    existingChatId = list(mongo.db.chats.find({'chatName': {'$all': [chatName]}}).limit(1))
    if len(existingChatId) > 0:
        mongo.db.chats.update_one({'chatName': chatName}, {'$push': {'members': userId}})
        return existingChatId
    else:
        chatId = str(uuid.uuid4())
        sentAt = math.floor(time.time())
        mongo.db.chats.insert_one({'chatName': chatName, 'chatId': chatId, 'lastMessageAt': sentAt, 'lastMessageId': None, 'members': [userId]})
        mongo.db.chats.update_one({'chatId': chatId}, {'$push': {'members': creatorId}})
        return chatId

def get_recent_chats(userId, limit=5):
    recent_chats = list(mongo.db.chats.find({'members': {'$all': [userId]}}, {'_id': 0}).sort('lastMessageAt', -1).limit(limit))
    return recent_chats


def get_most_recent_chat(userId):
    most_recent_chat = list(mongo.db.chats.find({'members': {'$all': [userId]}}, {'_id': 0}).sort('lastMessageAt', -1).limit(1))
    if len(most_recent_chat) > 0:
        most_recent_chat = most_recent_chat[0]
        return most_recent_chat['chatId']
    else:
        return None


def rename_chat(chatId, chatName):
    mongo.db.chats.update_one({'chatId': chatId}, {'$set': {'chatName': chatName}})


def send_message(userId, chatId, message, attachments=[]):
    messageId = str(uuid.uuid4())
    sentAt = math.floor(time.time())
    mongo.db.messages.insert_one({'messageId': messageId, 'chatId': chatId, 'uid': userId, 'sentAt': sentAt, 'content': message, 'attachments': attachments})
    mongo.db.chats.update_one({'chatId': chatId}, {'$set': {'lastMessageAt': sentAt, 'lastMessageId': messageId}})


def load_chat_data(chatId):
    chat_data = mongo.db.chats.find_one({'chatId': chatId}, {'_id': 0})
    if chat_data is not None:
        users = list(mongo.db.users.find({'uid': {'$in': chat_data['members']}}, {'_id': 0}))
        dict_users = {}
        for user in users:
            dict_users[user['uid']] = user
        chat_data['members'] = dict_users
        return chat_data
    else:
        return {}


def load_messages(chatId, limit=5, before=None, after=0):
    if before is None:
        before = time.time()
    messages = list(mongo.db.messages.find({'chatId': chatId, 'sentAt': {'$lt': before, '$gt': after}}, {'_id': 0}).sort('sentAt', -1).limit(limit))

    userids = set()
    for message in messages:
        userids.add(message['uid'])

    users = list(mongo.db.users.find({'uid': {'$in': list(userids)}},{'_id':0}))

    users_dict = {}
    for user in users:
        users_dict[user['uid']] = user

    response = {}
    response['messages'] = messages
    response['users'] = users_dict
    return response


def get_course_section(courseId):
    course = mongo.db.courses.find_one({"courseId": courseId})
    section = course['courseSection']
    return section
def get_course_name(courseId):
    course = mongo.db.courses.find_one({"courseId": courseId})
    name = course['courseName']
    return name


def get_categories(courseId):
    course = mongo.db.categories.find_one({"courseId": courseId})
    category_data = course['courseCategories']
    return category_data


def update_categories(courseId, categoryType):
    print(categoryType)
    mongo.db.categories.update_one({'courseId': courseId}, {'$push': {'courseCategories': categoryType}})


def add_to_roster(courseId, uid):

    mongo.db.courses.update_one({'courseId': courseId}, {'$push': {'members': uid}})


def delete_user_from_roster(courseId, uid):
  
    mongo.db.courses.update_one({'courseId': courseId}, {'$pull': {'members': uid}})

#can be config'd to insert data to mongo
def make_fake_users(firstName, lastName, email):
    passwordHash = get_hash('password')
    uid = str(uuid.uuid4())
    user = {
        'uid': uid,
        'role': 'Student',
        'firstName': firstName,
        'lastName': lastName,
        'fullName': firstName+' '+lastName,
        'profilePicture': None
    }
    credentials = {
        'uid': uid,
        'email': email,
        'passwordHash': passwordHash
    }
    mongo.db.credentials.insert_one(credentials)
    mongo.db.users.insert_one(user)
    return uid
"""
make_fake_users("Aadarsh", "Akula", "aadarshakula@gmail.com")
make_fake_users("Jordan", "Allen", "jordanallen@gmail.com")
make_fake_users("Tyler", "Baeur", "tylerbaeur@gmail.com")
make_fake_users("Derik", "Beardshear", "derikbeardsheara@gmail.com")
make_fake_users("Christopher", "Bennett", "christopherbennett@gmail.com")
make_fake_users("Dylan", "Black", "dylanblack@gmail.com")

make_fake_users("Evan", "Brown", "evanbrown@gmail.com")
make_fake_users("Jiameng", "Chen", "jiamengchen@gmail.com")
make_fake_users("Sullivan", "Eiden", "sullivaneiden@gmail.com")
make_fake_users("Jiayu", "Fang", "jiayafang@gmail.com")
make_fake_users("Connor", "Gravitt", "connergravitt@gmail.com")
make_fake_users("Mitchell", "Hanson", "mitchellhanson@gmail.com")
make_fake_users("Sam", "Heath", "samheath@gmail.com")
make_fake_users("Yor", "Her", "yorher@gmail.com")
make_fake_users("Austin", "High", "austinhigh@gmail.com")
make_fake_users("Mingfu", "Haung", "minfuhaung@gmail.com")
make_fake_users("Tyler", "Jeffries", "tylerjeffries@gmail.com")
make_fake_users("Lucas", "Johnson", "lucasjohnson@gmail.com")
make_fake_users("Jonas", "Kohls", "jonaskohls@gmail.com")
make_fake_users("Jacob", "Korf", "jacobkorf@gmail.com")
make_fake_users("Bailey", "LaBerge", "baileylaberge@gmail.com")
make_fake_users("Corbin", "LaFleur", "corbinlafleur@gmail.com")
make_fake_users("Matthew", "Lane", "matthewlane@gmail.com")
make_fake_users("Zachary", "Menter", "zacharymenter@gmail.com")
make_fake_users("Laura", "Pryor", "laurapryor@gmail.com")
make_fake_users("Nyle", "Siddiqui", "nylesiddiqui@gmail.com")

"""
