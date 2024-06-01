from util import util
from lastfm_api import LastFMUnauthenticatedAPI
from lastfm_post_requests import DeleteScrobblesAPI

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

            # Check if track that was supposed to be deleted and track still in the library are the same.
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
            