'''Module for google sheets parsing'''
import json
from tempfile import TemporaryDirectory
from pathlib import Path
import streamlit as st
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import httplib2
import pandas as pd
from settings import CREDENTIALS, SCOPES, FILE_ID, CELL_RANGE


def get_service_from_var():
    cred_str = st.secrets['CREDS']
    creds_obj = json.loads(cred_str)
    tmp_dir = TemporaryDirectory()
    tmp_dir_path = Path(tmp_dir.name)
    json_path = tmp_dir_path / 'creds.json'
    with open(json_path, 'w') as f:
        json.dump(creds_obj, f)
    creds_service = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS,
        SCOPES
        ).authorize(httplib2.Http())
    tmp_dir.cleanup()
    return build('sheets', 'v4', http=creds_service)


def get_service_acc():
    creds_service = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS,
        SCOPES
        ).authorize(httplib2.Http())
    return build('sheets', 'v4', http=creds_service)


def get_df_from_google_sheet(sheet_name):
    data = get_service_from_var().spreadsheets().values().get(
        spreadsheetId=FILE_ID,
        range=f"{sheet_name}!{CELL_RANGE}").execute()
    df = pd.DataFrame(data['values'], columns=data['values'][0])
    df = df[1:]
    return df
