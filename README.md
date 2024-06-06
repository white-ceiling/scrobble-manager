# Scrobble Manager
This allows you to export scrobbles to a CSV and delete scrobbles from an input CSV. An `example.py` is provided to show how to use Scrobble Manager.

Note: last.fm sometimes doesn't delete certain scrobbles, due to storing the track information differently than it shows publicly, but it still returns 'true' that the scrobble was deleted. I don't know how to get the internally correct track artist and title, as it doesn't show up from user.getRecentTracks or track.getInfo.

# Creating a ScrobbleManager object
`scrobble_manager = ScrobbleManager(user, api_key, api_app_name, web_session_id_cookie)`

user: The username of the user you want to export and delete scrobbles from

api_key, api_app_name: Make an API application at https://www.last.fm/api/account/create if you haven't or use an existing application at https://www.last.fm/api/accounts. Use the value next to "API Key" for the api_key and the Name of the app for api_app_name.

web_session_id_cookie: Grab your sessionid cookie from DevTools while you're on the last.fm website. Make sure you're logged in.
- Chrome > F12 > Application > Cookies > https://www.last.fm/ > Go to the sessionid cookie. Copy and paste the cookie value for web_session_id_cookie.
- Firefox > F12 > Storage > Cookies > Go to the sessionid cookie. Copy and paste the cookie value for web_session_id_cookie.

- Note: A valid sessionid starts with a period like '.eXXXXXXXXXX', meaning you are logged in, and is pretty long.

# Exporting scrobbles to a CSV
Use the following command to export your scrobbles to a CSV named {user}_full_scrobbles.csv.

`scrobble_manager.export_scrobbles_to_csv()`

Each row is one scrobble formatted like:
artist,album,track,unix_timestamp,date

The date is in the timezone your computer uses.

You can filter this CSV yourself to create a CSV containing ONLY the scrobble rows you want to delete.

# Deleting scrobbles
Use this command to delete your scrobbles when you have a CSV with ONLY the scrobbles you want to delete. Please do not use the generated {user}_full_scrobbles.csv as the file, because this will permanently delete all your scrobbles*. Replace path_to.csv with the path to the CSV you are using.

`scrobble_manager.delete_scrobbles_from_csv(scrobbles_for_deletion_csv)`

\* Deleted scrobbles within the past 2 weeks can be added back through the [track.scrobble](https://www.last.fm/api/show/track.scrobble) method from the last.fm API (currently not provided by this tool). If a scrobble is older than 2 weeks, it is impossible to scrobble it without shifting its timestamp to a date within the past 2 weeks.
