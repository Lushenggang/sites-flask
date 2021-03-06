import time

from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from datetime import datetime

post_tag_relations = db.Table('post_tag_relations',
  db.Column('post_id', db.Integer, db.ForeignKey('tags.id')),
  db.Column('tag_id', db.Integer, db.ForeignKey('posts.id'))
)

class Permission:
  FOLLOW = 1
  COMMENT = 2
  WRITE = 4
  MODERATE = 8
  ADMIN = 16

class Role(db.Model):
  __tablename__ = 'roles'
  id = db.Column(db.Integer, primary_key = True)
  name = db.Column(db.String(64), unique = True)
  permissions = db.Column(db.Integer)
  default = db.Column(db.Boolean, default = False, index = True)
  users = db.relationship('User', backref='role')

  def __init__(self, **kwargs):
    super(Role, self).__init__(**kwargs)
    if self.permissions is None:
      self.permissions = 0

  @staticmethod
  def insert_roles():
    roles = {
      'User': [Permission.FOLLOW, Permission.COMMENT],
      'Moderator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE],
      'Administrator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE, Permission.ADMIN]
    }
    default_role = 'User'
    for r in roles:
      role = Role.query.filter_by(name = r).first()
      if role is None:
        role = Role(name = r)
      role.reset_permissions()
      for perm in roles[r]:
        role.add_permission(perm)
      role.default = (role.name == default_role)
      db.session.add(role)
    db.session.commit()
  
  def has_permission(self, permission):
    return self.permissions & permission == permission

  def add_permission(self, permission):
    if not self.has_permission(permission):
      self.permissions += permission
  
  def remove_permission(self, permission):
    if self.has_permission(permission):
      self.permissions -= permission
    
  def reset_permissions(self):
    self.permissions = 0 

  def __repr__(self):
    return "<Role %r>" % self.name

# class Follow(db.Model):
#   __tablename__ = 'follows'
#   follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key = True)
#   followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key = True)
#   timestamp = db.Column(db.DateTime, default = datetime.utcnow)

class User(db.Model, UserMixin):
  __tablename__ = 'users'
  id = db.Column(db.Integer, primary_key = True)
  id_string = db.Column(db.String(32), unique = True, index = True) # 第三方登录唯一id
  email = db.Column(db.String(64), unique = True, index = True)
  username = db.Column(db.String(64), index = True)
  avatar = db.Column(db.Text(), default="default_avatar.jpg")
  role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
  password_hash = db.Column(db.String(128))
  confirmed = db.Column(db.Boolean, default = False)
  name = db.Column(db.String(64))
  location = db.Column(db.String(64))
  aboute_me = db.Column(db.Text())
  member_since = db.Column(db.DateTime(), default = datetime.utcnow)
  last_seen = db.Column(db.DateTime(), default = datetime.utcnow)
  posts = db.relationship('Post', backref = 'author', lazy = 'dynamic')
  comments = db.relationship('Comment', backref = 'author', lazy = 'dynamic')
  bbs = db.relationship('BBS', backref='author', lazy='dynamic')
  likes = db.relationship('Like', backref = 'author', lazy = 'dynamic')
  # followed = db.relationship('Follow',
    # foreign_keys = [Follow.followed_id],
    # backref = db.backref('follower', lazy="joined")
    # )

  # session_token = db.Column(db.String(64), unique = True, index = True)
  # session_expired_time = db.Column(db.String(64), unique = True, index = True)

  def __init__(self, **kwargs):
    super(User, self).__init__(**kwargs)
    if self.role is None:
      if self.email == current_app.config['FLASK_ADMIN']:
        self.role = Role.query.filter_by(name = 'Administrator').first()
        self.confirmed = True
      if self.role is None:
        self.role = Role.query.filter_by(default = True).first()
    if self.avatar is None:
      self.avatar = 'default_avatar.jpg'

  def __repr__(self):
    return "<User %r>" % self.username
  
  @property
  def password(self):
    return AttributeError('password is not a readable attribute')

  @password.setter
  def password(self, password):
    self.password_hash = generate_password_hash(password)
  
  def verify_password(self, password):
    return check_password_hash(self.password_hash, password)

  def generate_confirmation_token(self, expiration = 3600):
    s = Serializer(current_app.config['SECRET_KEY'], expires_in = expiration)
    return s.dumps({'confirm': self.id}).decode('utf-8')

  def confirm(self, token):
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
      data = s.loads(token.encode('utf-8'))
    except:
      return False
    if data.get('confirm') != self.id:
      return False
    self.confirmed = True
    db.session.add(self)
    return True

  def generate_reset_token(self, expiration = 3600):
    s = Serializer(current_app.config['SECRET_KEY'], expires_in = expiration)
    return s.dumps({'reset': self.id}).decode('utf-8')

  @staticmethod
  def reset_password(token, new_password):
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
      data = s.loads(token.encode('utf-8'))
    except:
      return False
    user = User.query.get(data.get('reset'))
    if user is None:
      return False
    user.password = new_password
    db.session.add(user)
    return True
  
  def generate_email_change_token(self, new_email, expiration = 3600):
    s = Serializer(current_app.config['SECRET_KEY'], expires_in = expiration)
    return s.dumps({
      'change_email': self.id,
      'new_email': new_email
    }).decode('utf-8')
  
  def change_email(self, token):
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
      data = s.loads(token.encode('utf-8'))
    except:
      return False
    if data.get('change_email') != self.id:
      return False
    new_email = data.get('new_email')
    if new_email is None:
      return False
    if self.query.filter_by(email = new_email).first() is not None:
      return False
    self.email = new_email
    db.session.add(self)
    return True

  def generate_auth_token(self, expiration):
    print(expiration)
    s = Serializer(current_app.config['SECRET_KEY'], expires_in = expiration)
    return s.dumps({'id': self.id}).decode('utf-8')
  
  @staticmethod
  def verify_auth_token(token):
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
      data = s.loads(token.encode('utf-8'))
    except:
      return None
    return User.query.get(data['id'])

  def can(self, permission):
    return self.role is not None and self.role.has_permission(permission)
  
  def is_administrator(self):
    return self.can(Permission.ADMIN)
  
  def ping(self):
    self.last_seen = datetime.utcnow()
    db.session.add(self)
  
  def to_json(self):
    json_user = {
      'id': self.id,
      'username': self.username,
      'manager': self.email == current_app.config['FLASK_ADMIN'],
      'avatar': self.avatar,
      'id_string': self.id_string
    }
    return json_user
  
  def detail(self):
    json_user = self.to_json()
    json_user['comments'] = list(map(lambda x:x.to_json(), self.comments))
    json_user['bbs'] = list(map(lambda x:x.to_json(), self.bbs))
    return json_user

  @staticmethod
  def generate_fake(count = 100):
    from sqlalchemy.exc import IntegrityError
    from random import seed
    import forgery_py

    seed()
    for i in range(count):
      u = User(email=forgery_py.internet.email_address(),
        username=forgery_py.internet.user_name(),
        password=forgery_py.lorem_ipsum.word(),
        confirmed=True,
        name=forgery_py.name.full_name(),
        location=forgery_py.address.city(),
        aboute_me=forgery_py.lorem_ipsum.sentence(),
        member_since=forgery_py.date.date(True))
      db.session.add(u)
      try:
        db.session.commit()
        print('auto create user %s done' % (i + 1))
      except:
        db.session.rollback()

class AnonymousUser(AnonymousUserMixin):
  def can(self, permissions):
    return False
  
  def is_administrator(self):
    return False

class Post(db.Model):
  __tablename__ = 'posts'
  id = db.Column(db.Integer, primary_key = True)
  title = db.Column(db.Text)
  body = db.Column(db.Text)
  body_html = db.Column(db.Text)
  hide = db.Column(db.Boolean, default = False)
  secretCode = db.Column(db.Text, default = '')
  abstract = db.Column(db.Text)
  abstract_image = db.Column(db.Text())
  timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
  author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
  type_id = db.Column(db.Integer, db.ForeignKey('post_type.id'))
  tags = db.relationship('Tag',
    secondary = post_tag_relations,
    backref = db.backref('tags', lazy = 'dynamic'),
    lazy='dynamic')
  comments = db.relationship('Comment', backref = 'post', lazy = 'dynamic')
  read_times = db.Column(db.Integer, default = 0)
  likes = db.relationship('Like', backref = 'post', lazy = 'dynamic')

  @staticmethod
  def on_change_body(target, value, oldvalue, initiator):
    pass

  def to_json(self):
    json_post = {
      'id': self.id,
      'author_id': self.author.id,
      'title': self.title,
      'abstract': self.abstract,
      'hide': self.hide,
      'body': self.body,
      'body_html': self.body_html,
      'timestamp': time.mktime(self.timestamp.timetuple()),
      'read_times': self.read_times,
      'likes': self.likes.count(),
      'tags': list(map(lambda x : x.id, self.tags)),
      'type': self.type_id,
      'abstract_image': self.abstract_image
    }
    return json_post
  
  def abstract_json(self):
    json_post = {
      'id': self.id,
      'author_id': self.author.id,
      'title': self.title,
      'timestamp': time.mktime(self.timestamp.timetuple()),
      'abstract': self.abstract,
      'read_times': self.read_times,
      'likes': self.likes.count(),
      'comment_times': self.comments.count(),
      'tags': list(map(lambda x : x.id, self.tags)),
      'type': self.type_id,
      'abstract_image': self.abstract_image
    }
    return json_post

  def comments_json(self):
    comments = list(map(lambda x : x.to_json(), self.comments))
    return comments

  @staticmethod
  def generate_fake(count=100):
    from random import seed, randint
    import forgery_py

    seed()
    user_count = User.query.count()
    type_count = PostType.query.count()
    for i in range(count):
      u = User.query.offset(randint(0, user_count - 1)).first()
      postType = PostType.query.offset(randint(0, type_count - 1)).first()
      p = Post(body=forgery_py.lorem_ipsum.sentences(randint(50, 100)),
        read_times=randint(0, 100),
        title=forgery_py.lorem_ipsum.sentences(1),
        abstract=forgery_py.lorem_ipsum.sentences(randint(5, 20)),
        timestamp=forgery_py.date.date(True),
        type=postType,
        author=u)
      db.session.add(p)
      try:
        db.session.commit()
        print('auto create post %s done' % (i + 1))
      except:
        db.session.rollback()

class Comment(db.Model):
  __tablename__ = 'comments'
  id = db.Column(db.Integer, primary_key = True)
  body = db.Column(db.Text)
  post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
  author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
  comments = db.relationship('Comment', backref = db.backref('response', remote_side=[id]))
  response_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
  timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
  
  def to_json(self):
    return {
      'id': self.id,
      'post_id': self.post_id,
      'post_title': self.post.title,
      'author_id': self.author_id,
      'body': self.body,
      'response_id': self.response_id,
      'response_author_id': self.response.author_id if self.response_id else 0,
      'timestamp': time.mktime(self.timestamp.timetuple())
    }

  @staticmethod
  def generate_fake(count=100):
    from random import seed, randint
    import forgery_py
    
    seed()
    user_count = User.query.count()
    post_count = Post.query.count()
    for i in range(count):
      u = User.query.offset(randint(0, user_count - 1)).first()
      p = Post.query.offset(randint(0, post_count - 1)).first()
      comment = Comment(body=forgery_py.lorem_ipsum.sentences(randint(2,5)),
        timestamp=forgery_py.date.date(True),
        author=u,
        post=p
      )
      db.session.add(comment)
      try:
        db.session.commit()
        print('auto create comment %s done' % (i + 1))
      except:
        db.session.rollback()

class Like(db.Model):
  __tabname__ = 'likes'
  id = db.Column(db.Integer, primary_key = True)
  post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
  author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
  timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)

  @staticmethod
  def generate_fake(count=100):
    from random import seed, randint
    import forgery_py
    
    seed()
    user_count = User.query.count()
    post_count = Post.query.count()
    for i in range(count):
      u = User.query.offset(randint(0, user_count - 1)).first()
      p = Post.query.offset(randint(0, post_count - 1)).first()
      like = Like(timestamp=forgery_py.date.date(True), author=u, post=p)
      db.session.add(like)
      try:
        db.session.commit()
        print('auto create like %s done' % ( i + 1 ))
      except:
        db.session.rollback()

class Tag(db.Model):
  __tablename__ = 'tags'
  id = db.Column(db.Integer, primary_key = True)
  name = db.Column(db.String(64))
  alias = db.Column(db.String(64), unique = True)

  def to_json(self):
    return {
      'id': self.id,
      'name': self.name,
      'alias': self.alias
    }

class PostType(db.Model):
  __tablename__ = 'post_type'
  id = db.Column(db.Integer, primary_key = True)
  name = db.Column(db.String(64))
  alias = db.Column(db.String(64), unique = True)
  posts = db.relationship("Post", backref='type')

  def to_json(self):
    return {
      'id': self.id,
      'name': self.name,
      'alias': self.alias
    }

class BBS(db.Model):
  __tablename__ = 'bbs'
  id = db.Column(db.Integer, primary_key = True)
  body = db.Column(db.Text)
  author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
  timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
  comments = db.relationship('BBS', backref = db.backref('response', remote_side=[id]))
  response_id = db.Column(db.Integer, db.ForeignKey('bbs.id'))
  root_id = db.Column(db.Integer)

  def to_json(self):
    return {
      'id': self.id,
      'author_id': self.author_id,
      'response_author_id': self.response.author_id if self.response_id else 0,
      'response_id': self.response_id,
      'timestamp': time.mktime(self.timestamp.timetuple()),
      'body': self.body
    }