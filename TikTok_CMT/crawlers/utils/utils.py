import re
import sys
import random
import secrets
import datetime
import browser_cookie3
import importlib_resources

from pydantic import BaseModel

from urllib.parse import quote, urlencode
from typing import Union, List, Any
from pathlib import Path

seed_bytes = secrets.token_bytes(16)
seed_int = int.from_bytes(seed_bytes, "big")
random.seed(seed_int)


def model_to_query_string(model: BaseModel) -> str:
    model_dict = model.dict()
    query_string = urlencode(model_dict)
    return query_string


def gen_random_str(randomlength: int) -> str:
    base_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-"
    return "".join(random.choice(base_str) for _ in range(randomlength))


def get_timestamp(unit: str = "milli"):
    now = datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)
    if unit == "milli":
        return int(now.total_seconds() * 1000)
    elif unit == "sec":
        return int(now.total_seconds())
    elif unit == "min":
        return int(now.total_seconds() / 60)
    else:
        raise ValueError("Unsupported time unit")


def timestamp_2_str(
        timestamp: Union[str, int, float], format: str = "%Y-%m-%d %H-%M-%S"
) -> str:
    if timestamp is None or timestamp == "None":
        return ""

    if isinstance(timestamp, str):
        if len(timestamp) == 30:
            return datetime.datetime.strptime(timestamp, "%a %b %d %H:%M:%S %z %Y")

    return datetime.datetime.fromtimestamp(float(timestamp)).strftime(format)


def num_to_base36(num: int) -> str:
    base_str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    if num == 0:
        return "0"

    base36 = []
    while num:
        num, i = divmod(num, 36)
        base36.append(base_str[i])

    return "".join(reversed(base36))


def split_set_cookie(cookie_str: str) -> str:
    if not isinstance(cookie_str, str):
        raise TypeError("`set-cookie` must be str")

    return ";".join(
        cookie.split(";")[0] for cookie in re.split(", (?=[a-zA-Z])", cookie_str)
    )


def split_dict_cookie(cookie_dict: dict) -> str:
    return "; ".join(f"{key}={value}" for key, value in cookie_dict.items())


def extract_valid_urls(inputs: Union[str, List[str]]) -> Union[str, List[str], None]:
    url_pattern = re.compile(r"https?://\S+")

    if isinstance(inputs, str):
        match = url_pattern.search(inputs)
        return match.group(0) if match else None

    elif isinstance(inputs, list):
        valid_urls = []

        for input_str in inputs:
            matches = url_pattern.findall(input_str)
            if matches:
                valid_urls.extend(matches)

        return valid_urls


def _get_first_item_from_list(_list) -> list:
    if _list and isinstance(_list, list):
        if isinstance(_list[0], list):
            return [inner[0] for inner in _list if inner]
        else:
            return [_list[0]]
    return []


def get_resource_path(filepath: str):
    return importlib_resources.files("f2") / filepath


def replaceT(obj: Union[str, Any]) -> Union[str, Any]:
    reSub = r"[^\u4e00-\u9fa5a-zA-Z0-9#]"

    if isinstance(obj, list):
        return [re.sub(reSub, "_", i) for i in obj]

    if isinstance(obj, str):
        return re.sub(reSub, "_", obj)

    return obj


def split_filename(text: str, os_limit: dict) -> str:
    os_name = sys.platform
    filename_length_limit = os_limit.get(os_name, 200)

    chinese_length = sum(1 for char in text if "\u4e00" <= char <= "\u9fff") * 3
    english_length = sum(1 for char in text if char.isalpha())
    num_underscores = text.count("_")

    total_length = chinese_length + english_length + num_underscores

    if total_length > filename_length_limit:
        split_index = min(total_length, filename_length_limit) // 2 - 6
        split_text = text[:split_index] + "......" + text[-split_index:]
        return split_text
    else:
        return text


def ensure_path(path: Union[str, Path]) -> Path:
    return Path(path) if isinstance(path, str) else path


def get_cookie_from_browser(browser_choice: str, domain: str = "") -> dict:
    if not browser_choice or not domain:
        return ""

    BROWSER_FUNCTIONS = {
        "chrome": browser_cookie3.chrome,
        "firefox": browser_cookie3.firefox,
        "edge": browser_cookie3.edge,
        "opera": browser_cookie3.opera,
        "opera_gx": browser_cookie3.opera_gx,
        "safari": browser_cookie3.safari,
        "chromium": browser_cookie3.chromium,
        "brave": browser_cookie3.brave,
        "vivaldi": browser_cookie3.vivaldi,
        "librewolf": browser_cookie3.librewolf,
    }
    cj_function = BROWSER_FUNCTIONS.get(browser_choice)
    cj = cj_function(domain_name=domain)
    cookie_value = {c.name: c.value for c in cj if c.domain.endswith(domain)}
    return cookie_value


def check_invalid_naming(
        naming: str, allowed_patterns: list, allowed_separators: list
) -> list:
    if not naming or not allowed_patterns or not allowed_separators:
        return []

    temp_naming = naming
    invalid_patterns = []

    for pattern in allowed_patterns:
        if pattern in temp_naming:
            temp_naming = temp_naming.replace(pattern, "")

    for char in temp_naming:
        if char not in allowed_separators:
            invalid_patterns.append(char)

    for pattern in allowed_patterns:
        if pattern + pattern in naming:
            invalid_patterns.append(pattern + pattern)
        for sep in allowed_patterns:
            if pattern + sep + pattern in naming:
                invalid_patterns.append(pattern + sep + pattern)

    return invalid_patterns


def merge_config(
        main_conf: dict = ...,
        custom_conf: dict = ...,
        **kwargs,
):
    merged_conf = {}
    for key, value in main_conf.items():
        merged_conf[key] = value
    for key, value in custom_conf.items():
        if value is not None and value != "":
            merged_conf[key] = value

    for key, value in kwargs.items():
        if key not in merged_conf:
            merged_conf[key] = value
        elif value is not None and value != "":
            merged_conf[key] = value

    return merged_conf
