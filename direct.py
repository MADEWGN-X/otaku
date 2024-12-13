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
from hashlib import sha256
from requests import Session
from os import path as ospath


user_agent = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
)




def gofile(url):
    try:
        if "::" in url:
            _password = url.split("::")[-1]
            _password = sha256(_password.encode("utf-8")).hexdigest()
            url = url.split("::")[-2]
        else:
            _password = ""
        _id = url.split("/")[-1]
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

    def __get_token(session):
        headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
        __url = "https://api.gofile.io/accounts"
        try:
            __res = session.post(__url, headers=headers).json()
            if __res["status"] != "ok":
                return "ERROR: Failed to get token."
            return __res["data"]["token"]
        except Exception as e:
            return str(e)

    def __fetch_links(session, _id, folderPath=""):
        _url = f"https://api.gofile.io/contents/{_id}?wt=4fd6sg89d7s6&cache=true"
        headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Authorization": "Bearer" + " " + token,
        }
        if _password:
            _url += f"&password={_password}"
        try:
            _json = session.get(_url, headers=headers).json()
        except Exception as e:
            return f"ERROR: {e.__class__.__name__}"
        if _json["status"] in "error-passwordRequired":
            return f"ERROR:\n{PASSWORD_ERROR_MESSAGE.format(url)}"
        if _json["status"] in "error-passwordWrong":
            return "ERROR: This password is wrong !"
        if _json["status"] in "error-notFound":
            return "ERROR: File not found on gofile's server"
        if _json["status"] in "error-notPublic":
            return "ERROR: This folder is not public"

        data = _json["data"]

        if not details["title"]:
            details["title"] = data["name"] if data["type"] == "folder" else _id

        contents = data["children"]
        for content in contents.values():
            if content["type"] == "folder":
                if not content["public"]:
                    continue
                if not folderPath:
                    newFolderPath = ospath.join(details["title"], content["name"])
                else:
                    newFolderPath = ospath.join(folderPath, content["name"])
                __fetch_links(session, content["id"], newFolderPath)
            else:
                if not folderPath:
                    folderPath = details["title"]
                item = {
                    "path": ospath.join(folderPath),
                    "filename": content["name"],
                    "url": content["link"],
                }
                if "size" in content:
                    size = content["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details["total_size"] += size
                details["contents"].append(item)

    details = {"contents": [], "title": "", "total_size": 0}
    with Session() as session:
        try:
            token = __get_token(session)
            if isinstance(token, str) and token.startswith("ERROR"):
                return token
        except Exception as e:
            return f"ERROR: {e.__class__.__name__}"
            
        details["header"] = f"Cookie: accountToken={token}"
        try:
            result = __fetch_links(session, _id)
            if isinstance(result, str) and result.startswith("ERROR"):
                return result
        except Exception as e:
            return str(e)

    if len(details["contents"]) == 1:
        return (details["contents"][0]["url"], details["header"])
    return details


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
