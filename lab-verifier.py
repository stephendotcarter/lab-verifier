#!/usr/bin/env python3
import os
import sys
import glob
import json
import logging
import requests
import subprocess

base_url = "https://<opsman>"
access_token = ""
config_dir = "./config"

expected_director_properties = {}
expected_products = {}
expected_products_properties = {}

actual_director_properties = {}
actual_products = {}
actual_products_properties = {}

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

# Disable requests/urllib logging
requests.packages.urllib3.disable_warnings()
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

if "-v" in sys.argv:
    ch.setLevel(logging.DEBUG)

# Get access token
logger.info("Getting access token from UAA")
uaac_token_output = subprocess.check_output(["bash", "get_access_token_from_uaac.sh"])
logger.debug("Output: {}".format(uaac_token_output.decode()))
access_token = str(uaac_token_output.decode()).strip().split("\n")[-1]
logger.debug("Access Token: {}".format(access_token))

# Get expected director properties
logger.info("Loading expected configuration from local files")

# for f in glob.glob("config/staged_director_*.json"):
#     logger.debug("FILE {}".format(f))
#     page = f.replace("config/staged_director_", "").replace(".json", "")
#     expected_director_properties[page] = json.load(open(f))

# Get expected product properties
product_file = config_dir + "/staged_products.json"
logger.debug("FILE {}".format(product_file))
expected_products = json.load(open(product_file))
expected_products = expected_products[1:] # Remove p-bosh
for product in expected_products:
    product_file = config_dir + "/staged_products_{}_properties.json".format(product["type"])
    logger.debug("FILE {}".format(product_file))
    expected_products_properties[product["type"]] = {
        "properties": json.load(open(product_file))["properties"]
    }
    del product["installation_name"]
    del product["guid"]

# Get actual director properties
logger.info("Loading actual configuration from OpsMan API")

s = requests.Session()
s.headers.update({"Authorization": "Bearer {}".format(access_token)})
url = base_url + "/api/v0/staged/products"
logger.debug("HTTP {}".format(url))
res = s.get(url, verify=False)
actual_products = res.json()
actual_products = actual_products[1:] # Remove p-bosh
for product in actual_products:
    url = base_url + "/api/v0/staged/products/{}/properties".format(product["guid"])
    logger.debug("HTTP {}".format(url))
    res = s.get(url, verify=False)
    actual_products_properties[product["type"]] = {
        "properties": res.json()["properties"]
    }
    del product["installation_name"]
    del product["guid"]

logger.info("Validating")

issues = {}

# for expected_product in expected_products:
#     if expected_product not in actual_products:
#         print("Tile \"{}\" not found in OpsMan".format(expected_product["type"]))

# for actual_product in actual_products:
#     if actual_product not in expected_products:
#         print("Tile \"{}\" should not be deployed".format(actual_product["type"]))

for expected_product in expected_products_properties:
    logger.debug(expected_product)
    issues[expected_product] = []

    if expected_product not in actual_products_properties:
        issues[expected_product].append("Tile not added to Installation Dashboard")
        logger.debug("expected product not found...ignoring")
        continue

    for prop in expected_products_properties[expected_product]["properties"]:
        logger.debug(prop)
        if expected_products_properties[expected_product]["properties"][prop]["configurable"] == False:
            logger.debug("not configurable...ignoring")
            continue

        if prop not in actual_products_properties[expected_product]["properties"]:
            issues[expected_product].append("Field \"{}\" not found.".format(prop.replace(".properties.", "").replace(".", " -> ")))
            continue

        expected_value = expected_products_properties[expected_product]["properties"][prop]["value"]
        actual_value = actual_products_properties[expected_product]["properties"][prop]["value"]

        if expected_value != actual_value:
            issues[expected_product].append("Field \"{}\" does not match the lab guide.".format(prop.replace(".properties.", "").replace(".", " -> ")))
            logger.info("{} | {} | actual: {} | expected: {}".format(expected_product, prop, actual_value, expected_value))

if issues == {}:
    print("\nLab configuration looks good :-)\n")
    exit(0)

print("\nWARNING: Lab configuration does not match the lab guide!")
for product, product_issues in issues.items():
    print("\nTile \"{}\"".format(product))
    if len(product_issues) == 0:
        print("\tConfiguration good!")
        continue
    for issue in product_issues:
        print("\t* " + issue)

print("\nPlease correct the configuration issues mentioned above before proceeding.\n")

exit(0)
