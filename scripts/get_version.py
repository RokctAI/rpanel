# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import sys


def main():
    try:
        with open("rpanel/versions.json") as f:
            data = json.load(f)
        print(data.get("rpanel", ""))
    except Exception as e:
        sys.stderr.write(f"Error reading version: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
