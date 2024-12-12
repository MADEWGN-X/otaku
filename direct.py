from json import loads
from lxml.etree import HTML
from os import path as ospath
from re import findall, match, search
from requests import Session, post, get, RequestException
from requests.adapters import HTTPAdapter
from time import sleep
from urllib.parse import parse_qs, urlparse
from urllib3.util.retry import Retry
from uuid import uuid4
from base64 import b64decode



user_agent = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
)


# def direct_link_generator(link):


#     elif "krakenfiles.com" in domain:
#         return krakenfiles(link)
    
def krakenfiles(url):
    with Session() as session:
        session.headers.update({'User-Agent': user_agent})
        try:
            _res = session.get(url)
        except Exception as e:
            return f"ERROR: {e.__class__.__name__}"
            
        html = HTML(_res.text)
        
        # Cek untuk recaptcha sitekey
        if sitekey := html.xpath('//div[@class="g-recaptcha"]/@data-sitekey'):
            # Handle recaptcha
            try:
                # Setup parameter untuk recaptcha
                params = {
                    "k": sitekey[0],
                    "v": "Trd9gRd_6H7d-TFk-HwJ3s3d", # Versi recaptcha
                    "co": "aHR0cHM6Ly9rcmFrZW5maWxlcy5jb206NDQz",  # Base64 encoded origin
                    "hl": "en",  # Language
                    "size": "invisible",
                    "cb": "kr" + str(uuid4())  # Random callback
                }
                captcha_response = get_captcha_token(session, params)
                if not captcha_response:
                    return "ERROR: Failed to get captcha token"
            except Exception as e:
                return f"ERROR: Failed to solve captcha - {str(e)}"
        
        # Dapatkan token dan URL post
        if post_url := html.xpath('//form[@id="dl-form"]/@action'):
            post_url = f"https://krakenfiles.com{post_url[0]}"
        else:
            return "ERROR: Unable to find post link."
            
        if token := html.xpath('//input[@id="dl-token"]/@value'):
            data = {
                "token": token[0],
                "g-recaptcha-response": captcha_response
            }
        else:
            return "ERROR: Unable to find token for post."
            
        try:
            # Tambahkan headers referer
            session.headers.update({'Referer': url})
            _json = session.post(post_url, data=data).json()
        except Exception as e:
            return f"ERROR: {e.__class__.__name__} While send post request"
            
    if _json.get("status") != "ok":
        return f"ERROR: {_json.get('message', 'Unable to find download after post request')}"
        
    return _json["url"]

def get_captcha_token(session, params):
    recaptcha_api = "https://www.google.com/recaptcha/api2"
    res = session.get(f"{recaptcha_api}/anchor", params=params)
    anchor_html = HTML(res.text)
    if not (anchor_token := anchor_html.xpath('//input[@id="recaptcha-token"]/@value')):
        return
    params["c"] = anchor_token[0]
    params["reason"] = "q"
    res = session.post(f"{recaptcha_api}/reload", params=params)
    if token := findall(r'"rresp","(.*?)"', res.text):
        return token[0]
