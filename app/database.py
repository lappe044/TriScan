import time
import uuid
from app.config import *
from hashlib import md5
import secrets


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
