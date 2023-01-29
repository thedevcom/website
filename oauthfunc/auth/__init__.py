import os
import json
import random
import string
import requests
import logging
from azure.functions import HttpRequest, HttpResponse

def main(req: HttpRequest) -> HttpResponse:
    client_id = os.environ.get("OAUTH_CLIENT_ID", "your_client_id")
    client_secret = os.environ.get("OAUTH_CLIENT_SECRET", "your_client_secret")
    redirect_uri = os.environ.get("OAUTH_REDIRECT_URI", "http://127.0.0.1:3000/api/callback")
    state = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
    scope = os.environ.get('OAUTH_SCOPES', 'repo,user')

    # Check if the request is for the authorization code
    if req.params.get("code"):
        # Log the request parameters
        logging.info(f'Received request with code: {req.params.get("code")}')
        # Exchange the authorization code for an access token
        code = req.params.get("code")
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": f'{redirect_uri}/callback',
            "state": state,
            "scope": scope
        }
        headers = {
            "Accept": "application/json"
        }
        response = requests.post("https://github.com/login/oauth/access_token", data=data, headers=headers)
        response_data = json.loads(response.text)
        logging.info(f'Received response: {response_data}')
        # Check if the access token is valid
        if "access_token" in response_data:
            access_token = response_data["access_token"]
            headers = {
                # "Authorization": f"token {access_token}",
                "content-type':'text/html"
            }
            content = json.dumps(
                {'token': access_token, 'provider': 'github'})
            message = 'success'

            post_message = json.dumps(
                'authorization:github:{0}:{1}'.format(message, content))
            # print(post_message)
            response = """<!DOCTYPE html><html><body><script>
            (function() {
            function recieveMessage(e) {
                console.log("recieveMessage %o", e)
                // send message to main window with da app
                window.opener.postMessage(
                """+post_message+""",
                e.origin
                )
            }
            window.addEventListener("message", recieveMessage, false)
            // Start handshare with parent
            console.log("Sending message: %o", "github")
            window.opener.postMessage("authorizing:github", "*")
            })()
            </script></body></html>"""
        
            # Return the user data
            return HttpResponse(body=response, status_code=200, headers={"content-type":"text/html"})
        else:
            # Return an error message
            logging.error("Invalid access token")
            return HttpResponse("Invalid access token", status_code=400)
    elif req.params.get("error"):
        # Return an error message
        error_message = req.params.get("error_description")
        logging.error(f'Error: {error_message}')
        return HttpResponse(error_message, status_code=400)
    else:
        # Redirect the user to the GitHub OAuth2 authorize page
        authorize_url = f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&state={state}"
        logging.info(f'Redirecting user to {authorize_url}')
        return HttpResponse(status_code=302, headers={"Location": authorize_url})
