from flask import Flask, session, redirect, url_for, request, render_template, flash, g, abort  # escape
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, NumberRange  # Length, NumberRange
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
manager = Manager(app)
bootstrap = Bootstrap(app)

# Read the configurations
app.config.from_pyfile('config/config.py')
# Contenu typique de config.py. Le vrai fichier devrait être changé.
# SQLALCHEMY_DATABASE_URI = 'sqlite:///data/aliments.db'
# SQLALCHEMY_TRACK_MODIFICATIONS=False
# SECRET_KEY='NotSoSecretKey'
# DEBUG=True

db = SQLAlchemy(app)


# Database Model
class AdminUser(db.Model):
    __tablename__ = 'tadmin_user'
    user_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(30), nullable=False)
    user_email = db.Column(db.String(80), nullable=False, unique=True)
    user_pass = db.Column(db.String(100), nullable=False)
    activated = db.Column(db.Boolean(), nullable=False, default=True)

    def __init__(self, first_name, last_name, user_email, user_pass):
        self.first_name = first_name
        self.last_name = last_name
        self.user_email = user_email
        self.user_pass = user_pass

    def __repr__(self):
        return '<user: {}>'.format(self.user_email)


class Aliment(db.Model):
    __tablename__ = 'taliment'
    id_aliment = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    nom_aliment = db.Column(db.String(30), nullable=False, unique=True)
    desc_aliment = db.Column(db.Text, nullable=True)

    def __init__(self, nom_aliment, desc_aliment):
        self.nom_aliment = nom_aliment
        self.desc_aliment = desc_aliment
        
    def __repr__(self):
        return '<aliment: {}'.format(self.nom_aliment)
    
    
# Formulaire web pour l'écran de login
class LoginForm(FlaskForm):
    email = StringField('Courriel', validators=[DataRequired(), Email(message='Le courriel est invalide.')])
    password = PasswordField('Mot de Passe', [DataRequired(message='Le mot de passe est obligatoire.')])
    request_password_change = BooleanField('Changer le mot de passe?')
    password_1 = PasswordField('Nouveau Mot de passe',
                               [EqualTo('password_2', message='Les mots de passe doivent être identiques.')])
    password_2 = PasswordField('Confirmation')
    submit = SubmitField('Se connecter')


# Formulaire web pour l'écran de register
class RegisterForm(FlaskForm):
    first_name = StringField('Prénom', validators=[DataRequired(message='Le prénom est requis.')])
    last_name = StringField('Nom de famille', validators=[DataRequired(message='Le nom de famille est requis.')])
    email = StringField('Courriel', validators=[DataRequired(), Email(message='Le courriel est invalide.')])
    password_1 = PasswordField('Mot de passe',
                               [DataRequired(message='Le mot de passe est obligatoire.'),
                                EqualTo('password_2', message='Les mots de passe doivent être identiques.')])
    password_2 = PasswordField('Confirmation')
    submit = SubmitField('S\'enrégistrer')


# Formulaire d'ajout d'un aliment
class AjtAlimentForm(FlaskForm):
    nom_aliment = StringField("Nom de l'aliment", validators=[DataRequired(message='Le nom est requis.')])
    desc_aliment = TextAreaField('Description')
    submit = SubmitField('Ajouter')


# Formulaire de modification d'un aliment
class ModAlimentForm(FlaskForm):
    nom_aliment = StringField("Nom de l'aliment", validators=[DataRequired(message='Le nom est requis.')])
    desc_aliment = TextAreaField('Description')
    submit = SubmitField('Modifier')


# Formulaire pour confirmer la suppression d'un aliment
class SupAlimentForm(FlaskForm):
    submit = SubmitField('Supprimer')


# Custom error pages
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


# The following functions are views
@app.route('/')
def index():
    if not logged_in():
        return redirect(url_for('login'))
    app.logger.debug('Entering index()')
    first_name = session.get('first_name', None)
    return render_template('aliment.html', user=first_name)


@app.route('/list_aliments')
def list_aliments():
    if not logged_in():
        return redirect(url_for('login'))
    aliments = Aliment.query.order_by(Aliment.nom_aliment).all()
    return render_template('list_aliments.html', aliments=aliments)


@app.route('/ajt_aliment', methods=['GET', 'POST'])
def ajt_aliment():
    if not logged_in():
        return redirect(url_for('login'))
    app.logger.debug('Entering ajt_aliment')
    form = AjtAlimentForm()
    if form.validate_on_submit():
        nom_aliment = request.form['nom_aliment']
        desc_aliment = request.form['desc_aliment']
        if db_ajt_aliment(nom_aliment, desc_aliment):
            flash("L'aliment a été ajouté.")
            return redirect(url_for('list_aliments'))
        else:
            flash('Une erreur de base de données est survenue.')
            abort(500)
    return render_template('ajt_aliment.html', form=form)


@app.route('/sup_aliment/<int:id_aliment>', methods=['GET', 'POST'])
def sup_aliment(id_aliment):
    if not logged_in():
        return redirect(url_for('login'))
    form = SupAlimentForm()
    if form.validate_on_submit():
        app.logger.debug('supacer un aliment')
        if db_sup_aliment(id_aliment):
            flash("L'aliment a été supacé.")
        else:
            flash("Quelque chose n'a pas fonctionné.")
        return redirect(url_for('list_aliments'))
    else:
        alim = Aliment.query.get(id_aliment)
        if alim:
            return render_template('sup_aliment.html', form=form, nom_aliment=alim.nom_aliment)
        else:
            flash("L'information n'a pas pu être retrouvée.")
            return redirect(url_for('list_aliments'))


@app.route('/mod_aliment/<int:id_aliment>', methods=['GET', 'POST'])
def mod_aliment(id_aliment):
    if not logged_in():
        return redirect(url_for('login'))
    session['id_aliment'] = id_aliment
    form = ModAlimentForm()
    if form.validate_on_submit():
        app.logger.debug('Mettre a jour aliment')
        nom_aliment = form.nom_aliment.data
        desc_aliment = form.desc_aliment.data
        if db_mod_aliment(id_aliment, nom_aliment, desc_aliment):
            flash("L'aliment a été modifiée.")
        else:
            flash("Quelque chose n'a pas fonctionné.")
        return redirect(url_for('list_aliments'))
    else:
        alim = Aliment.query.get(id_aliment)
        if alim:
            form.nom_aliment.data = alim.nom_aliment
            form.desc_aliment.data = alim.desc_aliment
#            sections = Section.query.filter_by(checklist_id=checklist_id, deleted_ind='N') \
#                .order_by(Section.section_seq).all()
#            cl_vars = Checklist_Var.query.filter_by(checklist_id=checklist_id).order_by(Checklist_Var.var_id).all()
#            for cl_v in cl_vars:
#                pr_v = Predef_Var.query.get(cl_v.var_id)
#                cl_v.var_name = pr_v.var_name
#                cl_v.var_desc = pr_v.var_desc
            return render_template("mod_aliment.html", form=form, alim=alim)
        else:
            flash("L'information n'a pas pu être retrouvée.")
            return redirect(url_for('list_aliments'))


@app.route('/aff_aliment/<int:id_aliment>')
def aff_aliment(id_aliment):
    if not logged_in():
        return redirect(url_for('login'))
    alim = Aliment.query.get(id_aliment)
    if alim:
        return render_template("aff_aliment.html", alim=alim)

    else:
        flash("L'information n'a pas pu être retrouvée.")
        return redirect(url_for('list_aliments'))


@app.route('/list_categories')
def list_categories():
    if not logged_in():
        return redirect(url_for('login'))
    abort(404)
    #aliments = Aliment.query.filter_by(deleted_ind='N').order_by(Aliment.nom_aliment).all()
    #return render_template('list_aliments.html', aliments=aliments)


@app.route('/list_bienfaits')
def list_bienfaits():
    if not logged_in():
        return redirect(url_for('login'))
    abort(404)


@app.route('/login', methods=['GET', 'POST'])
def login():
    app.logger.debug('Entering login()')
    form = LoginForm()
    if form.validate_on_submit():
        user_email = request.form['email']
        password = request.form['password']
        if db_validate_user(user_email, password):
            session['active_time'] = datetime.now()
            request_pwd_change = request.form.get('request_password_change', None)
            if request_pwd_change:
                app.logger.debug("Changer le mot de passe")
                new_password = request.form['password_1']
                change_password(user_email, new_password)
            return redirect(url_for('index'))
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    app.logger.debug('Entering logout()')
    session.pop('first_name', None)
    session.pop('last_name', None)
    session.pop('user_email', None)
    session.pop('active_time', None)
    flash('Vous êtes maintenant déconnecté.')
    return redirect(url_for('index'))


def logged_in():
    user_email = session.get('user_email', None)
    if user_email:
        active_time = session['active_time']
        delta = datetime.now() - active_time
        if (delta.days > 0) or (delta.seconds > 1800):
            flash('Votre session est expirée.')
            return False
        session['active_time'] = datetime.now()
        return True
    else:
        return False


@app.route('/register', methods=['GET', 'POST'])
def register():
    app.logger.debug('Entering register')
    form = RegisterForm()
    if form.validate_on_submit():
        app.logger.debug('Inserting a new registration')
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        user_email = request.form['email']
        user_pass = generate_password_hash(request.form['password_1'])
        if user_exists(user_email):
            flash('Cet usager existe déjà. Veuillez vous connecter.')
            return redirect(url_for('login'))
        else:
            user = AdminUser(first_name, last_name, user_email, user_pass)
            db.session.add(user)
            db.session.commit()
            flash('Revenez quand votre compte sera activé.')
            return redirect(url_for('index'))
    return render_template('register.html', form=form)


def user_exists(user_email):
    app.logger.debug('Entering user_exists with: ' + user_email)
    user = AdminUser.query.filter_by(user_email=user_email).first()
    if user is None:
        app.logger.debug('user_exists returns False')
        return False
    else:
        app.logger.debug('user_exists returns True' + user[0])
        return True


# Validate if a user is defined in tadmin_user with the proper password.
def db_validate_user(user_email, password):
    user = AdminUser.query.filter_by(user_email=user_email).first()
    if user is None:
        flash("L'usager n'existe pas.")
        return False

    if not user.activated:
        flash("L'usager n'est pas activé.")
        return False

    if check_password_hash(user.user_pass, password):
        session['user_email'] = user.user_email
        session['first_name'] = user.first_name
        session['last_name'] = user.last_name
        return True
    else:
        flash("Mauvais mot de passe!")
        return False


def change_password(user_email, new_password):
    user = AdminUser.query.filter_by(user_email=user_email).first()
    if user is None:
        flash("Mot de passe inchangé. L'usager n'a pas été retrouvé.")
    else:
        user.user_pass = generate_password_hash(new_password)
        db.session.commit()
        flash("Mot de passe changé.")


def db_ajt_aliment(nom_aliment, desc_aliment):
    alim = Aliment(nom_aliment, desc_aliment)
    try:
        db.session.add(alim)
        db.session.commit()
    except Exception as e:
        app.logger.error('DB Error' + str(e))
        return False
    return True


def db_sup_aliment(id_aliment):
    alim = Aliment.query.get(id_aliment)
    try:
        db.session.delete(alim)
        db.session.commit()
    except Exception as e:
        app.logger.error('DB Error' + str(e))
        return False
    return True


def db_mod_aliment(id_aliment, nom_aliment, desc_aliment):
    alim = Aliment.query.get(id_aliment)
    alim.nom_aliment = nom_aliment
    alim.desc_aliment = desc_aliment
    try:
        db.session.commit()
    except Exception as e:
        app.logger.error('DB Error' + str(e))
        return False
    return True


# Start the server for the application
if __name__ == '__main__':
    manager.run()