import urllib.parse
import requests
import urllib
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import time
import datetime
import csv

# Maximum number of threads to use to delete scrobbles
MAX_WORKERS=16

# Number of seconds to wait after using Last.FM's API
WAIT_SECONDS_AFTER_REQUEST=0.2

class util:
    def get_query_url(base_url, args):
        query = urllib.parse.urlencode(args)

        return f"{base_url}?{query}"

    def write_rows_to_csv(path, scrobbles):
        with open(path, "w", encoding="utf-8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerows(scrobbles)

    def write_scrobble_objects_to_csv(path, scrobbles):
        scrobbles = map(lambda s: [s["artist"], s["album"], s["track"], s["timestamp"], datetime.datetime.fromtimestamp(int(s["timestamp"])).strftime("%d %b %Y, %H:%M")], scrobbles)
        with open(path, "w", encoding="utf=8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerows(scrobbles)
    
    def make_scrobbles_from_csv(scrobbles_csv, **kwargs):
        """
        Generates scrobbles from a CSV, with optionally added albumArtist field.
        Expects CSV to be formatted as column 1 = artist, column 2 = album, column 3 = track, column 4 = unix timestamp.
            A line should look like: artist, album, track, unix timestamp, [anything can come after]

        optional fields:
            albumArtist:    The album artist - if this differs from the track artist.
        """
        scrobbles = []
        with open(scrobbles_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row[3]) == 0:
                    continue
                track = {}
                track.update(
                    artist = row[0],
                    album = row[1],
                    track = row[2],
                    timestamp = row[3],
                    **kwargs
                    )
                scrobbles.append(track)
        return scrobbles

class ScrobbleManager:
    def __init__(self, user, api_key, api_app_name, web_session_id_cookie):
        self.user = user
        self.lfmapi = LastFMUnauthenticatedAPI(api_key, api_app_name)
        self.deleter = DeleteScrobblesAPI(user, web_session_id_cookie)
    
    def export_scrobbles_to_csv(self):
        """
        Writes all of the user's scrobbles from the user.getRecentTracks API method to a file named {user}_full_scrobbles.csv.
        """
        user = self.user
        print(f"getting {user}'s scrobbles. this may take a while due to API restrictions")
        all_scrobbles = self.lfmapi.get_scrobbles_from_user(user)
        print(f"saving {user}'s scrobbles")
        util.write_rows_to_csv(f"{user}_full_scrobbles.csv", all_scrobbles)

    def delete_scrobbles_from_csv(self, scrobbles_for_deletion_csv):
        """
        Deletes the user's scrobbles based on a CSV.
        """
        scrobbles_for_deletion = util.make_scrobbles_from_csv(scrobbles_for_deletion_csv)
        self.deleter.delete(scrobbles_for_deletion)
        self.check_deletion(scrobbles_for_deletion)
    
    def check_deletion(self, scrobbles_for_deletion):
        print("checking if last.fm actually deleted those scrobbles")
        user = self.user
        pages_to_check = set()
        scrobbles_for_deletion = sorted(scrobbles_for_deletion, key=lambda s: int(s["timestamp"]), reverse=True)
        earliest_timestamp = int(scrobbles_for_deletion[-1]["timestamp"])
        print(f"getting {user}'s scrobbles. this may take a while due to API restrictions")
        all_scrobbles = self.lfmapi.get_scrobbles_from_user(user, earliest_timestamp=earliest_timestamp)
        current_index = 0
        unremoved_scrobbles = []
        for n, scrobble in enumerate(all_scrobbles):
            artist_for_deletion = scrobbles_for_deletion[current_index]["artist"]
            track_for_deletion = scrobbles_for_deletion[current_index]["track"]
            timestamp_for_deletion = scrobbles_for_deletion[current_index]["timestamp"]
            kept_artist = scrobble[0]
            kept_track = scrobble[2]
            kept_timestamp = scrobble[3]
            if track_for_deletion == kept_track and artist_for_deletion == kept_artist and timestamp_for_deletion == kept_timestamp:
                pages_to_check.add((n // 50) + 1)
                unremoved_scrobbles.append(scrobble)
                if current_index < len(scrobbles_for_deletion) - 1:
                    current_index += 1
        
        kept_scrobbles = len(unremoved_scrobbles)
        if kept_scrobbles == 0:
            print("scrobbles have been correctly deleted")
        else:
            pages = [f"https://www.last.fm/user/{user}/library?page={page}" for page in sorted(pages_to_check)]            
            pages_string = "\n".join(pages)
            print(f"{kept_scrobbles} scrobbles remain in your library, if they remain undeletable through this script please visit the following pages to delete them manually.\n{pages_string}")
            csv_path = "unremoved_scrobbles.csv"
            util.write_rows_to_csv(csv_path, unremoved_scrobbles)
            print(f"remaining scrobbles that should've been deleted can be found at {csv_path}")
            
class DeleteScrobblesAPI:
    def __init__(self, user, session_id_cookie):
        self.user = user
        if session_id_cookie[0] != ".":
            raise ValueError("Make sure your sessionid cookie is valid and that you copied the entire value. A valid sessionid starts with a period like '.eXXXXXXXXXX' and is pretty long.")
        self.session_id_cookie = session_id_cookie

    def delete(self, scrobbles):
        """
        To delete a scrobble, in addition to form data, the sessionid cookie, CSRF middleware token on the page, and Referer header are required in addition to form data.
        """
        def delete_helper(session, csrf_token, scrobble, user, index):
            payload = {
                "csrfmiddlewaretoken": csrf_token,
                "artist_name": scrobble["artist"],
                "track_name": scrobble["track"],
                "timestamp": scrobble["timestamp"],
            }
            p = session.post(f"https://www.last.fm/user/{user}/library/delete", data=payload, headers=headers)
            if p.status_code == 200:
                message = f"deleted {scrobble}"
            else:
                message = p.text
            return {"code": p.status_code, "index": index, "message": message}

        user = self.user
        headers = {"Referer": f"https://www.last.fm/user/{user}"}
        with requests.Session() as s:
            s.cookies.set("sessionid", self.session_id_cookie)
            r = s.get(f"https://www.last.fm/user/{user}")
            soup = BeautifulSoup(r.text, "html.parser")
            try:
                csrf_token = soup.find(attrs={"name": "csrfmiddlewaretoken"}).get("value")
            except:
                raise ValueError("couldn't find csrf token, try using a different sessionid.")

            successes = 0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as e:
                futures = [e.submit(delete_helper, s, csrf_token, scrobble, user, n) for n, scrobble in enumerate(scrobbles)]
                for f in futures:
                    result = f.result()
                    message = result["message"]
                    code = result["code"]
                    print(message)
                    if code == 200:
                        successes += 1
                    else:
                        index = result["index"]
                        print(f"failed to delete {scrobbles[index]}: error code {code}")
                        with open("error_page.html", "w", encoding="utf-8") as f:
                            f.write(message)
            print(f"{successes}/{len(scrobbles)} total scrobbles deleted")

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

            for page in range(page_start, page_end):
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