from fastapi import FastAPI, Request, Response, status
import icmplib
import uvicorn
import logging
from app.utils import get_real_ip

app = FastAPI()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.get("/")
def read_root():
    return {}

@app.get("/ping")
@app.get("/ping/{address}")
def ping(request: Request, response: Response, address: str | None = None):
    """Ping a host and return the delay

    Args:
        request (Request): request object
        response (Response): response object
        address (str | None, optional): target address, if None, use the client's ip. Defaults to None.

    Returns:
        _type_: _description_
    """
    if not address:
        address = get_real_ip(request)
    
    try:
        host = icmplib.ping(address)
    except icmplib.NameLookupError as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": str(e)}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": str(e)}
    
    if not host.is_alive:
        response.status_code = status.HTTP_408_REQUEST_TIMEOUT
        return {"error": "Host is not alive"}

    delay = host.avg_rtt
    return {"delay": delay}

@app.get('/myip')
def get_my_ip(request: Request):
    """
    Returns the IP address of the client making the request.

    Args:
        request (Request): The request object containing client information.

    Returns:
        str: The IP address of the client.
    """
    return get_real_ip(request)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
