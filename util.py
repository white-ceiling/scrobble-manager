import urllib
import datetime
import csv

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