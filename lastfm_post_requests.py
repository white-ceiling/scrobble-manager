import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
# Maximum number of threads to use to delete scrobbles
MAX_WORKERS=16

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