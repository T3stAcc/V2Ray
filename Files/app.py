import pybase64, base64, binascii, requests, os, concurrent.futures
from bs4 import BeautifulSoup

fixed_text = """#profile-title: base64:VjJSYXkgQ29uZmlncw==
#profile-update-interval: 1
#subscription-userinfo: upload=29; download=12; total=10737418240000000; expire=2546249531
#support-url: https://github.com/T3stAcc/V2Ray
#profile-web-page-url: https://github.com/T3stAcc/V2Ray
"""

def decode_base64(encoded):
    decoded = ""
    for encoding in ["utf-8", "iso-8859-1"]:
        try:
            if isinstance(encoded, bytes):
                padded = encoded + b"=" * (-len(encoded) % 4)
            else:
                padded = encoded.encode() + b"=" * (-len(encoded) % 4)
            decoded = pybase64.b64decode(padded).decode(encoding)
            break
        except (UnicodeDecodeError, binascii.Error):
            pass
    return decoded

def get_max_pages(base_url):
    try:
        response = requests.get(base_url)
        soup = BeautifulSoup(response.text, "html.parser")
        pagination = soup.find("ul", class_="pagination justify-content-center")
        if pagination:
            page_links = pagination.find_all("a", class_="page-link")
            page_numbers = []
            for link in page_links:
                href = link.get("href", "")
                if href.startswith("?page="):
                    try:
                        page_num = int(href.split("=")[-1])
                        page_numbers.append(page_num)
                    except ValueError:
                        pass
            return max(page_numbers) if page_numbers else 1
        return 1
    except requests.RequestException:
        return 1

def fetch_url_config(url):
    try:
        response = requests.get(url)
        return decode_base64(response.content) if response.content else ""
    except requests.RequestException:
        return ""

def fetch_server_config(server_url):
    try:
        response = requests.get(server_url)
        soup = BeautifulSoup(response.text, "html.parser")
        config_div = soup.find("textarea", {"id": "config"})
        if config_div and config_div.get("data-config"):
            return config_div.get("data-config")
        return None
    except requests.RequestException:
        return None

def scrape_v2nodes_links(base_url):
    max_pages = get_max_pages(base_url)
    links = []
    for page in range(1, max_pages + 1):
        try:
            page_url = f"{base_url}?page={page}"
            response = requests.get(page_url)
            soup = BeautifulSoup(response.text, "html.parser")
            servers = soup.find_all("div", class_="col-md-12 servers")
            server_urls = [f"{base_url}/servers/{server.get('data-id')}/" for server in servers if server.get("data-id")]
            links.extend(server_urls)
        except requests.RequestException:
            pass
    return links

def decode_urls(urls):
    decoded_data = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        future_to_url = {executor.submit(fetch_url_config, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            config = future.result()
            if config:
                decoded_data.append(config)
    return decoded_data

def decode_links(links):
    decoded_data = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        future_to_url = {executor.submit(fetch_server_config, url): url for url in links}
        for future in concurrent.futures.as_completed(future_to_url):
            config = future.result()
            if config:
                decoded_data.append(config)
    return decoded_data

def filter_for_protocols(data, protocols):
    filtered_data = []
    for line in data:
        for config_line in (line.splitlines() if "\n" in line else [line]):
            if any(config_line.startswith(f"{protocol}://") for protocol in protocols):
                filtered_data.append(config_line)
    return filtered_data

def ensure_directories_exist():
    output_folder = os.path.abspath(os.path.join(os.getcwd(), ".."))
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    return output_folder

def main():
    output_folder = ensure_directories_exist()
    protocols = ["vmess", "vless", "trojan", "ss", "ssr"]
    links = [
        "https://shadowmere.xyz/api/b64sub/",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/V2RAY_BASE64.txt",
        "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/Eternity"
    ]
    base_url = "https://v2nodes.com"

    decoded_links = decode_urls(links)
    v2nodes_links = scrape_v2nodes_links(base_url)
    v2nodes_configs = decode_links(v2nodes_links)
    merged_configs = filter_for_protocols(decoded_links + v2nodes_configs, protocols)

    output_filename = os.path.join(output_folder, "All_Configs_Sub.txt")
    base64_filename = os.path.join(output_folder, "All_Configs_Base64.txt")
    if os.path.exists(base64_filename):
        os.remove(base64_filename)

    with open(output_filename, "w") as f:
        f.write(fixed_text)
        for config in merged_configs:
            f.write(config + "\n")

    with open(output_filename, "r") as input_file:
        config_data = input_file.read()

    with open(base64_filename, "w") as output_file:
        encoded_config = base64.b64encode(config_data.encode()).decode()
        output_file.write(encoded_config)

if __name__ == "__main__":
    main()
