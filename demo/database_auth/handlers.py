from textwrap import dedent
from typing import NoReturn

from aiohttp import web

from aiohttp_security import (authorized_userid, check_authorized, check_permission, forget,
                              remember)
from .db_auth import check_credentials


class Web(object):
    index_template = dedent("""
        <!doctype html>
            <head></head>
            <body>
                <p>{message}</p>
                <form action="/login" method="post">
                  Login:
                  <input type="text" name="login">
                  Password:
                  <input type="password" name="password">
                  <input type="submit" value="Login">
                </form>
                <a href="/logout">Logout</a>
            </body>
    """)

    async def index(self, request: web.Request) -> web.Response:
        username = await authorized_userid(request)
        if username:
            template = self.index_template.format(
                message='Hello, {username}!'.format(username=username))
        else:
            template = self.index_template.format(message='You need to login')
        response = web.Response(body=template.encode())
        return response

    async def login(self, request: web.Request) -> NoReturn:
        invalid_resp = web.HTTPUnauthorized(body=b"Invalid username/password combination")
        form = await request.post()
        login = form.get('login')
        password = form.get('password')
        db_engine = request.app["db_engine"]

        if not (isinstance(login, str) and isinstance(password, str)):
            raise invalid_resp

        if await check_credentials(db_engine, login, password):
            response = web.HTTPFound("/")
            await remember(request, response, login)
            raise response

        raise invalid_resp

    async def logout(self, request: web.Request) -> web.Response:
        await check_authorized(request)
        response = web.Response(body=b'You have been logged out')
        await forget(request, response)
        return response

    async def internal_page(self, request: web.Request) -> web.Response:
        await check_permission(request, 'public')
        response = web.Response(
            body=b'This page is visible for all registered users')
        return response

    async def protected_page(self, request: web.Request) -> web.Response:
        await check_permission(request, 'protected')
        response = web.Response(body=b'You are on protected page')
        return response

    def configure(self, app: web.Application) -> None:
        router = app.router
        router.add_route('GET', '/', self.index, name='index')
        router.add_route('POST', '/login', self.login, name='login')
        router.add_route('GET', '/logout', self.logout, name='logout')
        router.add_route('GET', '/public', self.internal_page, name='public')
        router.add_route('GET', '/protected', self.protected_page,
                         name='protected')
