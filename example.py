from scrobble_manager import ScrobbleManager

if __name__ == "__main__":
    user = "username"
    api_key = "your api key"
    api_app_name = "your api app's name"
    web_session_id_cookie = ".eXXXXXXXXXX"

    scrobble_manager = ScrobbleManager(user=user, api_key=api_key, api_app_name=api_app_name, web_session_id_cookie=web_session_id_cookie)
    
    # Use this command to export your scrobbles.
    # scrobble_manager.export_scrobbles_to_csv()

    # Use this command to delete your scrobbles.
    # scrobble_manager.delete_scrobbles_from_csv("path_to.csv")