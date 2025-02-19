'''Settings for the project'''

CREDENTIALS = "./creds/so.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
FILE_ID = '1ZxnKEqeTQnlPTLofqv_ZhhvOZnxvwO61kHyQPCkVs1g'
METERS_SHEET_NAME = 'МетрыV2'
LOCATIONS_SHEET_NAME = 'Локации'
CELL_RANGE = 'A1:AB1000'

with open('greeting_message.txt', 'r') as f:
    txt = f.read()
INTRO_MESSAGE = txt
CLUB_URL = 'https://swimocean.ru/'
INFO_URL = ("https://vc.ru/travel/"
            "1053812-klub-oceans-seven-ekstremalnye-zaplyvy-na-otkrytoi-vode")
DEFAULT_START_CAPTION = 'Точка старта'
DEFAULT_FINISH_CAPTION = 'Точка финиша'
START_DATE = '13-01-2025'
