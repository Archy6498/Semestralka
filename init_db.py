#SQLAlchemy
def init_sql_alchemy():
    from app import db
    db.create_all()
    from app import User
    from app import Todo
    test = User(name='bob',password='123456',admin=True)
    db.session.add(test)
    test2 = Todo(text='dssdd',complete=0,user_id=1)
    db.session.add(test2)
    db.session.commit()    
if __name__ == '__main__':
    init_sql_alchemy()    
