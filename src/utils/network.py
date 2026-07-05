import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from src.utils.logger import logger

def get_session(retries=3, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504)):
    """
    Membuat session requests dengan retry logic bawaan urllib3.
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Global session reuse
_global_session = None

def get_request(url, params=None, headers=None, timeout=10):
    """
    Wrapper requests.get dengan log dan retry mechanism otomatis.
    """
    global _global_session
    if _global_session is None:
        _global_session = get_session()
    
    # Tambahkan User-Agent standar agar tidak dicurigai bot oleh web server
    if headers is None:
        headers = {}
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
    try:
        response = _global_session.get(url, params=params, headers=headers, timeout=timeout)
        return response
    except Exception as e:
        logger.error(f"[Network] HTTP GET Request ke {url} gagal: {e}")
        raise e
