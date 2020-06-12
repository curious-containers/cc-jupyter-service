import functools

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from cc_jupyter_service.common.conf import Conf
from cc_jupyter_service.common.helper import normalize_url, check_agency, AgencyError
from cc_jupyter_service.service.db import DatabaseAPI

bp = Blueprint('auth', __name__, url_prefix='/auth')
conf = Conf.from_system()


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        agency_url = normalize_url(request.form['agencyUrl'])
        agency_username = request.form['agencyUsername']
        agency_password = request.form['agencyPassword']

        error = None
        authorization_cookie = None
        try:
            authorization_cookie = check_agency(agency_url, agency_username, agency_password)
        except AgencyError as e:
            error = str(e)

        database_api = DatabaseAPI.create()

        if error is None:
            # get/create user
            user = database_api.get_user(agency_username=agency_username)
            if user is None:
                user_id = database_api.create_user(agency_username, agency_url)
            else:
                user_id = user.user_id

            # save authorization cookie
            if authorization_cookie is not None:
                database_api.create_cookie(authorization_cookie, user_id)

            session.clear()
            session['user_id'] = user_id
            return redirect(url_for('root'))

        flash(error)
    return render_template('login.html', predefinedAgencyUrls=conf.predefined_agency_urls)


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('root'))


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

