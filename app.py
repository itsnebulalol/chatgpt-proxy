import requests
import json
import auth
import time
import random

from flask import Flask, request


app = Flask(__name__)

with open("config.json", "r") as f:
    global config
    config = json.load(f)

with open("auth.json", "r") as f:
    global auth_file
    auth_file = json.load(f)


def refresh_token():
    choice = None
    while choice is None:
        c = random.choice(config["accounts"])
        try:
            if c != auth_file["email"]:
                choice = c
        except KeyError:
            choice = c

    print(f"Logging in with {choice['email']}")

    open_ai_auth = auth.OpenAIAuth(
        email_address=choice['email'], password=choice['password'])
    open_ai_auth.begin()
    time.sleep(3)
    is_still_expired = auth.expired_creds()

    if is_still_expired:
        print(f"Failed to refresh credentials. Please try again.")
        exit(1)
    else:
        print(f"Successfully refreshed credentials.")

    if auth.get_access_token() == "":
        print(f"Access token is missing in auth.json.")
        exit(1)


expired_creds = auth.expired_creds()
if expired_creds:
    refresh_token()
else:
    print(f"Valid credentials found.")

if auth.get_access_token() == "":
    print(f"Access token is missing in auth.json.")
    exit(1)


@app.route('/')
def root():
    return 'Hello, World!'


@app.route('/prompt', methods=['POST'])
def prompt():
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header == f"Bearer {config['api_key']}":
        pass
    else:
        err = {
            'status': 'error',
            'error': 'You are not authorized to use this endpoint. Please make sure your API key is correct.'
        }

        return json.loads(json.dumps(err, indent=4))

    content = request.get_json()

    headers = {
        'Authorization': f'Bearer {auth.get_access_token()}',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
    }

    json_data = {
        'action': 'next',
        'conversation_id': content["conversation"],
        'messages': [
            {
                'id': content["id"],
                'role': 'user',
                'content': {
                    'content_type': 'text',
                    'parts': [
                        content["prompt"],
                    ],
                },
            },
        ],
        'parent_message_id': content["context"],
        'model': 'text-davinci-002-render',
    }

    res = requests.post(
        'https://chat.openai.com/backend-api/conversation', headers=headers, json=json_data)

    if res.status_code == 200:
        text = res.text

        return json.loads(text.splitlines()[-4].replace("data: ", ""))
    else:
        text = res.text

        # Some error parsing
        print(text)
        j = json.loads(text)
        try:
            if "Too many requests" in j["detail"]:
                err = {
                    'status': 'error',
                    'error': "We're rate limited! We're going to attempt to swap accounts... give us a moment and retry."
                }

                refresh_token()
                access_token = auth.get_access_token()

                return json.loads(json.dumps(err, indent=4))
        except KeyError:
            if j["message"]["code"] == "token_expired":
                err = {
                    'status': 'error',
                    'error': "The token expired! We're going to refresh it... give us a moment and retry."
                }

                refresh_token()
                access_token = auth.get_access_token()

                return json.loads(json.dumps(err, indent=4))
            elif "Rate limit reached" in j["message"]["code"]:
                err = {
                    'status': 'error',
                    'error': "Rate limit reached for the minute... please try again in a minute."
                }

                return json.loads(json.dumps(err, indent=4))

        err = {
            'status': 'error',
            'error': text
        }

        return json.loads(json.dumps(err, indent=4))


@app.route('/refresh_auth', methods=['GET'])
def refresh_auth():
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header == f"Bearer {config['api_key']}":
        pass
    else:
        err = {
            'status': 'error',
            'error': 'You are not authorized to use this endpoint. Please make sure your API key is correct.'
        }

        return json.loads(json.dumps(err, indent=4))

    refresh_token()
    access_token = auth.get_access_token()

    if access_token == "":
        err = {
            'status': 'error',
            'error': 'An error occurred refreshing the auth token, please check proxy console.'
        }

        return json.loads(json.dumps(err, indent=4))
    else:
        done = {
            'status': 'success',
            'error': 'Done! Refreshed your auth token!'
        }

        return json.loads(json.dumps(done, indent=4))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="6000")
