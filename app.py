#!/usr/bin/env python2
#Copyright (C) 2014, Cameron Brandon White
# -*- coding: utf-8 -*-

import argparse 
import urlparse
import urllib
import logging
import os

import flask
from flask import Flask

import flask_bootstrap

app = Flask(__name__)
flask_bootstrap.Bootstrap(app)
app.logger.addHandler(logging.StreamHandler())
app.secret_key = os.environ.get('SECRET_KEY', None)
app.config['cas_server'] = os.environ.get('CAS_SERVER', None)

@app.route('/')
def route_root():
    return flask.render_template(
        'layout.html',
        username = flask.session.get('username', None),
    )

@app.route('/login/')
def route_login():
    """
    This route is has two purposes. First, it is used by the user 
    to login. Second, it is used by the CAS to respond with the 
    `ticket` after the user logins in successfully.

    When the user accesses this url they are redirected to the CAS
    to login. If the login was successful the CAS will respond to this
    route with the ticket in the url. The ticket this then validated. 
    If validation was successful the logged in username is saved in 
    the user's session under the key `username`.
    """

    if 'ticket' in flask.request.args:
        flask.session['_cas_token'] = flask.request.args['ticket']

    if '_cas_token' in flask.session:

        if validate(flask.session['_cas_token']):
            redirect_url = flask.url_for('route_root')
        else:
            redirect_url = create_cas_login_url(app.config['cas_server'])
            del flask.session['_cas_token']
    else:
        redirect_url = create_cas_login_url(app.config['cas_server'])

    app.logger.debug('Redirecting to: {}'.format(redirect_url))

    return flask.redirect(redirect_url)

@app.route('/logout/')
def route_logout():
    """
    When the user accesses this route they are logged out.
    """
    if 'username' in flask.session:
        del flask.session['username']
    redirect_url = create_cas_logout_url(app.config['cas_server'])
    app.logger.debug('Redirecting to: {}'.format(redirect_url))
    return flask.redirect(redirect_url)

def create_cas_login_url(cas_url):
    service_url = urllib.quote(
        flask.url_for('route_login',_external=True))
    return urlparse.urljoin(
        cas_url, 
        '/cas/?service={}'.format(service_url))

def create_cas_logout_url(cas_url):
    url = urllib.quote(flask.url_for('route_login', _external=True))
    return urlparse.urljoin(
        cas_url,
        '/cas/logout?url={}'.format(url))

def create_cas_validate_url(cas_url, ticket):
    service_url = urllib.quote(
        flask.url_for('route_login',_external=True))
    ticket = urllib.quote(ticket)
    return urlparse.urljoin(
        cas_url,
        '/cas/validate?service={}&ticket={}'.format(service_url, ticket))

def validate(ticket):
    """
    Will attempt to validate the ticket. If validation fails False 
    is returned. If validation is successful then True is returned 
    and the validated username is saved in the session under the 
    key `username`.
    """

    app.logger.debug("validating token {}".format(ticket))

    cas_validate_url = create_cas_validate_url(
        app.config['cas_server'], ticket)
    
    app.logger.debug("Making GET request to {}".format(
        cas_validate_url))

    try:
        (isValid, username) = urllib.urlopen(cas_validate_url).readlines()
        isValid = True if isValid.strip() == 'yes' else False
        username = username.strip()
    except ValueError:
        app.logger.error("CAS returned unexpected result")
        isValid = False

    if isValid:
        app.logger.debug("valid")
        flask.session['username'] = username
    else:
        app.logger.debug("invalid")

    return isValid

def create_parser():

    parser = argparse.ArgumentParser(
        description="", 
    )
    parser.add_argument(
       "--host", "-H",
       type=str,
       default=None,
    )
    parser.add_argument(
       "--port", "-P",
       type=int,
       default=None,
    )
    parser.add_argument(
       "--debug", "-D",
       type=bool,
       default=False,
    )
    parser.add_argument(
       "--cas_server", "-c",
       type=str,
       required=True,
    )
    parser.add_argument(
        "--secret_key", "-S",
        type=str,
        default="DEFAULT SECRET KEY",
    )
    return parser

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    app.secret_key = args.secret_key
    app.config['cas_server'] = args.cas_server
    app.run(
        host=args.host, 
        port=args.port,
        debug=args.debug,
    )
