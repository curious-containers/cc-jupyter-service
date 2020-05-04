import functools

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from cc_jupyter_service.common.helper import normalize_url, check_agency, AgencyError
from cc_jupyter_service.service.db import DatabaseAPI

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        agency_url = normalize_url(request.form['agency_url'])
        agency_username = request.form['username']
        agency_password = request.form['password']

        error = None
        try:
            check_agency(agency_url, agency_username, agency_password)
        except AgencyError as e:
            error = str(e)

        database_api = DatabaseAPI.create()

        if error is None:
            user = database_api.get_user(agency_username=agency_username)
            if user is None:
                user_id = database_api.create_user(agency_username, agency_url)
            else:
                user_id = user.user_id

            session.clear()
            session['user_id'] = user_id
            return redirect(url_for('index'))

        flash(error)
    return render_template('login.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        database_api = DatabaseAPI.create()
        g.user = database_api.get_user(user_id=user_id)


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)
    return wrapped_view

