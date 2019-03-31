#!/usr/bin/env python3
import os
import sys
import glob
import json
import logging
import requests
import subprocess
requests.packages.urllib3.disable_warnings()

base_url = "https://<opsman>"

access_token = ""

config = {
    "director": {},
    "products": {},
}

# Assume everything is good!
safe_to_proceed = True

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

if "-v" in sys.argv:
    ch.setLevel(logging.DEBUG)

print("Checking the lab configuration")

# Get access token
logger.debug("Getting access token from UAA")
uaac_token_output = subprocess.check_output(["bash", "get_access_token_from_uaac.sh"])
logger.debug("Output: {}".format(uaac_token_output.decode()))
access_token = str(uaac_token_output.decode()).strip().split("\n")[-1]
logger.debug("Access Token: {}".format(access_token))

# Get director properties
logger.debug("Loading expected configuration from local files")
for f in glob.glob("config/staged_director_*.json"):
    logger.debug("- {}".format(f))
    page = f.replace("config/staged_director_", "").replace(".json", "")
    config["director"][page] = json.load(open(f))

# Get product properties
staged_products = json.load(open("config/staged_products.json"))
staged_products = staged_products[1:] # Remove p-bosh
for staged_product in staged_products:
    product_file = "config/staged_products_{}_properties.json".format(staged_product["type"])
    logger.debug("- {}".format(product_file))
    config["products"][staged_product["type"]] = {
        "properties": json.load(open(product_file))["properties"]
    }

logger.debug("Loading actual configuration from OpsMan API")
s = requests.Session()
s.headers.update({"Authorization": "Bearer {}".format(access_token)})
url = base_url + "/api/v0/staged/products"
logger.debug("HTTP GET {}".format(url))
res = s.get(url, verify=False)
staged_products = res.json()
staged_products = staged_products[1:] # Remove p-bosh
for product in staged_products:
    logger.debug("Verifying {}".format(product["type"]))
    if product["type"] not in config["products"]:
        print("\n{}".format(product["guid"]))
        print("    Unexpected tile deployed!")
        continue

    url = base_url + "/api/v0/staged/products/{}/properties".format(product["guid"])
    logger.debug("HTTP GET {}".format(url))
    res = s.get(url, verify=False)
    product_properties = res.json()

    for prop in config["products"][product["type"]]["properties"]:
        if prop not in product_properties["properties"]:
            print("\n{} -> {}".format(product["guid"], prop))
            print("    Not Found!")
            continue

        expected_value = config["products"][product["type"]]["properties"][prop]["value"]
        actual_value = product_properties["properties"][prop]["value"]

        if expected_value != actual_value:
            print("\n{} -> {}".format(product["guid"], prop))
            print("    Found    : \"{}\"".format(actual_value))
            print("    Expected : \"{}\"".format(expected_value))
            safe_to_proceed = False

if safe_to_proceed:
    print("\nYou should be safe to proceed!\n")
else:
    print("\nPlease fix the configuration before proceeding!\n")

exit(0)
