import requests
import base64
import tls_client
import urllib
import re
import json
import ssl
import time

from wand.image import Image
from bs4 import BeautifulSoup


def expired_creds() -> bool:
    """
        Check if the creds have expired
        returns:
            bool: True if expired, False if not
    """
    try:
        with open("auth.json", 'r') as f:
            creds = json.load(f)
            expires_at = float(creds['expires_at'])
            if time.time() > expires_at + 3600:
                return True
            else:
                return False
    except FileNotFoundError:
        return True


def get_access_token() -> str:
    """
        Get the access token
        returns:
            str: The access token
    """
    try:
        with open("auth.json", 'r') as f:
            creds = json.load(f)
            return creds['access_token']
    except FileNotFoundError:
        return ""


class OpenAIAuth:
    # Credit to https://github.com/rawandahmad698/PyChatGPT
    # Modified for 2captcha support, thanks nyuszika7h
    def __init__(self, email_address: str, password: str, use_proxy: bool = False, proxy: str = None):
        self.email_address = email_address
        self.password = password
        self.use_proxy = use_proxy
        self.proxy = proxy
        self.session = tls_client.Session(
            client_identifier="chrome_105"
        )
        self.access_token: str = None

    @staticmethod
    def url_encode(string: str) -> str:
        """
        URL encode a string
        :param string:
        :return:
        """
        return urllib.parse.quote(string)

    def begin(self):
        """
            Begin the auth process
        """
        print("Begin")
        if not self.email_address or not self.password:
            return
        else:
            if self.use_proxy:
                if not self.proxy:
                    return

                proxies = {
                    "http": self.proxy,
                    "https": self.proxy
                }
                self.session.proxies(proxies)

        # First, make a request to https://chat.openai.com/auth/login
        url = "https://chat.openai.com/auth/login"
        headers = {
            "Host": "ask.openai.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

        response = self.session.get(url=url, headers=headers)
        if response.status_code == 200:
            self.part_two()
        else:
            return
            # TODO: Add error handling

    def part_two(self):
        """
        In part two, We make a request to https://chat.openai.com/api/auth/csrf and grab a fresh csrf token
        """
        print("Part 2")

        url = "https://chat.openai.com/api/auth/csrf"
        headers = {
            "Host": "ask.openai.com",
            "Accept": "*/*",
            "Connection": "keep-alive",
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Referer": "https://chat.openai.com/auth/login",
            "Accept-Encoding": "gzip, deflate, br",
        }
        response = self.session.get(url=url, headers=headers)
        if response.status_code == 200 and 'json' in response.headers['Content-Type']:
            csrf_token = response.json()["csrfToken"]
            self.part_three(token=csrf_token)
        else:
            return

    def part_three(self, token: str):
        """
        We reuse the token from part to make a request to /api/auth/signin/auth0?prompt=login
        """
        print("Part 3")
        url = "https://chat.openai.com/api/auth/signin/auth0?prompt=login"

        payload = f'callbackUrl=%2F&csrfToken={token}&json=true'
        headers = {
            'Host': 'ask.openai.com',
            'Origin': 'https://chat.openai.com',
            'Connection': 'keep-alive',
            'Accept': '*/*',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Referer': 'https://chat.openai.com/auth/login',
            'Content-Length': '100',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = self.session.post(url=url, headers=headers, data=payload)
        print(response.status_code)
        print(response.text)
        if response.status_code == 200 and 'json' in response.headers['Content-Type']:
            url = response.json()["url"]
            self.part_four(url=url)
        elif response.status_code == 400:
            return
        else:
            return

    def part_four(self, url: str):
        """
        We make a GET request to url
        :param url:
        :return:
        """
        print("Part 4")
        headers = {
            'Host': 'auth0.openai.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://chat.openai.com/',
        }
        response = self.session.get(url=url, headers=headers)
        if response.status_code == 302:
            state = re.findall(r"state=(.*)", response.text)[0]
            state = state.split('"')[0]
            self.part_five(state=state)
        else:
            return

    def part_five(self, state: str):
        """
        We use the state to get the login page & check for a captcha
        """
        print("Part 5")
        url = f"https://auth0.openai.com/u/login/identifier?state={state}"

        headers = {
            'Host': 'auth0.openai.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://chat.openai.com/',
        }
        response = self.session.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            if captcha := soup.find("img", alt="captcha"):
                print("Captcha detected, attempting to solve")
                self.solve_captcha(
                    state=state, captcha_b64=captcha["src"].split(",")[-1])
            else:
                self.part_six(state=state, captcha=None)
        else:
            return

    def solve_captcha(self, state: str, captcha_b64: str) -> None:
        with Image(blob=base64.b64decode(captcha_b64)) as img:
            img.format = "png"
            captcha_b64_png = base64.b64encode(img.make_blob()).decode()

            r = requests.post(
                url="https://2captcha.com/in.php",
                json={
                    "key": config["2captcha_api_key"],
                    "method": "base64",
                    "body": captcha_b64_png,
                    "json": "1",
                },
            )
            res = r.json()
            print(res)

            if res["status"] != 1:
                raise ValueError(f"2Captcha API error: {res['request']!r}")

            req_id = res["request"]
            print("Waiting for solution.", end="", flush=True)
            while True:
                time.sleep(5)
                r = requests.get(
                    url="https://2captcha.com/res.php",
                    params={
                        "key": config["2captcha_api_key"],
                        "action": "get",
                        "id": req_id,
                        "json": "1",
                    },
                )

                res = r.json()
                if res["request"] == "CAPCHA_NOT_READY":
                    print(".", end="", flush=True)
                elif res["status"] != 1:
                    raise ValueError(f"2Captcha API error: {res['request']!r}")
                else:
                    print(" Received")
                    self.part_six(state, res["request"])
                    break

    def part_six(self, state: str, captcha: str or None):
        """
        We make a POST request to the login page with the captcha, email
        :param state:
        :param captcha:
        :return:
        """
        print("Part 6")

        url = f"https://auth0.openai.com/u/login/identifier?state={state}"
        email_url_encoded = self.url_encode(self.email_address)
        payload = f'state={state}&username={email_url_encoded}&captcha={captcha}&js-available=true&webauthn-available=true&is-brave=false&webauthn-platform-available=false&action=default'

        if captcha is None:
            payload = f'state={state}&username={email_url_encoded}&js-available=false&webauthn-available=true&is-brave=false&webauthn-platform-available=false&action=default'

        headers = {
            'Host': 'auth0.openai.com',
            'Origin': 'https://auth0.openai.com',
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Referer': f'https://auth0.openai.com/u/login/identifier?state={state}',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = self.session.post(url, headers=headers, data=payload)
        if response.status_code == 302:
            self.part_seven(state=state)
        else:
            print(response.text)
            print(response.status_code)
            print(payload)
            print(response.url)
            return

    def part_seven(self, state: str):
        """
        We enter the password
        :param state:
        :return:
        """
        print("Part 7")

        url = f"https://auth0.openai.com/u/login/password?state={state}"

        email_url_encoded = self.url_encode(self.email_address)
        password_url_encoded = self.url_encode(self.password)
        payload = f'state={state}&username={email_url_encoded}&password={password_url_encoded}&action=default'
        headers = {
            'Host': 'auth0.openai.com',
            'Origin': 'https://auth0.openai.com',
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Referer': f'https://auth0.openai.com/u/login/password?state={state}',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = self.session.post(url, headers=headers, data=payload)
        is_302 = response.status_code == 302
        if is_302:
            new_state = re.findall(r"state=(.*)", response.text)[0]
            new_state = new_state.split('"')[0]
            self.part_eight(old_state=state, new_state=new_state)
        else:
            return

    def part_eight(self, old_state: str, new_state):
        print("Part 8")

        url = f"https://auth0.openai.com/authorize/resume?state={new_state}"
        headers = {
            'Host': 'auth0.openai.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Referer': f'https://auth0.openai.com/u/login/password?state={old_state}',
        }
        response = self.session.get(url, headers=headers, allow_redirects=True)
        is_200 = response.status_code == 200
        if is_200:
            soup = BeautifulSoup(response.text, 'lxml')
            # Find __NEXT_DATA__, which contains the data we need, the get accessToken
            next_data = soup.find("script", {"id": "__NEXT_DATA__"})
            # Access Token
            try:
                access_token = re.findall(
                    r"accessToken\":\"(.*)\"", next_data.text)[0]
                access_token = access_token.split('"')[0]
            except:
                time.sleep(5)
                next_data = soup.find("script", {"id": "__NEXT_DATA__"})
                access_token = re.findall(
                    r"accessToken\":\"(.*)\"", next_data.text)[0]
                access_token = access_token.split('"')[0]

            # Save access_token and an hour from now on auth.json
            self.save_access_token(access_token=access_token)

    def save_access_token(self, access_token: str):
        """
        Save access_token and an hour from now on auth.json
        :param access_token:
        :return:
        """
        self.access_token = access_token

        with open("auth.json", "w+") as f:
            f.write(json.dumps(
                {"access_token": access_token, "expires_at": time.time() + 3600, "email": self.email_address}, indent=4))

    def part_nine(self):
        print("Part 9")

        url = "https://chat.openai.com/api/auth/session"
        headers = {
            "Host": "ask.openai.com",
            "Connection": "keep-alive",
            "If-None-Match": "\"bwc9mymkdm2\"",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Referer": "https://chat.openai.com/chat",
            "Accept-Encoding": "gzip, deflate, br",
        }
        response = self.session.get(url, headers=headers)
        is_200 = response.status_code == 200
        if is_200:
            # Get the session token
            # return response.json()
            pass
