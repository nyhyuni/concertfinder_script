#!/usr/bin/python3

import argparse
import base64
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta

import pandas as pd
import pytz
import requests
import urllib3
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from PIL import Image

import chatGPTQuestion

http = urllib3.PoolManager()

# sqlite3 adapters and converters for datetime formatting
def adapt_date(val):
    return val.isoformat()
def convert_date(s):
    return datetime.date.fromisoformat(s.decode("ascii"))
def adapt_datetime(val):
    return val.isoformat(" ")
def convert_datetime(s):
    return datetime.fromisoformat(s.decode("ascii"))

sqlite3.register_adapter(datetime.date, adapt_date)
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("date", convert_date)
sqlite3.register_converter("timestamp", convert_datetime)


area_code_to_name = {
    11: '서울특별시',
    26: '부산광역시',
    27: '대구광역시',
    28: '인천광역시',
    29: '광주광역시',
    30: '대전광역시',
    31: '울산광역시',
    36: '세종특별자치시',
    41: '경기도',
    43: '충청북도',
    44: '충청남도',
    45: '전라북도',
    46: '전라남도',
    47: '경상북도',
    48: '경상남도',
    50: '제주특별자치도',
    51: '강원특별자치도'
}


def get_kopis_api_key():
    try:
        load_dotenv()
    except Exception:
        raise
    kopis_api_key = os.getenv("KOPIS_API_KEY")
    if kopis_api_key is None:
        raise TypeError("KOPIS API Key is None.")
    return kopis_api_key


def get_openai_api_key():
    try:
        load_dotenv()
    except Exception:
        raise
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key is None:
        raise TypeError("OpenAI API Key is None.")
    return openai_api_key


def get_chatgpt_qs():
    try:
        get_pieces_from_poster_q = chatGPTQuestion.get_pieces_from_poster_q()
        get_pieces_from_program_q = chatGPTQuestion.get_pieces_from_program_q()
    except Exception:
        raise
    return {
        "get_pieces_from_poster_q": get_pieces_from_poster_q,
        "get_pieces_from_program_q": get_pieces_from_program_q,
    }


def get_dates(start_date, periods):
    start_date = datetime.strptime(start_date, "%Y%m%d")
    date_generated = pd.date_range(start_date, periods=int(periods))
    date_generated = date_generated.strftime("%Y%m%d")
    return date_generated


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--startDate")
    parser.add_argument("-p", "--periods")
    parser.add_argument("-c", "--cronJob", action="store_true")
    return parser.parse_args()


def get_concerts_list(date, kopis_api_key):
    area_codes = [11, 26, 27, 28, 29, 30, 31, 36, 41, 43, 44, 45, 46, 47, 48, 50, 51]
    concerts_list = []
    for area_code in area_codes:
        url = "http://www.kopis.or.kr/openApi/restful/pblprfr?service={0}&stdate={1}&&eddate={1}&signgucode={2}&shcate=CCCA&rows=100&cpage=1".format(
            kopis_api_key, date, area_code
        )
        print(date, area_code_to_name[area_code], url)
        response = http.request("GET", url)
        soup = BeautifulSoup(response.data, "lxml-xml")
        concerts = soup.find_all("db")
        for concert in concerts:
            concert_info = {}
            concert_info["area"] = area_code
            concert_info["prfnm"] = concert.find("prfnm").text
            concert_info["kopis_id"] = concert.find("mt20id").text
            concert_info["display_poster_name"] = concert.find("poster").text.split("/")[-1]
            concerts_list.append(concert_info)
    return concerts_list


def get_concerts_from_kopis(start_date, kopis_api_key):
    concerts_list = get_concerts_list(start_date, kopis_api_key)
    for concert in concerts_list:
        url = "https://www.kopis.or.kr/openApi/restful/pblprfr/{0}?service={1}&newsql=Y".format(
            concert["kopis_id"], kopis_api_key
        )
        response = http.request("GET", url)
        soup = BeautifulSoup(response.data, "lxml-xml")
        concert_info = soup.find("db")
        concert["price"] = concert_info.find("pcseguidance").text
        concert["date"] = datetime.strptime(start_date, "%Y%m%d")

        ticket_vendors = {}
        try:
            relates = concert_info.find("relates").findChildren(
                "relate", recursive=False
            )
            for relate in relates:
                relateurl = relate.findChildren("relateurl")[0].text
                try:
                    relatenm = relate.findChildren("relatenm")[0].text
                except AttributeError:
                    domain = urllib3.util.parse_url(relateurl).netloc
                    relatenm = ".".join(domain.split(".")[-2:-1])
                if len(relatenm) <= 1:
                    domain = urllib3.util.parse_url(relateurl).netloc
                    relatenm = ".".join(domain.split(".")[-2:-1])
                ticket_vendors[relatenm] = relateurl
                concert["ticket_vendors"] = ticket_vendors
        except AttributeError:
            concert["ticket_vendors"] = ticket_vendors
        full_poster_names = []
        try:
            styurls = concert_info.find("styurls").findChildren(
                "styurl", recursive=False
            )
            for styurl in styurls:
                full_poster_name = styurl.text.split("/")[-1]
                full_poster_names.append(full_poster_name)
            concert["full_poster_names"] = full_poster_names
        except AttributeError:
            concert["full_poster_names"] = [concert["display_poster_name"]]
        concert["prfruntime"] = concert_info.find("prfruntime").text
        concert["prfcast"] = concert_info.find("prfcast").text
        concert["fcltynm"] = concert_info.find("fcltynm").text
        try:
            concert["program_blurb"] = concert_info.find("sty").text
        except AttributeError:
            concert["program_blurb"] = ""
        concert["time"] = re.search(
            r"(?<=\().+?(?=\))", concert_info.find("dtguidance").text
        ).group()
        try:
            hour, minute = concert["time"].split(":")
        except ValueError:
            hour, minute = 0, 0
        concert["date"] = concert["date"].replace(hour=int(hour), minute=int(minute))
        local_tz = pytz.timezone("Asia/Seoul")
        local_dt = local_tz.localize(concert["date"], is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)
        concert["date"] = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
    return concerts_list


def insert_or_select_facility(area, fcltynm):
    facility_tuple = (area, fcltynm)
    query1 = """SELECT id FROM concerts_facility WHERE area_id = ? and name = ?"""
    query2 = """INSERT INTO concerts_facility (area_id,name) VALUES(?,?) returning id"""

    with sqlite3.connect("concertfinder.sqlite3") as conn:
        try:
            result = conn.execute(query1, facility_tuple)
            row = result.fetchone()
            if row is None:
                result = conn.execute(query2, facility_tuple)
                row = result.fetchone()
            return row[0]  # id
        except Exception:
            pass


def insert_concert_into_db(concert, facility_id):
    sql = """ INSERT INTO concerts_concert(kopis_id,prfnm,datetime,prfruntime,price,facility_id,area_id,display_poster_name,prfcast,program_blurb)
              VALUES(?,?,?,?,?,?,?,?,?,?) """
    with sqlite3.connect("concertfinder.sqlite3") as conn:
        cur = conn.cursor()
        try:
            concert_tuple = (
                concert["kopis_id"],
                concert["prfnm"],
                concert["date"],
                concert["prfruntime"],
                concert["price"],
                facility_id,
                concert["area"],
                concert["display_poster_name"],
                concert["prfcast"],
                concert["program_blurb"],
            )
            cur.execute(sql, concert_tuple)
        except Exception:
            raise


def insert_performers_into_db(concert):
    with sqlite3.connect("concertfinder.sqlite3") as conn:
        try:
            cur = conn.cursor()
            prfcast = concert["prfcast"]
            if prfcast[-2:] == " 등":
                prfcast = prfcast[:-2]
            prfcast = prfcast.split(", ")
            performer_tuples = [
                (concert["kopis_id"], performer) for performer in prfcast
            ]
            cur.executemany(
                "insert into concerts_performer(concert_id, name) values (?,?)",
                performer_tuples,
            )
        except sqlite3.Error as e:
            print(e, concert)


def insert_ticket_vendors_into_db(concert):
    with sqlite3.connect("concertfinder.sqlite3") as conn:
        try:
            cur = conn.cursor()
            ticket_vendor_tuples = [
                (concert["kopis_id"], name, url)
                for name, url in concert["ticket_vendors"].items()
            ]
            cur.executemany(
                "insert into concerts_ticketvendor(concert_id,name,url) values (?,?,?)",
                ticket_vendor_tuples,
            )
        except sqlite3.Error as e:
            print(e, concert)


def insert_full_posters_into_db(concert):
    with sqlite3.connect("concertfinder.sqlite3") as conn:
        try:
            cur = conn.cursor()
            full_poster_name_tuples = [
                (concert["kopis_id"], full_poster_name)
                for full_poster_name in concert["full_poster_names"]
            ]
            cur.executemany(
                "insert into concerts_fullpostername(concert_id,name) values (?,?)",
                full_poster_name_tuples,
            )
        except sqlite3.Error as e:
            print(e, concert)


def save_poster(image_name, poster_type):
    current_path = os.path.dirname(os.path.abspath(__file__))
    if poster_type == "display":
        image_url = "http://www.kopis.or.kr/upload/pfmPoster/" + image_name
        img_data = requests.get(image_url).content
        try:
            with open(
                os.path.join(
                    current_path, "media/display_poster/{0}".format(image_name)
                ),
                "wb",
            ) as handler:
                handler.write(img_data)
        except Exception as e:
            raise Exception(
                "Could not save display poster {0} due to '{1}'".format(image_name, e)
            )
    if poster_type == "full":
        image_url = "http://www.kopis.or.kr/upload/pfmIntroImage/" + image_name
        img_data = requests.get(image_url).content
        try:
            with open(
                os.path.join(current_path, "media/full_poster/{0}".format(image_name)),
                "wb",
            ) as handler:
                handler.write(img_data)
        except Exception as e:
            raise Exception(
                "Could not save full poster {0} due to '{1}'".format(image_name, e)
            )


def merge_posters(kopis_id, posters):
    current_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "media/full_poster/"
    )
    poster_full_paths = []
    for poster in posters:
        full_path = os.path.join(current_path, "{0}".format(poster))
        poster_full_paths.append(full_path)

    images = [Image.open(x) for x in poster_full_paths]
    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths)
    max_height = max(heights)

    new_im = Image.new("RGB", (total_width, max_height))

    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]

    merged_file_path = os.path.join(current_path, "{0}_merged.jpg".format(kopis_id))
    new_im.save(merged_file_path)


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def send_request(headers, payload):
    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )
    if response.status_code == 200:
        pieces = response.json()["choices"][0]["message"]["content"].split("\n")
        return pieces
    else:
        print("Error:", response.status_code, response.text)
        return []


def get_pieces_from_poster(concert_id, poster_path, question):
    base64_image = encode_image(poster_path)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}",
    }

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "{0}".format(question),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
        "max_tokens": 300,
    }
    return send_request(headers, payload)


def get_pieces_from_program(concert_id, program, question):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}",
    }

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "{0}. {1}.".format(program, question),
                    },
                ],
            }
        ],
        "max_tokens": 300,
    }
    return send_request(headers, payload)


def parse_pieces(kopis_id, pieces):
    piece_tuples = []
    for piece in pieces:
        if "|" in piece:
            piece = piece.split("|")
            # print('composer: {}, piece: {}'.format(piece[0], piece[1]))
            piece_tuple = (kopis_id, piece[0], piece[1])
            piece_tuples.append(piece_tuple)
    return piece_tuples


def insert_pieces_into_db(kopis_id, piece_tuples):
    with sqlite3.connect("concertfinder.sqlite3") as conn:
        cur = conn.cursor()
        try:
            cur.executemany(
                "insert into concerts_composition(concert_id, composer, name) values (?,?,?)",
                piece_tuples,
            )
        except sqlite3.Error as e:
            print(e, kopis_id)


def get_program_from_chatgpt(concert, chatgpt_qs):
    if len(concert["program_blurb"]) > 1:
        pieces = get_pieces_from_program(
            concert["kopis_id"],
            concert["program_blurb"],
            chatgpt_qs["get_pieces_from_program_q"],
        )
        parsed_pieces = parse_pieces(concert["kopis_id"], pieces)
        insert_pieces_into_db(concert["kopis_id"], parsed_pieces)
    else:
        current_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "media/full_poster/"
        )
        merged_file_path = os.path.join(
            current_path, "{0}_merged.jpg".format(concert["kopis_id"])
        )
        pieces = get_pieces_from_poster(
            concert["kopis_id"],
            merged_file_path,
            chatgpt_qs["get_pieces_from_poster_q"],
        )
        parsed_pieces = parse_pieces(concert["kopis_id"], pieces)
        insert_pieces_into_db(concert["kopis_id"], parsed_pieces)


if __name__ == "__main__":
    try:
        kopis_api_key = get_kopis_api_key()
    except Exception as e:
        sys.exit(
            "Could not retrieve KOPIS API Key. Not proceeding. Error: {0}".format(e)
        )

    try:
        openai_api_key = get_openai_api_key()
    except Exception as e:
        sys.exit(
            "Could not retrieve OpenAI API Key. Not proceeding. Error: {0}".format(e)
        )

    try:
        chatgpt_qs = get_chatgpt_qs()
    except Exception as e:
        sys.exit(
            "Could not retrieve ChatGPT questions. Not proceeding. Error: {0}".format(e)
        )

    args = parse_args()
    if args.cronJob:
        target_date = datetime.now() + timedelta(days=60)
        target_date = datetime.strftime(target_date, "%Y%m%d")
        dates = [target_date]
    else:
        if args.startDate is None or args.periods is None:
            sys.exit("Start date and period were not provided. Not proceeding.")
        dates = get_dates(args.startDate, args.periods)
    for date in dates:
        concerts_list = get_concerts_from_kopis(date, kopis_api_key)
        for concert in concerts_list:
            try:
                facility_id = insert_or_select_facility(
                    concert["area"], concert["fcltynm"]
                )
                insert_concert_into_db(concert, facility_id)
            except Exception as e:
                print(concert["kopis_id"], e)
            else:
                insert_performers_into_db(concert)
                insert_ticket_vendors_into_db(concert)
                insert_full_posters_into_db(concert)
                save_poster(concert["display_poster_name"], "display")
                for full_poster_name in concert["full_poster_names"]:
                    save_poster(full_poster_name, "full")
                if len(concert["program_blurb"]) <= 1:
                    merge_posters(concert["kopis_id"], concert["full_poster_names"])
                get_program_from_chatgpt(concert, chatgpt_qs)
