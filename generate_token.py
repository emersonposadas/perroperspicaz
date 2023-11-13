import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def generate_token():
    creds = None
    token_file = 'token.pickle'
    client_secrets_file = 'client_secrets.json'
    scopes = ['https://www.googleapis.com/auth/youtube']

    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
    creds = flow.run_local_server(port=8080)

    with open(token_file, 'wb') as token:
        pickle.dump(creds, token)
    print("token.pickle file has been created successfully.")

if __name__ == "__main__":
    generate_token()
