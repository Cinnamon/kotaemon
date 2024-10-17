#!/usr/bin/env python

from __future__ import print_function

import base64
import string
from zlib import compress

import httplib2
import six  # type: ignore

if six.PY2:
    from string import maketrans
else:
    maketrans = bytes.maketrans


plantuml_alphabet = (
    string.digits + string.ascii_uppercase + string.ascii_lowercase + "-_"
)
base64_alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits + "+/"
b64_to_plantuml = maketrans(
    base64_alphabet.encode("utf-8"), plantuml_alphabet.encode("utf-8")
)


class PlantUMLError(Exception):
    """
    Error in processing.
    """


class PlantUMLConnectionError(PlantUMLError):
    """
    Error connecting or talking to PlantUML Server.
    """


class PlantUMLHTTPError(PlantUMLConnectionError):
    """
    Request to PlantUML server returned HTTP Error.
    """

    def __init__(self, response, content, *args, **kwdargs):
        self.response = response
        self.content = content
        message = "%d: %s" % (self.response.status, self.response.reason)
        if not getattr(self, "message", None):
            self.message = message
        super(PlantUMLHTTPError, self).__init__(message, *args, **kwdargs)


def deflate_and_encode(plantuml_text):
    """zlib compress the plantuml text and encode it for the plantuml server."""
    zlibbed_str = compress(plantuml_text.encode("utf-8"))
    compressed_string = zlibbed_str[2:-4]
    return (
        base64.b64encode(compressed_string).translate(b64_to_plantuml).decode("utf-8")
    )


class PlantUML(object):
    """Connection to a PlantUML server with optional authentication.

    All parameters are optional.

    :param str url: URL to the PlantUML server image CGI. defaults to
                    http://www.plantuml.com/plantuml/svg/
    :param dict request_opts: Extra options to be passed off to the
                    httplib2.Http().request() call.
    """

    def __init__(self, url="http://www.plantuml.com/plantuml/svg/", request_opts={}):
        self.HttpLib2Error = httplib2.HttpLib2Error
        self.http = httplib2.Http()

        self.url = url
        self.request_opts = request_opts

    def get_url(self, plantuml_text):
        """Return the server URL for the image.
        You can use this URL in an IMG HTML tag.

        :param str plantuml_text: The plantuml markup to render
        :returns: the plantuml server image URL
        """
        return self.url + deflate_and_encode(plantuml_text)

    def process(self, plantuml_text):
        """Processes the plantuml text into the raw PNG image data.

        :param str plantuml_text: The plantuml markup to render
        :returns: the raw image data
        """
        url = self.get_url(plantuml_text)
        try:
            response, content = self.http.request(url, **self.request_opts)
        except self.HttpLib2Error as e:
            raise PlantUMLConnectionError(e)
        if response.status != 200:
            raise PlantUMLHTTPError(response, content)

        svg_content = content.decode("utf-8")
        svg_content = svg_content.replace("<svg ", "<svg id='mindmap' ")

        # wrap in fixed height div
        svg_content = (
            "<div id='mindmap-wrapper' "
            "style='height: 400px; overflow: hidden;'>"
            f"{svg_content}</div>"
        )

        return svg_content
