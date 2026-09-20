"""Uniform handling for unexpected errors in JSON routes.

Returning str(exception) to the browser leaks internals (file paths, SQL, library
messages) to whoever triggered the error. This logs the full traceback server-side,
where it belongs, and sends the client a generic message.
"""
from flask import current_app, jsonify, request


def server_error(exc, message="Something went wrong. Please try again."):
    current_app.logger.error("Unhandled error in %s %s", request.method, request.path, exc_info=exc)
    return jsonify({"success": False, "error": message}), 500
