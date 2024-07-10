import time
import requests
import datetime
from util import util

# Number of seconds to wait after using Last.FM's API
WAIT_SECONDS_AFTER_REQUEST=0.2

class LastFMUnauthenticatedAPI:
    def __init__(self, api_key, api_app_name):
        self.base_url = "http://ws.audioscrobbler.com/2.0/"
        self.api_key = api_key
        self.headers = {"User-Agent": api_app_name}
    
    def get_params(self, **kwargs):
        params = {
            "format": "json",
            "api_key": self.api_key
        }
        params.update(**kwargs)

        return params
    
    def get_request_json(self, params):
        url = util.get_query_url(self.base_url, params)
        r = requests.get(url, headers=self.headers)
        status_code = r.status_code
        if status_code != 200:
            raise ValueError(f"error: status code {status_code}; perhaps you were requesting too quickly?")
        
        return r.json()
    
    def get_getrecenttrack_params(self, user, page):
        params = self.get_params(
            method="user.getRecentTracks",
            limit="1000",
            user=user,
            page=page
        )

        return params
    
    def get_specified_page_scrobbles_from_user(self, user, page):
        """
        Gets a specific page's scrobbles.
        """
        params = self.get_getrecenttrack_params(user, page)
        try:
            r_json = self.get_request_json(params)
            print(r_json["@attr"])
        except:
            # Retry once after waiting double the normal wait time.
            time.sleep(WAIT_SECONDS_AFTER_REQUEST * 2)
            r_json = self.get_request_json(params)
        page_scrobbles = r_json["recenttracks"]["track"]
        
        return page_scrobbles
    
    def get_scrobbles_from_user(self, user, page_start=1, page_end=None, earliest_timestamp=None):
        unique_scrobbles = set()
        all_scrobbles = []

        def append_page_scrobbles(page_scrobbles):
            for scrobble in page_scrobbles:
                if "@attr" in scrobble: # Ignore now playing scrobble
                    continue
                artist = scrobble["artist"]["#text"]
                album = scrobble["album"]["#text"]
                track = scrobble["name"]
                unix_timestamp = scrobble["date"]["uts"]
                date = datetime.datetime.fromtimestamp(int(unix_timestamp)).strftime("%d %b %Y, %H:%M")
                if earliest_timestamp != None and earliest_timestamp > int(unix_timestamp):
                    print(f"stopping at {date} at timestamp {unix_timestamp}")
                    return -1
                identifier = f"{artist}{album}{track}{unix_timestamp}"
                if identifier not in unique_scrobbles:
                    unique_scrobbles.add(identifier)
                else:
                    continue
                all_scrobbles.append([artist, album, track, unix_timestamp, date])
        
        try:
            params = self.get_getrecenttrack_params(user, page_start)
            r_json = self.get_request_json(params)
            pages = int(r_json["recenttracks"]["@attr"]["totalPages"])
            
            if page_end == None:
                page_end = pages + 1

            if page_start == 1:
                page = 1
                page_scrobbles = r_json["recenttracks"]["track"]
                if append_page_scrobbles(page_scrobbles) == -1:
                    page_end = 0
                print(f"got page {page}/{pages}")
                page_start = 2

            for page in range(page_start, page_end + 1):
                time.sleep(WAIT_SECONDS_AFTER_REQUEST)
                params.update(page=page)
                page_scrobbles = self.get_specified_page_scrobbles_from_user(user, page)
                print(f"got page {page}/{pages}")
                if append_page_scrobbles(page_scrobbles) == -1:
                    break
        except Exception as e:
            print(e)
            print("keeping all scrobbles before the error")
    
        return all_scrobbles