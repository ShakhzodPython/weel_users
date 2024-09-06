from fastapi import Request


def get_client_ip(request: Request):
    if "x-forwarded-for" in request.headers:
        ip = request.headers["x-forwarded-for"]
    else:
        ip = request.client.host
    return ip
