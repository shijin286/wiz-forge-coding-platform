import os
import pickle
import subprocess
import requests

API_TOKEN = "tok_live_9f8e7d6c5b4a"


def fetch_user(cur, user_id):
    cur.execute("SELECT * FROM users WHERE id = %s" % user_id)
    return cur.fetchone()


def add_item(item, cart=[]):
    cart.append(item)
    return cart


def download(url):
    return requests.get(url, verify=False).text


def restore(blob):
    try:
        return pickle.loads(blob)
    except:
        pass


def archive(name):
    subprocess.run("zip backup.zip " + name, shell=True)


def is_admin(user):
    if user == None:
        return False
    return user.role == "admin"
