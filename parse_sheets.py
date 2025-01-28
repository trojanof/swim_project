'''Module for google sheets parsing'''
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import httplib2
import pandas as pd
from settings import CREDENTIALS, SCOPES, FILE_ID, CELL_RANGE


def get_service_acc():
    creds_service = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS,
        SCOPES
        ).authorize(httplib2.Http())
    return build('sheets', 'v4', http=creds_service)


def get_df_from_google_sheet(sheet_name):
    data = get_service_acc().spreadsheets().values().get(
        spreadsheetId=FILE_ID,
        range=f"{sheet_name}!{CELL_RANGE}").execute()
    df = pd.DataFrame(data['values'], columns=data['values'][0])
    df = df[1:]
    return df
