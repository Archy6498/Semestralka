from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps

app = Flask(__name__)

app.config['SECRET_KEY'] = 'thisissecret'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://bcwxfcqbmotisk:8cf4f0a564264fc4b921bfa5160bd93c4efb0d7b2b232baa3b5d46d34dc4aa04@ec2-54-172-175-251.compute-1.amazonaws.com:5432/da3s606auusc1p'
db = SQLAlchemy(app)                   
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(50))
    password = db.Column(db.String(80))
    admin = db.Column(db.Boolean)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(50))
    complete = db.Column(db.Boolean)
    user_id = db.Column(db.Integer)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message' : 'Nenalezen token!'}), 401
        print("Token", token)
        try: 
            data = jwt.decode(token, app.config['SECRET_KEY'])
            current_user = User.query.filter_by(public_id=data['public_id']).first()
        except jwt.DecodeError:
            return jsonify({"message": "auth token is invalid"}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "auth token expired"}), 401

        return f(current_user, *args, **kwargs)

    return decorated

@app.route('/user', methods=['GET'])
@token_required
def get_all_users(current_user):

    if not current_user.admin:
            return jsonify({'message' : 'Nemas dostatecne opravneni'})

    users = User.query.all()

    output = []

    for user in users:
        user_data = {}
        user_data['public_id'] = user.public_id
        user_data['name'] = user.name
        user_data['password'] = user.password
        user_data['admin'] = user.admin
        output.append(user_data)

    return jsonify({'users' : output})

@app.route('/user/<public_id>', methods=['GET'])
@token_required
def get_one_user(current_user, public_id):

    if not current_user.admin:
        return jsonify({'message' : 'Nemas dostatecne opravneni'})

    user = User.query.filter_by(public_id=public_id).first()

    if not user:
        return jsonify({'message' : 'Uzivatel nenalezen'})

    user_data = {}
    user_data['public_id'] = user.public_id
    user_data['name'] = user.name
    user_data['password'] = user.password
    user_data['admin'] = user.admin

    return jsonify({'user' : user_data})

@app.route('/user', methods=['POST'])
@token_required
def create_user(current_user):
    if not current_user.admin:
        return jsonify({'message' : 'Nemas dostatecne opravneni'})

    data = request.get_json()

    hashed_password = generate_password_hash(data['password'], method='sha256')

    new_user = User(public_id=str(uuid.uuid4()), name=data['name'], password=hashed_password, admin=False)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message' : 'Uzivatel vytvoren'})

@app.route('/user/<public_id>', methods=['PUT'])
@token_required
def promote_user(current_user, public_id):
    if not current_user.admin:
        return jsonify({'message' : 'Nemas dostatecne opravneni'})

    user = User.query.filter_by(public_id=public_id).first()

    if not user:
        return jsonify({'message' : 'Uzivatel nenalezen'})

    user.admin = True
    db.session.commit()

    return jsonify({'message' : 'Uzivateli ma nyni administratorske opravneni'})

@app.route('/user/<public_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, public_id):
    if not current_user.admin:
        return jsonify({'message' : 'Nemas dostatecne opravneni'})

    user = User.query.filter_by(public_id=public_id).first()

    if not user:
        return jsonify({'message' : 'Uzivatel nenalezen'})

    db.session.delete(user)
    db.session.commit()

    return jsonify({'message' : 'Uzivatel byl uspesne smazan'})

@app.route('/login', methods=["GET"])
def login():
    auth = request.authorization
    print ("AUTH", auth)

    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    user = User.query.filter_by(name=auth.username).first()
    print("USER", user.password)
    print("auth", auth.password)
    if not user:
        return make_response('Could not verify - user', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    if user.password == auth.password:
        token = jwt.encode({'public_id' : user.public_id, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])
        print("token", token)
        return jsonify({'token' : token})

    return make_response('Could not verify -pass', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

@app.route('/todo', methods=['GET'])
@token_required
def get_all_todos(current_user):
    todos = Todo.query.filter_by(user_id=current_user.id).all()

    output = []

    for todo in todos:
        todo_data = {}
        todo_data['id'] = todo.id
        todo_data['text'] = todo.text
        todo_data['complete'] = todo.complete
        output.append(todo_data)

    return jsonify({'todos' : output})

@app.route('/todo/complete', methods=['GET'])
@token_required
def get_all_todos_complete(current_user):
    todos = Todo.query.filter_by(complete=True, user_id=current_user.id).all()

    output = []

    for todo in todos:
        todo_data = {}
        todo_data['id'] = todo.id
        todo_data['text'] = todo.text
        todo_data['complete'] = todo.complete
        output.append(todo_data)

    return jsonify({'todos' : output})

@app.route('/todo/incomplete', methods=['GET'])
@token_required
def get_all_todos_incomplete(current_user):
    todos = Todo.query.filter_by(complete=False, user_id=current_user.id).all()

    output = []

    for todo in todos:
        todo_data = {}
        todo_data['id'] = todo.id
        todo_data['text'] = todo.text
        todo_data['complete'] = todo.complete
        output.append(todo_data)

    return jsonify({'todos' : output})

@app.route('/todo/<todo_id>', methods=['GET'])
@token_required
def get_one_todo(current_user, todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()

    if not todo:
        return jsonify({'message' : 'Zadne ukoly nenalezeny'})

    todo_data = {}
    todo_data['id'] = todo.id
    todo_data['text'] = todo.text
    todo_data['complete'] = todo.complete

    return jsonify(todo_data)

@app.route('/todo', methods=['POST'])
@token_required
def create_todo(current_user):
    data = request.get_json()

    new_todo = Todo(text=data['text'], complete=False, user_id=current_user.id)
    db.session.add(new_todo)
    db.session.commit()

    return jsonify({'message' : "Ukol vytvoren"})

@app.route('/todo/<todo_id>', methods=['PUT'])
@token_required
def complete_todo(current_user, todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()

    if not todo:
        return jsonify({'message' : 'Zadne ukoly nenalezeny'})

    todo.complete = True
    db.session.commit()

    return jsonify({'message' : 'Ukol dokoncen'})

@app.route('/todo/<todo_id>', methods=['DELETE'])
@token_required
def delete_todo(current_user, todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()

    if not todo:
        return jsonify({'message' : 'Zadne ukoly nenalezeny'})

    db.session.delete(todo)
    db.session.commit()

    return jsonify({'message' : 'Ukol je smazany'})

if __name__ == '__main__':
    app.run(debug=True)