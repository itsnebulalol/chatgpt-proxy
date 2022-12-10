# ChatGPT Proxy

Handles auth and prompts

# How to use

1. Clone this repo
2. Copy `config.example.json` to `config.json`
3. Edit the values in `config.json`
   - If you don't have 2captcha, you can edit the code to not use it. However, you need to get lucky that Auth0 won't give you a captcha.
4. Install requirements
5. Run app.py!

The server will be running on port 6000.

# Sending requests

To give ChatGPT a prompt, you can POST `/prompt`. Here is an example JSON body:
```json
{
    "id": "65c5f9f9-ad25-4e7a-8807-86e2805c8560",
    "conversation": null,
    "context": "",
    "prompt": "Hi, how are you?"
}
```

The ID should be randomly generated. You may use context and conversation to keep a conversation.
