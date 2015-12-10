# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2015  Brian Langenberger

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


def perform_lookup(mbid,
                   coverartarchive_server="coverartarchive.org",
                   coverartarchive_port=80):
    """given a MusicBrainz ID as a plain string,
    and optional coverartarchive server/port,
    returns a list of Image objects for each cover

    may return an empty list if no covers are found
    or raise an exception if a problem occurs querying the server"""

    from audiotools import Image
    from audiotools import FRONT_COVER
    from audiotools import BACK_COVER

    try:
        from urllib.request import urlopen
        from urllib.request import URLError
    except ImportError:
        from urllib2 import urlopen
        from urllib2 import URLError

    from json import loads

    # query server for JSON data about MBID release
    try:
        j = urlopen("http://{server}:{port}/release/{release}/".format(
                    server=coverartarchive_server,
                    port=coverartarchive_port,
                    release=mbid))
    except URLError:
        return []

    json_data = loads(j.read().decode("utf-8", "replace"))
    j.close()

    images = []

    # get URLs of all front and back cover art in list
    try:
        for image in json_data[u"images"]:
            if image[u"front"] or image[u"back"]:
                try:
                    data = urlopen(image[u"image"])
                    images.append(
                        Image.new(
                            data.read(),
                            u"",
                            FRONT_COVER if image[u"front"] else BACK_COVER))
                    data.close()
                except URLError:
                    # skip images that aren't found
                    pass
    except KeyError:
        pass

    # return list of all fetched cover art
    return images
