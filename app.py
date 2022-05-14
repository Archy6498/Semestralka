from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
import jwt
import datetime
from functools import wraps


app = Flask(__name__)

app.config['SECRET_KEY'] = 'thisissecret'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://whfbxexdvczmfu:af363dcb3875208cca7d2581b17f0e6bb78d1a1be6395406d348f58ffcf31a11@ec2-54-165-184-219.compute-1.amazonaws.com:5432/d29bjm8r00s5sr'
SQLALCHEMY_TRACK_MODIFICATIONS  = False

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
            return jsonify({'message' : 'Autorizační token nenalezen!'}), 401
        print("Token", token)
        try: 
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(public_id=data['public_id']).first()
        except jwt.DecodeError:
            return jsonify({"message": "Autorizační token je neplatný!"}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Autorizační token propadl!"}), 401
       
        return f(current_user, *args, **kwargs)

    return decorated

@app.route('/user', methods=['GET'])
@token_required
def get_all_users(current_user):

    if not current_user.admin:
            return jsonify({'message' : 'Nemáš dostatečné oprávnění!'})

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
        return jsonify({'message' : 'Nemáš dostatečné oprávnění!'})

    user = User.query.filter_by(public_id=public_id).first()

    if not user:
        return jsonify({'message' : 'Uživatel nebyl nalezen!'})

    user_data = {}
    user_data['public_id'] = user.public_id
    user_data['name'] = user.name
    user_data['password'] = user.password
    user_data['admin'] = user.admin

    return jsonify({'user' : user_data})

@app.route('/user/<public_id>', methods=['PUT'])
@token_required
def promote_user(current_user, public_id):
    if not current_user.admin:
        return jsonify({'message' : 'Nemáš dostatečné oprávnění!'})

    user = User.query.filter_by(public_id=public_id).first()

    if not user:
        return jsonify({'message' : 'Uživatel nebyl nalezen!'})

    user.admin = True
    db.session.commit()

    return jsonify({'message' : 'Uzivateli ma nyni administratorske opravneni'})

@app.route('/user/unpromote/<public_id>', methods=['PUT'])
@token_required
def unpromote_user(current_user, public_id):
    if not current_user.admin:
        return jsonify({'message' : 'Nemáš dostatečné oprávnění!'})

    user = User.query.filter_by(public_id=public_id).first()

    if not user:
        return jsonify({'message' : 'Uživatel nebyl nalezen!'})

    user.admin = False
    db.session.commit()

    return jsonify({'message' : 'Uzivateli již nemá administratorske opravneni'})

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
   
    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    user = User.query.filter_by(name=auth.username).first()
    
    if not user:
        return make_response('Could not verify - user', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    if check_password_hash(user.password, auth.password):
        token = jwt.encode({'public_id' : user.public_id, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'], "HS256")
        
        return jsonify({'token' : token})

    return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})


#Endpoints pro úkoly

# vytvoření nového úkolu
@app.route('/todo', methods=['POST'])
@token_required
def create_todo(current_user):
    data = request.get_json()

    new_todo = Todo(text=data['text'], complete=False, user_id=current_user.id)
    db.session.add(new_todo)
    db.session.commit()

    return jsonify({'message' : "Úkol vytvořen!"})

# dokončení úkolu
@app.route('/todo/<todo_id>', methods=['PUT'])
@token_required
def complete_todo(current_user, todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()

    if not todo:
        return jsonify({'message' : 'Žádné úkoly nebyly nalezeny!'})

    todo.complete = True
    db.session.commit()

    return jsonify({'message' : 'Úkol byl dokončen!'})

# upravení úkolu - editace textu
@app.route('/todo/edit/<todo_id>', methods=['PUT'])
@token_required
def edit_todo(current_user, todo_id):
    data = request.get_json()
    
    text = data.get('text', None)
    
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()
    todos = Todo.query.filter_by(id=todo_id, complete=False, user_id=current_user.id).first()

    if not todo:
        return jsonify({'message' : 'Špatně zadané ID úkolu!'})
    elif not todos:
        return jsonify({'message' : 'Dokončený úkol nemůžeš měnit!'})

    todo.text = text
    db.session.commit()

    return jsonify({'message' : 'Úkol byl úspěšně změněn!'})

# výpis všech úkolů uživatele
@app.route('/todo', methods=['GET'])
@token_required
def get_all_todos(current_user):
    todos = Todo.query.filter_by(user_id=current_user.id).all()
    if not todos:
        return jsonify({'message' : 'Nejsou zde žádné úkoly'})
    output = []

    for todo in todos:
        todo_data = {}
        todo_data['id'] = todo.id
        todo_data['text'] = todo.text
        todo_data['complete'] = todo.complete
        output.append(todo_data)

    return jsonify({'Tvoje úkoly:' : output})

# výpis všech dokončených úkolů
@app.route('/todo/complete', methods=['GET'])
@token_required
def get_all_todos_complete(current_user):
    todos = Todo.query.filter_by(complete=True, user_id=current_user.id).all()
    if not todos:
        return jsonify({'message' : 'Nejsou zde žádné úkoly!'})
    output = []

    for todo in todos:
        todo_data = {}
        todo_data['id'] = todo.id
        todo_data['text'] = todo.text
        todo_data['complete'] = todo.complete
        output.append(todo_data)

    return jsonify({'Tvoje hotové úkoly:' : output})

# výpis všech nedokončených úkolů
@app.route('/todo/incomplete', methods=['GET'])
@token_required
def get_all_todos_incomplete(current_user):
    todos = Todo.query.filter_by(complete=False, user_id=current_user.id).all()
    if not todos:
        return jsonify({'message' : 'Všechny úkoly máš vyřešené, gratuluji!'})
    output = []

    for todo in todos:
        todo_data = {}
        todo_data['id'] = todo.id
        todo_data['text'] = todo.text
        todo_data['complete'] = todo.complete
        output.append(todo_data)

    return jsonify({'Úkoly, které je nutné dokončit:' : output})

# výpis samostatného úkolu
@app.route('/todo/<todo_id>', methods=['GET'])
@token_required
def get_one_todo(current_user, todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()

    if not todo:
        return jsonify({'message' : 'Úkol neexistuje!'})

    todo_data = {}
    todo_data['id'] = todo.id
    todo_data['text'] = todo.text
    todo_data['complete'] = todo.complete

    return jsonify(todo_data)

# smazání úkolu
@app.route('/todo/<todo_id>', methods=['DELETE'])
@token_required
def delete_todo(current_user, todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()

    if not todo:
        return jsonify({'message' : 'Žádné úkoly nenalezeny!'})

    db.session.delete(todo)
    db.session.commit()

    return jsonify({'message' : 'Úkol je smazaný!'})

if __name__ == '__main__':
    app.run(debug=True)