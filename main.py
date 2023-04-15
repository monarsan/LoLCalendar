import requests
import urllib.parse
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os
import logging

load_dotenv()
RIOT_API_KEY = os.getenv('RIOT_API_KEY')
SCOPES = ['https://www.googleapis.com/auth/calendar.events.owned']
SERVICE_ACCOUNT_FILE = 'service.json'
calendar_id = os.getenv('CALENDAR_ID')
summoner_name = os.getenv('SUMMONER_NAME')
headers = {'X-Riot-Token': RIOT_API_KEY}


def get_puuid(summoner_name):
    """
    Returns:
        puuid of summoner
    """    
    summoner_name = urllib.parse.quote(summoner_name.encode('utf-8'))
    url = 'https://jp1.api.riotgames.com/lol/summoner/v4/summoners/by-name/' + summoner_name
    r = requests.get(url, headers=headers)
    return r.json()['puuid']


def get_match_list(puuid, unix_time):
    """
    Args:
        puuid (str): puuid of summoner
        unix_time (int): unix time in milliseconds or seconds?
    Returns:
        list of match ids
    """
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids'
    query_params = {'startTime': unix_time, 'count': 20}
    r = requests.get(url, headers=headers, params=query_params)
    print('get_match_list====================')
    print(r.json())
    return r.json()


def get_match_info(match_id):
    """
        get one match info from match id
    Returns:
        match info
    """
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/{match_id}'
    r = requests.get(url, headers=headers)
    return r.json()


def get_match_start_time(match_info):
    """
        get match start time from match info
    Returns:
        match start time in datetime
    """
    start_time = datetime.datetime.fromtimestamp(match_info['info']['gameStartTimestamp'] / 1000)
    start_time = start_time.replace(second=0, microsecond=0)
    return start_time


def get_match_duration(match_info):
    return match_info['info']['gameDuration']


def get_match_end_time(match_info):
    """
        get match end time from match info
    Returns:
        match end time in datetime
    """
    end_time = get_match_start_time(match_info) + datetime.timedelta(seconds=get_match_duration(match_info))
    end_time = end_time.replace(second=0, microsecond=0)
    return end_time


def get_last_record_time():
    """
    Returns:
        Tokyo time of last recorded event
    """
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
    one_day_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat() + 'Z'
    query = {
    'calendarId': calendar_id,
    'timeMin': one_day_ago,
    'maxResults': 100,
    'singleEvents': True,
    'orderBy': 'startTime',
    'timeZone': 'Asia/Tokyo'
    }
    event = service.events().list(**query).execute()
    return datetime.datetime.fromisoformat(event['items'][-1]['end']['dateTime'])


def get_match_list_not_recorded(tokyo_time):
    puuid = get_puuid(summoner_name)
    unix_time = int(tokyo_time.timestamp()) + 100 
    matches = get_match_list(puuid, unix_time)
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
    for match in matches:
        match_info = get_match_info(match)
        match_start_time = get_match_start_time(match_info)
        match_end_time = get_match_end_time(match_info)
        game_mode = match_info['info']['gameMode']
        body = {
            'summary': f'LoL: {game_mode}',
            'start': {
                'dateTime': match_start_time.isoformat(),
                'timeZone': 'Japan'
            },
            'end': {
                'dateTime': match_end_time.isoformat(),
                'timeZone': 'Japan'
            },
        }
        event = service.events().insert(calendarId=calendar_id, body=body).execute()
        
if __name__ == '__main__':
    tokyo_time = get_last_record_time()
    get_match_list_not_recorded(tokyo_time)
