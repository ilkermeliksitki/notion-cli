#!/usr/bin/env python3

import requests
import json
from datetime import datetime, timezone, timedelta, date
from columnar import columnar # for tabular formatting of the output. In the future, write your own method.
import argparse
import os
import math

 # id of access-gained notion-database.
DATABASE_ID = os.environ["NOTIONDATABASEID"]
TOKEN = os.environ["NOTIONTOKEN"]

HEADERS = {
    "Authorization": "Bearer " + TOKEN,
    "Notion-Version": "2022-02-22",
    "Content-Type": "application/json"
}

# first appeared keys value's icon will be added to page. 
# if title = "coursera-aws" -> icon_url = "https://i.imgur.com/pm8bgGc.png" etc.
# the default one is linux in case of any key is not being found.
ICON_DICT = { 
    "rosetta": "https://i.imgur.com/Mg3Jw5L.png",
    "golang": "https://i.imgur.com/AooJrK8.png",
    "coursera": "https://i.imgur.com/pm8bgGc.png",
    "anki": "https://i.imgur.com/GZwZgGo.png",
    "german": "https://upload.wikimedia.org/wikipedia/commons/b/ba/Flag_of_Germany.svg",
    "aws": "https://www.svgrepo.com/show/331300/aws.svg",
    "datacamp": "https://i.imgur.com/HsGxoXa.jpg",
    "linux": "https://i.imgur.com/PBzqSEO.png"
}

class EmptyFieldError(Exception):
    pass

def write_notion_to_json_file(pseudo_json, name_of_the_file="temp"):
    """helper function for read_database_pages and read_database."""
    json_data = json.loads(pseudo_json)
    with open(name_of_the_file + ".json", "w", encoding="utf-8") as fh:
        json.dump(json_data, fh, indent=4)
    return json_data


def read_database_pages(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    r = requests.post(url, headers=HEADERS)
    #write_notion_to_json_file(r.text, "read_database_pages")
    return r.json()


def filter_pages(di=DATABASE_ID, flags=None):
    pages = []
    for page in read_database_pages(di)["results"]:
        select_of_status_of_page = page["properties"]["Status"]["select"]
        if select_of_status_of_page:
            if select_of_status_of_page["name"] != "Completed" and select_of_status_of_page["name"] != "Incomplete":
                pages.append(page)
    return pages


def page_task_name(page):
    return page['properties']['Task Name']['title'][0]['plain_text']


def read_database(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}"
    r = requests.get(url, headers=HEADERS)
    write_notion_to_json_file(r.text, "read_database")


def create_a_database(database_name, database_id="49a783fcd2c34f86884beb08012b3090"):
    """By default, database will be created in Main Work Space."""
    url = "https://api.notion.com/v1/databases"
    data = {
        "parent": {
            "type": "page_id",
            "page_id": database_id
        },
        "properties": {
            "Page Name": {
                "id": "title",
                "type": "title",
                "title": {}
            },
        },
        "title": [
            {
                "type": "text",
                "text": {
                    "content": database_name
                }
            }
        ]
    }
    data = json.dumps(data)
    r = requests.post(url, headers=HEADERS, data=data)
    # print(r.json())


def create_a_page(
        title: str,
        priority,
        tag,
        database_id,
        status_name,
        task_kind
    ):
    icon_url = ICON_DICT["linux"]
    for icon_name in ICON_DICT.keys():
        if icon_name in title.lower():
            icon_url = ICON_DICT[icon_name]
            break
    url = "https://api.notion.com/v1/pages"
    data = {
        "parent": {
            "database_id": database_id
        },
        "properties": {
            "Task Name": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "Status": {
                "type": "select",
                "select": {
                    "name": status_name
                }
            },
            "Date": {
                "type": "date",
                "date": {
                    "start": str(date.today() + timedelta(days=1))
                }
            },
            "Task Kind": {
                "type": "multi_select",
                "multi_select": [{"name": task_kind}]
            },
            "Tag": {
                "type": "multi_select",
                "multi_select": [{"name": tag}]
            },
            "Priority": {
                "type": "select",
                "select": {
                    "name": priority
                }
            }
        },
        "icon": {
            "type": "external",
            "external": {
                "url": icon_url
            }
        }
    }
    data = json.dumps(data)
    r = requests.post(url, headers=HEADERS, data=data)
    if r.status_code == 200:
        print(f"{title} <- page is successfully created.")
    else:
        print(r.json())
        

def update_remaining_day():
    """This function update the duration column of Daily Task Table."""

    # This part filters the pages whose status is not equal to "Completed" or "None", reducing computational weight and
    # number of API calls.
    pages = filter_pages()
    for page in pages:
        date = page["properties"]["Date"]
        if date["date"]:
            end = date["date"]["end"]
            if end is not None:
                # Calculate the duration time.
                end = datetime.fromisoformat(end)
                end = end.replace(tzinfo=timezone.utc)  # made it offset-aware
                now = datetime.now(tz=timezone.utc)
                duration = end - now
                days = duration.days
                seconds = duration.seconds
                microseconds = duration.microseconds
                total_day = days + (seconds / 86400) + (microseconds / 8.64e+10) - 0.125
                url = f"https://api.notion.com/v1/pages/{page['id']}"
                data = {
                    "properties": {
                        "Remaining Day": {
                            "type": "number",
                            "number": round(total_day, 2)
                        }
                    }
                }
                data = json.dumps(data)
                r = requests.patch(url, headers=HEADERS, data=data)
                # print(r.json())
            else:
                now = datetime.now(tz=timezone.utc)
                start = datetime.fromisoformat(date["date"]["start"])
                start = start.replace(tzinfo=timezone.utc)  # made it offset-aware
                duration = start - now
                days = duration.days
                seconds = duration.seconds
                microseconds = duration.microseconds
                total_day = days + (seconds / 86400) + (microseconds / 8.64e+10) - 0.125  # 0.125 is because of UTC+3
                url = f"https://api.notion.com/v1/pages/{page['id']}"
                data = {
                    "properties": {
                        "Remaining Day": {
                            "type": "number",
                            "number": round(total_day, 2)
                        }
                    }
                }
                data = json.dumps(data)
                r = requests.patch(url, headers=HEADERS, data=data)
                # print(r.json())
            print(f"Updated remaining day of {page_task_name(page)}")


def change_date_by(n):
    """increment or decrement the date by the amount of n for all non-completed tasks."""
    pages = filter_pages()
    for page in pages:
        curr_date = date.fromisoformat(page["properties"]["Date"]["date"]["start"])
        url = f"https://api.notion.com/v1/pages/{page['id']}"
        data = {
            "properties" : {
                    "Date" : {
                        "date" : {
                            "start" : ( curr_date + timedelta(days=n) ).isoformat()
                        }
                    }
            }
        }
        data = json.dumps(data)
        r = requests.patch(url, headers=HEADERS, data=data)
        name_of_the_task = page_task_name(page)
        if r.status_code == 200:
            if n > 0:
                print(f"date is incremented by {n} -> {name_of_the_task}")
            else:
                print(f"date is decremented by {abs(n)} -> {name_of_the_task}")
        else:
            print(f"something went wrong\n{r.json()}")


def update_priority_of_page(page, name_of_priority):
    """helper function for priority setter"""
    page_id = page["id"]
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "Priority": {
                "type": "select",
                "select": {
                    "name": name_of_priority
                }
            }
        }
    }
    data = json.dumps(data)
    r = requests.patch(url, data=data, headers=HEADERS)
    # print(r.json())


def arrange_priorities():
    """This function set "overdue" priority if you miss the deadline of an event whose status is not "Completed"."""

    # This part filters the pages whose status is not equal to "Completed" or "None", reducing computational weight and
    # number of API calls.
    pages = filter_pages()
    for page in pages:
        remaining_day = page["properties"]["Remaining Day"]
        priority_of_page = page["properties"]["Priority"]["select"]["name"]
        if remaining_day is not None and remaining_day["number"] < 0 and priority_of_page != "⚠Overdue⚠":
            update_priority_of_page(page, "⚠Overdue⚠")
            print(f"changed priority of {page_task_name(page)}")


def list_database():
    """print stdout the filtered tasks"""
    headers = ["Task Name", "Status", "Priority", "Task Kind", "Tag", "Remaining Day", "Date"]
    frame = []
    pages = filter_pages()
    for page in pages:
        name_of_the_task = page_task_name(page) 
        properties = page["properties"]
        status = properties["Status"]["select"]["name"]
        priority = properties["Priority"]["select"]["name"]
        task_kinds = [ms_dict["name"] for ms_dict in properties["Task Kind"]["multi_select"]]
        task_kinds_joined = "\n".join(task_kinds)
        working_type = properties["Tag"]["select"]["name"]
        try:
            remaining_day = float(properties["Remaining Day"]["number"])
        except TypeError:
            internal = EmptyFieldError(f"please update the remaining day column of \"{name_of_the_task}\"")
            internal.__suppress_context__ = True
            raise internal
        date = properties["Date"]["date"]["start"]
        frame.append([name_of_the_task, status, priority, task_kinds_joined, working_type, remaining_day, date])
    frame.sort(key=lambda row: row[5])
    print(columnar(frame, headers, no_borders=True))


parser = argparse.ArgumentParser(
    description="Enables you to loosely interact with tokenized databases in notion.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)

# subparsers = parser.add
parser.add_argument("title", nargs="?", help="title of page")
parser.add_argument("-p","--priority", choices=["low", "medium", "high", "overdue"], default="medium", help="sets priority of page")
parser.add_argument("-t", "--tag", default="study", help="sets tag name of the task")
parser.add_argument("-s", "--status-name", default="not started", help="status of task")
parser.add_argument("-d", "--database-id", help="working space id, column names and types should be same.")
parser.add_argument("-k", "--task-kind", default="daily productivity", help="enables to categorize page task")
parser.add_argument("-u", "--update-remaining-day", action="store_true", help="updates remaining day column, which shows the remaining day of task")
parser.add_argument("-a", "--arrange-priorities", action="store_true", help="set `overdue`as a priority if you miss the deadline of tasks")
parser.add_argument("-l", "--list", action="store_true")
parser.add_argument("--change-date")
parser.add_argument("--version", action="version", version="notion-cli 1.0.0 by İlker M. Sıtkı")
args = parser.parse_args()

if args.database_id:
    DATABASE_ID = args.database_id

if args.update_remaining_day:
    update_remaining_day()
    print("remaining days updated.")

if args.arrange_priorities:
    arrange_priorities()
    print("priorities arranged.")    

if args.title:
    create_a_page(
        title=args.title,
        priority=args.priority,
        tag=args.tag,
        database_id=DATABASE_ID,
        status_name=args.status_name,
        task_kind=args.task_kind
    )

if args.list:
    list_database()

if args.change_date:
    change_date_by(int(args.change_date))
    print('done.')

