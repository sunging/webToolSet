from fastapi import Request

def get_real_ip(request: Request):
    """
    Get the real IP address from the request.

    This function checks for the "X-Real-IP" and "X-Forwarded-For" headers in the request.
    If either of these headers is present, the corresponding IP address is returned.
    If none of the headers are present, the IP address of the client host is returned.

    Args:
        request (Request): The request object.

    Returns:
        str: The real IP address.

    """
    headers = request.headers
    return headers.get("X-Real-IP") or headers.get("X-Forwarded-For") or request.client.host