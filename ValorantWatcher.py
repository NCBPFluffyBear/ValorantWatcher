import requests
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import cloudscraper
import re


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


global access, entitlements, puuid, scraper


def seleniumLogin():
    global access
    driver = webdriver.Firefox()
    driver.get(
        'https://auth.riotgames.com/authorize?redirect_uri=https%3A%2F%2Fplayvalorant.com%2Fopt_in%2F&client_id=play'
        '-valorant-web-prod&response_type=token%20id_token&nonce=1&scope=account%20openid'
    )

    try:
        WebDriverWait(driver, 60).until(EC.url_contains('access_token='))
    except TimeoutException:
        print(f'{bcolors.FAIL}Failed to detect user login with 60 seconds. Quitting...{bcolors.ENDC}')
        exit()

    # Some half-assed regex
    access = re.match('^.*access_token=(.*)&scope=.*$', driver.current_url).groups()[0]


def getEntitlements(retry):
    global entitlements

    headers = {
        'Authorization': 'Bearer ' + access,
        'Content-Type': 'application/json',
        'User-Agent': ''
    }

    response = scraper.post('https://entitlements.auth.riotgames.com/api/token/v1', headers=headers)

    if response.status_code != 200:
        if retry:
            print(f'{bcolors.WARNING}Unable to get entitlements token. Retrying...{bcolors.ENDC}')
            getEntitlements(False)
            return
        print(f'{bcolors.FAIL}Unable to get entitlements token. Try restarting the script?{bcolors.ENDC}')
        exit()

    entitlements = response.json()['entitlements_token']


def getUserInfo():
    global puuid

    headers = {
        'Authorization': 'Bearer ' + access,
        'Content-Type': 'application/json',
        'User-Agent': ''
    }

    response = scraper.post('https://auth.riotgames.com/userinfo', headers=headers)

    if response.status_code != 200:
        return False

    puuid = response.json()['sub']
    return True


# Load token from file or get from user login
def loadTokens():
    global access
    # Generate tokens file
    try:
        config = open('tokens.txt', 'x')
        config.close()
    except OSError:  # File already created, read instead
        pass

    # Read in token
    with open('tokens.txt', 'r') as config:
        access = config.readline()

    # Token has not been generated yet
    if len(access) == 0:
        seleniumLogin()
        print(f'{bcolors.OKGREEN}Loaded Access Token from login{bcolors.ENDC}', access)
        # Write tokens to config
        with open('tokens.txt', 'w') as config:
            config.write(access)
    else:
        print(f'{bcolors.OKGREEN}Loaded Access Token from config{bcolors.ENDC}', access)

    # Check token still valid
    if not getUserInfo():
        print(f'{bcolors.WARNING}Token is wrong or expired, rerequesting...{bcolors.ENDC}', access)
        seleniumLogin()
        getEntitlements(True)
        getUserInfo()
    else:
        getEntitlements(True)
        # Skip token and puuid, already loaded

    print(f'{bcolors.OKGREEN}Loaded Entitlements{bcolors.ENDC}', entitlements)
    print(f'{bcolors.OKGREEN}Loaded PUUID{bcolors.ENDC}', puuid)


def getCurrentMatch():
    headers = {
        'Authorization': 'Bearer ' + access,
        'X-Riot-Entitlements-JWT': entitlements
    }

    response = scraper.get('https://glz-na-1.na.a.pvp.net/core-game/v1/players/' + puuid, headers=headers)

    if response.status_code != 200:
        return None

    return response.json()['MatchID']


def getMatchData(matchID):
    headers = {
        'Authorization': 'Bearer ' + access,
        'X-Riot-Entitlements-JWT': entitlements
    }

    response = scraper.get('https://glz-na-1.na.a.pvp.net/core-game/v1/matches/' + matchID, headers=headers)

    if response.status_code != 200:
        return None

    return response.json()


if __name__ == '__main__':
    session = requests.Session()
    scraper = cloudscraper.create_scraper(sess=session)

    # Loads in user and entitlements tokens
    loadTokens()

    matchID = getCurrentMatch()
    if matchID is not None:
        print(getMatchData(matchID))
