#!/usr/bin/env python3

from __future__ import print_function

import asyncio

import os
import datetime
from time import mktime
import discord
import logging

from tabulate import tabulate

from pprint import pprint

from dotenv import load_dotenv

from discord.ext import commands
from discord.ext import tasks

from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from apiclient import discovery

from discord_webhook import DiscordWebhook, DiscordEmbed

import time
import json
from urllib.request import urlopen, Request
from websockets.client import connect
import websockets.exceptions
import httplib2
import sqlite3


def parse_world(world):
    worlds = {
        "L": "Lich",
        "O": "Odin",
        "P": "Phoenix",
        "S": "Shiva",
        "T": "Twintania",
        "Z": "Zodiark",
        "A": "Alpha",
        "R": "Raiden"
    }

    initial = world[0].capitalize()
    return worlds[initial]


def worldTimeLoc(world, leg=None):
    locs = {
        "Lich": "C4",
        "Odin": "C5",
        "Phoenix": "C6",
        "Shiva": "C8",
        "Twintania": "C9",
        "Zodiark": "C10",
        "Alpha": "C3",
        "Raiden": "C7"
    }
    if leg == 1:
        locs = {
            "Lich": "C21",
            "Odin": "C22",
            "Phoenix": "C23",
            "Shiva": "C25",
            "Twintania": "C26",
            "Zodiark": "C27",
            "Alpha": "C20",
            "Raiden": "C24"
        }
    return locs[world]


def worldStatusLoc(world, leg=None):
    locs = {
        "Lich": "E4",
        "Odin": "E5",
        "Phoenix": "E6",
        "Shiva": "E8",
        "Twintania": "E9",
        "Zodiark": "E10",
        "Alpha": "E3",
        "Raiden": "E7"
    }
    if leg == 1:
        locs = {
            "Lich": "E21",
            "Odin": "E22",
            "Phoenix": "E23",
            "Shiva": "E25",
            "Twintania": "E26",
            "Zodiark": "E27",
            "Alpha": "E20",
            "Raiden": "E24"
        }
    return locs[world]


async def bot_log(msg):
    await bot.get_channel(LOG_CHANNEL).send(msg)


async def sonar_log(msg):
    await bot.get_channel(SONAR_CHANNEL).send(msg)


async def scout_log(msg):
    await bot.get_channel(BOT_CHANNEL).send(msg)


async def spec_log(msg):
    await bot.get_channel(SPEC_CHANNEL).send(msg)


async def update_channel(server, status, started, legacy=None):
    ids = {
        "Lich": 888868356659228682,
        "Odin": 888868371423191051,
        "Phoenix": 888868382877831188,
        "Shiva": 888868394772860988,
        "Twintania": 888868418361630811,
        "Zodiark": 888868429950484491,
        "Alpha": 993531334754578534,
        "Raiden": 993531381462351923
    }

    ids_l = {
        "Lich": 895686404531707964,
        "Odin": 895686423351533609,
        "Phoenix": 895686443064766545,
        "Shiva": 895686465483309116,
        "Twintania": 895686484659679343,
        "Zodiark": 895686518335737936,
        "Alpha": 993531610962071744,
        "Raiden": 993531650413690920
    }

    servers = {
        "Lich": "lich",
        "Odin": "odin",
        "Phoenix": "phoe",
        "Shiva": "shiva",
        "Twintania": "twin",
        "Zodiark": "zodi",
        "Alpha": "alpha",
        "Raiden": "raid"
    }

    statuses = {
        "Up": "up",
        "Scouting": "scouting",
        "Scouted": "scouted",
        "Running": "run",
        "Dead": "dead",
        "Sniped": "sniped"
    }

    statusicons = {
        "Up": "✅",
        "Scouting": "📡",
        "Scouted": "🌐",
        "Running": "🚋",
        "Dead": "🔒",
        "Sniped": "🏹"
    }
    if legacy != 1:
        chan = bot.get_channel(ids[server])
    else:
        chan = bot.get_channel(ids_l[server])
    newname = f"{statusicons[status]}{servers[server]}-{statuses[status]}"
    if chan.name != newname:
        print("need to update name")
        await chan.edit(name=newname)
    else:
        print("no need to update name")


async def update_sheet(world, status, time, legacy=None):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    creds = None

    secret = os.path.join(os.getcwd(), 'nuny.json')
    creds = service_account.Credentials.from_service_account_file(secret, scopes=SCOPES)

    service = build('sheets', 'v4', credentials=creds)

    sheet = service.spreadsheets()
    timecell = "Up Times!" + worldTimeLoc(world, legacy)
    statuscell = "Up Times!" + worldStatusLoc(world, legacy)
    if time != 0:
        temp = datetime.datetime(1899, 12, 30)
        delta = time - temp
        time = float(delta.days) + (float(delta.seconds) / 86440)
        body = {
            "valueInputOption": "RAW",
            "data": [
                {
                    'range': timecell,
                    'values': [[time]]
                },
                {
                    'range': statuscell,
                    'values': [[status]]
                }
            ]
        }

    else:
        body = {
            "valueInputOption": "RAW",
            "data": [
                {
                    'range': statuscell,
                    'values': [[status]]
                }
            ]
        }

    response = sheet.values().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()


def fetch_sheet(range):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    secret = os.path.join(os.getcwd(), 'nuny.json')
    creds = service_account.Credentials.from_service_account_file(secret, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    try:
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range,
                                    valueRenderOption="UNFORMATTED_VALUE").execute()
    except HttpError as err:
        print(f"HttpError! {err.resp.status}")
        return 0
    return result.get('values', [])


async def update_from_sheets():
    EW_RANGE = 'Up Times!B3:E10'
    LEGACY_RANGE = 'Up Times!B20:E27'

    values = fetch_sheet(EW_RANGE)

    if not values:
        print('No data found.')
    else:
        for row in values:
            if ready == 1:
                await update_channel(row[0], row[3], datetime.datetime(1899, 12, 30) + datetime.timedelta(days=row[1]),
                                     0)

    values = fetch_sheet(LEGACY_RANGE)

    if not values:
        print('No data found.')
    else:
        for row in values:
            if ready == 1:
                await update_channel(row[0], row[3], datetime.datetime(1899, 12, 30) + datetime.timedelta(days=row[1]),
                                     1)


async def update_from_sheets_to_chat(legacy=None):
    range = 'Up Times!B3:E10'
    message = "Endwalker status\n```"
    if legacy == 1:
        range = 'Up Times!B20:E27'
        message = "Shadowbringers status\n```"

    values = fetch_sheet(range)

    if not values:
        print('No data found.')
    else:
        taulu = []
        taulu.append(["Server", "Status\nchanged", "+6h", "Status\nduration", "Status"])
        for row in values:
            if ready == 1:
                t1 = datetime.datetime.strftime(
                    datetime.datetime(1899, 12, 30) + datetime.timedelta(days=row[1]),
                    "%d.%m %H:%M"
                )
                if row[3] == "Dead":
                    t2 = datetime.datetime.strftime(
                        datetime.datetime(1899, 12, 30) + datetime.timedelta(days=row[2]),
                        "%H:%M"
                    )
                else:
                    t2 = ""
                t3_td = datetime.datetime.utcnow() - (datetime.datetime(1899, 12, 30) + datetime.timedelta(days=row[1]))
                t3_h = int(divmod(t3_td.total_seconds(), 3600)[0])
                t3_m = int(divmod(divmod(t3_td.total_seconds(), 3600)[1], 60)[0])
                if t3_h < 0:
                    t3 = ""
                else:
                    t3 = f"{t3_h}:{t3_m:02d}"

                taulu.append([row[0], t1, t2, t3, row[3]])
    message += tabulate(taulu, headers="firstrow", tablefmt="fancy_grid") + "```"
    return message


async def update_from_sheets_to_compact_chat(legacy=None):
    range = 'Up Times!B33:D40'
    values = fetch_sheet(range)

    if not values:
        print('No data found.')
    else:
        taulu = []
        taulu.append(["Server", "EW", "SHB"])
        for row in values:
            if ready == 1:
                taulu.append([row[0], row[1], row[2]])
    message = "```" + tabulate(taulu, headers="firstrow", tablefmt="fancy_grid") + "```"
    return message


def delta_to_words(delta):
    delta = abs(delta)
    delta_d = int(divmod(delta.total_seconds(), 86400)[0])
    delta_h = int(divmod(divmod(delta.total_seconds(), 86400)[1], 3600)[0])
    delta_m = int(divmod(divmod(delta.total_seconds(), 3600)[1], 60)[0])

    msg = ""
    if delta_d > 0:
        msg = f"{delta_d} days, "
    if delta_h > 0:
        msg += f"{delta_h} hours and "
    msg += f"{delta_m} minutes"
    return msg


def spec_delta(time, start_s, end_s, type):
    now = datetime.datetime.utcnow()
    start = time + datetime.timedelta(seconds=start_s) - now
    end = time + datetime.timedelta(seconds=end_s) - now
    st = delta_to_words(start)
    en = delta_to_words(end)
    if type == "spawn":
        if int(start.total_seconds()) > 0:
            msg = f"Marks have been despawned and will start spawning in {st} and will be fully spawned in {en}."
        else:
            msg = f"Marks have started spawning {st} ago and should be fully spawned in {en}."
    else:
        if int(start.total_seconds()) > 0:
            msg = f"Marks are up and will start despawning in {st} and will be fully despawned in {en}."
        else:
            msg = f"Marks have started to despawn {st} ago and will be fully despawned in {en}."
    return msg


def speculate(world, legacy=None):
    now = datetime.datetime.utcnow()
    l = 0
    l_text = ""
    if legacy[0].capitalize() == "L":
        l = 1
        l_text = " (legacy) "
    w = parse_world(world)

    timecell = "Up Times!" + worldTimeLoc(w, l)
    statuscell = "Up Times!" + worldStatusLoc(w, l)

    time = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=fetch_sheet(timecell)[0][0])
    delta = now - time
    status = fetch_sheet(statuscell)[0][0]

    msg = f"Status **{status}** for **{w}**{l_text} was set at {time}.\n"
    if status == "Dead":
        msg += spec_delta(time, 12600, 21600, "spawn")
    if status == "Up" or status == "Scouting" or status == "Scouted":
        dur = now - time + datetime.timedelta(hours=0)
        if int(dur.total_seconds()) < 86400:
            msg += spec_delta(time, 77400, 86400, "despawn")
        else:
            if int(dur.total_seconds()) < 108000:
                msg += spec_delta(time, 91800, 108000, "spawn")
            else:
                if int(dur.total_seconds()) < 194400:
                    msg += spec_delta(time, 178200, 194400, "despawn")
                else:
                    if int(dur.total_seconds()) < 216000:
                        msg += spec_delta(time, 192600, 216000, "spawn")
                    else:
                        if int(dur.total_seconds()) < 302400:
                            msg += spec_delta(time, 279000, 302400, "despawn")
                        else:
                            if int(dur.total_seconds()) < 324000:
                                msg += spec_delta(time, 293400, 324000, "spawn")
                            else:
                                msg += "Condition uncertain, try to run trains more often."
    # marks alive, last 18 hours
    sel_alive = """
SELECT count(*) from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND lastseen > datetime('now','-20 hours') AND 
lastfound > datetime('now', '-20 hours') AND currenthp!=0
              """
    # marks that should have respawned but no sighting
    sel_spawned = """
SELECT count(*) from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND lastkilled > datetime('now','-20 hours') AND 
lastkilled < datetime('now','-6 hours') AND currenthp=0
                 """
    # marks killed during last 6 hours
    sel_spawning = """
SELECT count(*) from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND lastkilled > datetime('now','-6 hours') AND 
lastkilled < datetime('now','-4 hours') AND currenthp=0
                 """
    # marks killed during last 4 hours
    sel_dead = """
SELECT count(*) from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND lastkilled > datetime('now','-4 hours') AND currenthp=0
             """

    if l == 0:
        exp = 5
    else:
        exp = 4

    cursor.execute(sel_alive, (exp, w))
    alive = cursor.fetchall()[0][0]

    cursor.execute(sel_spawned, (exp, w))
    spawned = cursor.fetchall()[0][0]

    cursor.execute(sel_spawning, (exp, w))
    spawning = cursor.fetchall()[0][0]

    cursor.execute(sel_dead, (exp, w))
    dead = cursor.fetchall()[0][0]

    msg += f"\nSonar data suggests that {alive} marks are alive, {spawned} marks should have spawned, "
    f"{spawning} marks have potential to spawn and {dead} marks are dead."

    return msg


def mapping(world, legacy=None):
    l = 0
    l_text = ""
    if legacy[0].capitalize() == "L":
        l = 1
        l_text = " (legacy) "

    w = parse_world(world)

    if l == 0:
        exp = 5
    else:
        exp = 4

    ishort = {0: '',
              1: '',
              2: '',
              3: ''}

    ilong = {0: '',
             1: '  (Instance ONE)',
             2: '  (Instance TWO)',
             3: '  (Instance THREE)'}

    sel = """
SELECT hunts.name, zones.name,hunt.instanceid, 
       round(((41 / zones.scale) * (((hunt.x + zones.offset_x)*zones.scale + 1024) / 2048)+1),1),
       round(((41 / zones.scale) * (((hunt.y + zones.offset_y)*zones.scale + 1024) / 2048)+1),1) from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
INNER JOIN zones on zones.id=hunt.zoneid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND lastseen > datetime('now','-20 hours') AND 
lastfound > datetime('now','-20 hours') AND currenthp != 0
ORDER BY hunt.zoneid,hunt.instanceid
        """
    cursor.execute(sel, (exp, w))
    h = cursor.fetchall()
    msg = "Sonar data suggests following mapping:\n```\n"
    for l in h:
        msg += f"({l[0]}) {l[1]}{ishort[l[2]]} ( {l[3]} , {l[4]} ){ilong[l[2]]}\n"
    msg += "```"
    return msg


def parse_parameters(time, leg):
    try:
        if time == None:
            time = datetime.datetime.utcnow()
        else:
            if time[0].capitalize() == "L" or time[0] == "5":
                leg = "L"
                time = datetime.datetime.utcnow()
            else:
                if time[0] == "4":
                    leg = "4"
                else:
                    if time[0] == "+":
                        time = datetime.timedelta(minutes=int(time[1:])) + datetime.datetime.utcnow()
                    else:
                        t = time.split(":")
                        h = int(t[0])
                        m = int(t[1])
                        time = datetime.datetime.utcnow().replace(hour=h, minute=m, second=45)
    except ValueError:
        time = datetime.datetime.utcnow()
    l = 0
    stb = 0
    if leg[0].capitalize() == "L":
        l = 1
    if leg[0] == "5":
        l = 1
    if leg[0] == "4":
        stb = 1
        l = 1
    return [time, l, stb]


def webhook_shout(webhook, role, embed):
    mentions = {
        "roles": [role]
    }
    if role == 0:
        msg = "Hunt train is about to start!"
    else:
        msg = f"<@&{role}> train is about to start!"
    webhook = DiscordWebhook(url=webhook, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                             username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
    webhook.add_embed(embed)
    resp = webhook.execute()


logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
LOG_CHANNEL = int(os.getenv('LOG_CHANNEL'))
BOT_CHANNEL = int(os.getenv('BOT_CHANNEL'))
SONAR_CHANNEL = int(os.getenv('SONAR_CHANNEL'))
SPEC_CHANNEL = int(os.getenv('SPEC_CHANNEL'))
DC_ASSET = os.getenv('DC_ASSET')
WORLD_ASSET = os.getenv('WORLD_ASSET')
HUNT_ASSET = os.getenv('HUNT_ASSET')
ZONE_ASSET = os.getenv('ZONE_ASSET')
SONAR_WEBSOCKET = os.getenv('SONAR_WEBSOCKET')

WEBHOOK_TEST = os.getenv('WEBHOOK_TEST')
WEBHOOK_ESC = os.getenv('WEBHOOK_ESC_FC')
WEBHOOK_CC = os.getenv('WEBHOOK_CC')
WEBHOOK_CH = os.getenv('WEBHOOK_CH')
WEBHOOK_ANGEL = os.getenv('WEBHOOK_ANGEL')
WEBHOOK_FALOOP = os.getenv('WEBHOOK_FALOOP')
WEBHOOK_WRKJN = os.getenv('WEBHOOK_WRKJN')
WEBHOOK_KETTU = os.getenv('WEBHOOK_KETTU')
WEBHOOK_HAO = os.getenv('WEBHOOK_HAO')
WEBHOOK_ASHIE = os.getenv('WEBHOOK_ASHIE')
WEBHOOK_VINCENT = os.getenv('WEBHOOK_VINCENT')
WEBHOOK_SYNCHRONISED = os.getenv('WEBHOOK_SYNCHRONISED')
WEBHOOK_LUCY = os.getenv('WEBHOOK_LUCY')
WEBHOOK_KENZIE = os.getenv('WEBHOOK_KENZIE')
WEBHOOK_BADGER = os.getenv('WEBHOOK_BADGER')
WEBHOOK_DELIAH = os.getenv('WEBHOOK_DELIAH')
WEBHOOK_SWEEPER = os.getenv('WEBHOOK_SWEEPER')
WEBHOOK_UNICORN = os.getenv('WEBHOOK_UNICORN')
WEBHOOK_CTLANTAA = os.getenv('WEBHOOK_CTLANTAA')
WEBHOOK_IZZY = os.getenv('WEBHOOK_IZZY')

ROLE_EW_TEST = int(os.getenv('ROLE_TEST_EW'))
ROLE_SHB_TEST = int(os.getenv('ROLE_TEST_SHB'))
ROLE_EW_ESC = int(os.getenv('ROLE_ESC_FC'))
ROLE_SHB_ESC = int(os.getenv('ROLE_ESC_FC'))
ROLE_EW_CC = int(os.getenv('ROLE_CC_EW'))
ROLE_SHB_CC = int(os.getenv('ROLE_CC_SHB'))
ROLE_EW_CH = int(os.getenv('ROLE_CH_EW'))
ROLE_SHB_CH = int(os.getenv('ROLE_CH_SHB'))
ROLE_STB_CH = int(os.getenv('ROLE_CH_STB'))
ROLE_EW_FALOOP = int(os.getenv('ROLE_FALOOP_EW'))
ROLE_SHB_FALOOP = int(os.getenv('ROLE_FALOOP_SHB'))
ROLE_STB_FALOOP = int(os.getenv('ROLE_FALOOP_STB'))
ROLE_EW_KETTU = int(os.getenv('ROLE_KETTU_EW'))
ROLE_SHB_KETTU = int(os.getenv('ROLE_KETTU_SHB'))
ROLE_STB_KETTU = int(os.getenv('ROLE_KETTU_STB'))
ROLE_HAO = int(os.getenv('ROLE_HAO'))
ROLE_ASHIE = int(os.getenv('ROLE_ASHIE'))
ROLE_EW_BADGER = int(os.getenv('ROLE_BADGER_EW'))
ROLE_SHB_BADGER = int(os.getenv('ROLE_BADGER_SHB'))
ROLE_STB_BADGER = int(os.getenv('ROLE_BADGER_STB'))
ROLE_SWEEPER = int(os.getenv('ROLE_SWEEPER'))
ROLE_EW_UNICORN = int(os.getenv('ROLE_UNICORN_EW'))
ROLE_SHB_UNICORN = int(os.getenv('ROLE_UNICORN_SHB'))
ROLE_STB_UNICORN = int(os.getenv('ROLE_UNICORN_STB'))

ready = 0

bot = commands.Bot(command_prefix=".")


@bot.command(name='speculate', help='Speculate about status of a certain world')
async def spec(ctx, world, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    msg = speculate(world, legacy)
    await ctx.send(msg)


@bot.command(name='mapping', aliases=["map", ], help='Check mapping data from Sonar')
async def spec(ctx, world, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    msg = mapping(world, legacy)
    await ctx.send(msg)


@bot.command(name='scout', aliases=['sc', 'scouting'], help='Begin scouting.')
async def scouting(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    world = parse_world(world)
    parm = parse_parameters(time, legacy)
    time = 0
    l = parm[1]
    stb = parm[2]
    if stb == 0:
        statuscell = "Up Times!" + worldStatusLoc(world, l)
        status = fetch_sheet(statuscell)[0][0]
        if status == "Dead":
            await ctx.send("Scouting a dead world, adjusting timer.")
            timecell = "Up Times!" + worldTimeLoc(world, l)
            time = datetime.datetime(1899, 12, 30) + datetime.timedelta(
                days=fetch_sheet(timecell)[0][0]) + datetime.timedelta(hours=6)
        await update_sheet(world, "Scouting", time, l)
        await update_channel(world, "Scouting", time, l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")


@bot.command(name='scoutcancel', aliases=['cancel', 'sccancel', 'scc'],
             help="Cancel scouting. Return server to up status.")
async def scoutcancel(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    world = parse_world(world)
    parm = parse_parameters(time, legacy)
    l = parm[1]
    stb = parm[2]
    status = "Up"
    if stb == 0:
        timecell = "Up Times!" + worldTimeLoc(world, l)
        time = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=fetch_sheet(timecell)[0][0])
        if time > datetime.datetime.utcnow():
            time = time - datetime.timedelta(hours=6)
            status = "Dead"
            await ctx.send("Adjusting time -6h and status to dead because timestamp in future.")
        else:
            time = 0
        await update_sheet(world, status, time, l)
        await update_channel(world, status, time, l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")


@bot.command(name='scouted', aliases=['scdone', 'scend'], help='End scouting.')
async def scoutend(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    world = parse_world(world)
    parm = parse_parameters(time, legacy)
    time = 0
    l = parm[1]
    stb = parm[2]
    if stb == 0:
        await update_sheet(world, "Scouted", time, l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")


@bot.command(name='start', aliases=['begin', 'run', 'go'],
             help='Start train.\n Time parameter is optional, defaults to current time and can be manually set in '
                  'form "+15" (minutes) or "15:24" (server time)')
async def begintrain(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    world = parse_world(world)
    parm = parse_parameters(time, legacy)
    time = parm[0]
    l = parm[1]
    stb = parm[2]

    if stb == 0:
        await update_sheet(world, "Running", time, l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")


@bot.command(name='end', aliases=['done', 'dead', 'finish'],
             help='Finish train.\n Time parameter is optional, defaults to current time and can be manually set in '
                  'form "+15" (minutes) or "15:24" (server time)')
async def endtrain(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    world = parse_world(world)
    parm = parse_parameters(time, legacy)
    time = parm[0]
    l = parm[1]
    stb = parm[2]
    if stb == 0:
        await update_sheet(world, "Dead", time, l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")

    # statistics 
    sel_stat = """
SELECT round(avg(players)),min(players),max(players) from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND currenthp=0 AND 
lastkilled > datetime('now', '-45 minutes') AND players>10
             """

    if l == 0:
        exp = 5
    else:
        exp = 4

    cursor.execute(sel_stat, (exp, world))
    stats = cursor.fetchall()[0]
    s_avg = stats[0]
    s_min = stats[1]
    s_max = stats[2]

    await scout_log(
        f"Average participation on the train seemed to be about {s_avg} players. (varied between {s_min}-{s_max})")


@bot.command(name='up', aliases=['reset'], help='Reset train')
async def resettrain(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return

    await ctx.message.add_reaction("⛔")
    return

    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    world = parse_world(world)
    parm = parse_parameters(time, legacy)
    time = parm[0]
    l = parm[1]
    stb = parm[2]

    if stb == 0:
        await update_sheet(world, "Up", time, l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")


@bot.command(name="status", aliases=['getstatus', 'stat'], help='Get train status')
async def getstatus(ctx, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    leg = 0
    if legacy[0].capitalize() == "L":
        leg = 1
    msg = await update_from_sheets_to_chat(leg)
    await ctx.send(msg)
    await ctx.message.add_reaction("✅")


@bot.command(name="cstatus", aliases=['compactstatus', 'cstat', 'cs'], help='Get compact train status')
async def getstatus(ctx):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    msg = await update_from_sheets_to_compact_chat()
    await ctx.send(msg)
    await ctx.message.add_reaction("✅")


async def periodicstatus():
    msg = await update_from_sheets_to_chat(0)
    await bot_log(msg)
    msg = await update_from_sheets_to_chat(1)
    await bot_log(msg)


@bot.command(name="testadvertise", aliases=['testshout', 'testsh'],
             help='Advertise your train. Put multi-part parameters in quotes (eg. .shout twin "Fort Jobb"). '
                  'Any attached image wil be included in the shout')
async def advertise(ctx, world, start, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return

    world = parse_world(world)
    parm = parse_parameters(None, legacy)
    l = parm[1]
    if l == 0:
        role = "@Endwalker_role"
    else:
        role = "@Legacy_role"

    username = ctx.message.author.display_name
    user_avatar = ctx.message.author.avatar_url

    imageurl = ""

    if ctx.message.attachments:
        imageurl = str(ctx.message.attachments[0].url)

    embed = discord.Embed(
        title="Hunt train will start in 10 minutes")
    embed.set_author(name=str(username), icon_url=str(user_avatar))
    embed.add_field(name="Server", value=world, inline=True)
    embed.add_field(name="Start location", value=start)

    if imageurl != "":
        embed.set_image(url=imageurl)

    msg = (f"About to send this notification to the test server (react with ✅ to send or wait 15 sec to cancel):"
           f"\n\n{role} train is about to start!")

    msg1 = await ctx.send(msg, embed=embed)
    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id == msg1.id and str(reaction.emoji) == '✅' and user.id == ctx.author.id

    try:
        res = await bot.wait_for("reaction_add", check=check, timeout=15)
    except asyncio.TimeoutError:
        print("Timed out")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        pass
    else:
        if res:
            reaction, user = res
            print(reaction.emoji)

            embed = DiscordEmbed(
                title="Hunt train will start in 10 minutes")
            embed.set_author(name=str(username), icon_url=str(user_avatar))
            embed.add_embed_field(name="Server", value=world, inline=True)
            embed.add_embed_field(name="Start location", value=start)

            if imageurl != "":
                embed.set_image(url=imageurl)

            # test server
            print("test")
            if l == 0:
                role = ROLE_EW_TEST
            else:
                role = ROLE_SHB_TEST

            webhook_shout(WEBHOOK_TEST, role, embed)

            await msg1.delete()
            await ctx.message.add_reaction('✅')


@bot.command(name="testadvertise2", aliases=['testshout2', 'testsh2'],
             help='Advertise your train. Put multi-part parameters in quotes (eg. .testsh2 "message text here" '
                  '[image_url] [legacy])')
async def advertise(ctx, message, imageurl="", legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return

    username = ctx.message.author.display_name
    user_avatar = ctx.message.author.avatar_url

    if imageurl == "l":
        legacy = "l"
        imageurl = ""

    if ctx.message.attachments:
        imageurl = str(ctx.message.attachments[0].url)

    parm = parse_parameters(None, legacy)
    l = parm[1]
    if l == 0:
        roletext = "@Endwalker_role"
    else:
        roletext = "@Legacy_role"

    msg = "About to send this notification to test server:"
    embed = discord.Embed(
        title=f"{roletext} train is about to start!",
        description=message)
    embed.set_author(name=username, icon_url=user_avatar)
    if imageurl != "":
        embed.set_image(url=imageurl)
    try:
        msg1 = await ctx.send(msg, embed=embed)
    except:
        await ctx.message.add_reaction('❌')
        await ctx.send("Invalid url or image")
        return

    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id == msg1.id and str(reaction.emoji) == '✅' and user.id == ctx.author.id

    try:
        res = await bot.wait_for("reaction_add", check=check, timeout=30)
    except asyncio.TimeoutError:
        print("Timed out")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        pass
    else:
        if res:
            reaction, user = res
            print(reaction.emoji)

            embed = DiscordEmbed(description=str(message))
            embed.set_author(name=str(username), icon_url=str(user_avatar))
            if imageurl != "":
                embed.set_image(url=str(imageurl))

            # test server
            print("test")

            if l == 0:
                role = ROLE_EW_TEST
            else:
                role = ROLE_SHB_TEST
            webhook_shout(WEBHOOK_TEST, role, embed)

            await msg1.delete()
            await ctx.message.add_reaction('✅')


@bot.command(name="advertise", aliases=['ad', 'shout', 'sh'],
             help='Advertise your train. Put multi-part parameters in quotes (eg. .shout twin "Fort Jobb"). '
                  'Additionally will set the server status to running.')
async def advertise(ctx, world, start, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    username = ctx.message.author.display_name

    if len(start) < 6:
        await ctx.message.add_reaction("❌")
        await ctx.send("Start location needs to be over 5 characters.")
        return

    tenmin = datetime.timedelta(minutes=10) + datetime.datetime.now()
    timestamp = int(mktime(tenmin.timetuple()))
    world = parse_world(world)
    parm = parse_parameters(None, legacy)
    l = parm[1]
    stb = parm[2]
    if l == 0:
        msg = f"About to send this notification to various servers: ```@Endwalker_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```Also I will set the server to *running* state. React with ✅ to send or wait 30 seconds to cancel."
    if l == 1:
        msg = f"About to send this notification to various servers: ```@Shadowbringers_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```Also I will set the server to *running* state. React with ✅ to send or wait 30 seconds to cancel."
    if stb == 1:
        msg = f"About to send this notification to various servers: ```@Stormblood_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel."

    msg1 = await ctx.send(msg)
    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id == msg1.id and str(reaction.emoji) == '✅' and user.id == ctx.author.id

    try:
        res = await bot.wait_for("reaction_add", check=check, timeout=30)
    except asyncio.TimeoutError:
        print("Timed out")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        pass
    else:
        if res:
            reaction, user = res
            print(reaction.emoji)

            # test server
            print("test")
            mentions = {
                "roles": [ROLE_EW_TEST, ROLE_SHB_TEST]
            }
            if l == 0:
                msg = f"<@&{ROLE_EW_TEST}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            if l == 1:
                msg = f"<@&{ROLE_SHB_TEST}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_TEST, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # kettu server
            print("kettu")
            mentions = {
                "roles": [ROLE_EW_KETTU, ROLE_SHB_KETTU, ROLE_STB_KETTU]
            }
            if l == 0:
                msg = f"<@&{ROLE_EW_KETTU}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            if l == 1:
                msg = f"<@&{ROLE_SHB_KETTU}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            if stb == 1:
                msg = f"<@&{ROLE_STB_KETTU}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."

            webhook = DiscordWebhook(url=WEBHOOK_KETTU, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # ch server
            print("ch")
            mentions = {
                "roles": [ROLE_EW_CH, ROLE_SHB_CH, ROLE_STB_CH]
            }
            if l == 0:
                msg = f"<@&{ROLE_EW_CH}> **[{world}]** Hunt train starting in <t:{timestamp}:R> at {start} (Conductor: {username})."
            if l == 1:
                msg = f"<@&{ROLE_SHB_CH}> **[{world}]** Hunt train starting in <t:{timestamp}:R> at {start} (Conductor: {username})."
            if stb == 1:
                msg = f"<@&{ROLE_STB_CH}> **[{world}]** Hunt train starting in <t:{timestamp}:R> at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_CH, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # angel server
            print("angel")
            if l == 0:
                msg = f"[{world}] Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
                webhook = DiscordWebhook(url=WEBHOOK_ANGEL, rate_limit_retry=True, content=msg, username="Nunyunuwi",
                                         avatar_url="https://jvaarani.kapsi.fi/nuny.png")
                resp = webhook.execute()

            # wrkjn server
            print("wrkjn")
            if l == 0:
                msg = f"[{world}] Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
                webhook = DiscordWebhook(url=WEBHOOK_WRKJN, rate_limit_retry=True, content=msg, username="Nunyunuwi",
                                         avatar_url="https://jvaarani.kapsi.fi/nuny.png")
                resp = webhook.execute()

            # ashie server
            print("ashie")
            mentions = {
                "roles": [ROLE_ASHIE]
            }
            msg = f"<@&{ROLE_ASHIE}> [{world}] Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_ASHIE, rate_limit_retry=True, content=msg, username="Nunyunuwi",
                                     avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # faloop server
            print("faloop")
            mentions = {
                "roles": [ROLE_EW_FALOOP, ROLE_SHB_FALOOP, ROLE_STB_FALOOP]
            }
            if l == 0:
                msg = f"<@&{ROLE_EW_FALOOP}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            if l == 1:
                msg = f"<@&{ROLE_SHB_FALOOP}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            if stb == 1:
                msg = f"<@&{ROLE_STB_FALOOP}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."

            webhook = DiscordWebhook(url=WEBHOOK_FALOOP, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # vincent server
            print("vincent")
            msg = f"[{world}] Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_VINCENT, rate_limit_retry=True, content=msg, username="Nunyunuwi",
                                     avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # syncronised server
            print("syncronised")
            msg = f"[{world}] Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_SYNCHRONISED, rate_limit_retry=True, content=msg, username="Nunyunuwi",
                                     avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # kenzie server
            print("kenzie")
            msg = f"[{world}] Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_KENZIE, rate_limit_retry=True, content=msg, username="Nunyunuwi",
                                     avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # badger server
            print("badger")
            mentions = {
                "roles": [ROLE_EW_BADGER, ROLE_SHB_BADGER, ROLE_STB_BADGER]
            }
            if l == 0:
                msg = f"<@&{ROLE_EW_BADGER}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            if l == 1:
                msg = f"<@&{ROLE_SHB_BADGER}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            if stb == 1:
                msg = f"<@&{ROLE_STB_BADGER}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."

            webhook = DiscordWebhook(url=WEBHOOK_BADGER, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # deliah server
            print("deliah")
            msg = f"[{world}] Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_DELIAH, rate_limit_retry=True, content=msg, username="Nunyunuwi",
                                     avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # sweeper server
            print("sweeper")
            mentions = {
                "roles": [ROLE_SWEEPER]
            }
            msg = f"<@&{ROLE_SWEEPER}> [{world}] Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_SWEEPER, rate_limit_retry=True, content=msg, username="Nunyunuwi",
                                     avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # unicorn server
            print("unicorn")
            mentions = {
                "roles": [ROLE_EW_UNICORN, ROLE_SHB_UNICORN, ROLE_STB_UNICORN]
            }
            if l == 0:
                msg = f"<@&{ROLE_EW_UNICORN}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            if l == 1:
                msg = f"<@&{ROLE_SHB_UNICORN}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            if stb == 1:
                msg = f"<@&{ROLE_STB_UNICORN}> **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."

            webhook = DiscordWebhook(url=WEBHOOK_UNICORN, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # ctlantaa server
            print("ctlantaa")
            msg = f"[{world}] Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_CTLANTAA, rate_limit_retry=True, content=msg, username="Nunyunuwi",
                                     avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # izzy server
            print("izzy")
            msg = f"[{world}] Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_IZZY, rate_limit_retry=True, content=msg, username="Nunyunuwi",
                                     avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # all done

            time = parm[0]
            if stb == 0:
                await update_sheet(world, "Running", time, l)

            await msg1.delete()
            await ctx.message.add_reaction('✅')


@bot.command(name="advmanual", aliases=['adm', 'mshout', 'msh'],
             help='Advertise your train. Put multi-part parameters in quotes (eg. .mshout "[Twintania] '
                  'Hunt train starting in 10 minutes at Fort Jobb")')
async def madvertise(ctx, message, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print(f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    username = ctx.message.author.display_name
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    print(message)

    if len(message) < 6:
        await ctx.message.add_reaction("❌")
        await ctx.send("Message needs to be over 5 characters.")
        return

    parm = parse_parameters(None, legacy)
    l = parm[1]
    stb = parm[2]
    if l == 0:
        msg = (f"About to send this notification to various servers: ```@Endwalker_role {message} "
               f"(Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel.")
    if l == 1:
        msg = (f"About to send this notification to various servers: ```@Shadowbringers_role {message} "
               f"(Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel.")
    if stb == 1:
        msg = (f"About to send this notification to various servers: ```@Stormblood_role {message} "
               f"(Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel.")

    msg1 = await ctx.send(msg)
    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id == msg1.id and str(reaction.emoji) == '✅' and user.id == ctx.author.id

    try:
        res = await bot.wait_for("reaction_add", check=check, timeout=30)
    except asyncio.TimeoutError:
        print("Timed out")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        pass
    else:
        if res:
            reaction, user = res
            print(reaction.emoji)

            # test discord
            print("test")
            mentions = {
                "roles": [ROLE_EW_TEST, ROLE_SHB_TEST]
            }
            if l == 0:
                msg = f"<@&{ROLE_EW_TEST}> {message} (Conductor: {username})."
            if l == 1:
                msg = f"<@&{ROLE_SHB_TEST}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_TEST, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # kettu discord
            print("kettu")
            mentions = {
                "roles": [ROLE_EW_KETTU, ROLE_SHB_KETTU, ROLE_STB_KETTU]
            }
            if l == 0:
                msg = f"<@&{ROLE_EW_KETTU}> {message} (Conductor: {username})."
            if l == 1:
                msg = f"<@&{ROLE_SHB_KETTU}> {message} (Conductor: {username})."
            if stb == 1:
                msg = f"<@&{ROLE_STB_KETTU}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_KETTU, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # ch discord
            print("ch")
            mentions = {
                "roles": [ROLE_EW_CH, ROLE_SHB_CH, ROLE_STB_CH]
            }
            if l == 0:
                msg = f"<@&{ROLE_EW_CH}> {message} (Conductor: {username})."
            if l == 1:
                msg = f"<@&{ROLE_SHB_CH}> {message} (Conductor: {username})."
            if stb == 1:
                msg = f"<@&{ROLE_STB_CH}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_CH, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # angel server
            print("angel")
            if l == 0:
                msg = f"{message} (Conductor: {username})."
                webhook = DiscordWebhook(url=WEBHOOK_ANGEL, rate_limit_retry=True, content=msg,
                                         allowed_mentions=mentions, username="Nunyunuwi",
                                         avatar_url="https://jvaarani.kapsi.fi/nuny.png")
                resp = webhook.execute()

            # wrkjn server
            print("wrkjn")
            if l == 0:
                msg = f"{message} (Conductor: {username})."
                webhook = DiscordWebhook(url=WEBHOOK_WRKJN, rate_limit_retry=True, content=msg,
                                         allowed_mentions=mentions, username="Nunyunuwi",
                                         avatar_url="https://jvaarani.kapsi.fi/nuny.png")
                resp = webhook.execute()

            # ashie server
            print("ashie")
            mentions = {
                "roles": [ROLE_ASHIE]
            }
            msg = f"<@&{ROLE_ASHIE}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_ASHIE, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # faloop discord
            print("faloop")
            mentions = {
                "roles": [ROLE_EW_FALOOP, ROLE_SHB_FALOOP, ROLE_STB_FALOOP]
            }
            if l == 0:
                msg = f"<@&{ROLE_EW_FALOOP}> {message} (Conductor: {username})."
            if l == 1:
                msg = f"<@&{ROLE_SHB_FALOOP}> {message} (Conductor: {username})."
            if stb == 1:
                msg = f"<@&{ROLE_STB_FALOOP}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_FALOOP, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # vincent server
            print("vincent")
            msg = f"{message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_VINCENT, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # synchronised server
            print("synchronised")
            msg = f"{message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_SYNCHRONISED, rate_limit_retry=True, content=msg,
                                     allowed_mentions=mentions, username="Nunyunuwi",
                                     avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # kenzie server
            print("kenzie")
            msg = f"{message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_KENZIE, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # badger discord
            print("badger")
            mentions = {
                "roles": [ROLE_EW_BADGER, ROLE_SHB_BADGER, ROLE_STB_BADGER]
            }
            if l == 0:
                msg = f"<@&{ROLE_EW_BADGER}> {message} (Conductor: {username})."
            if l == 1:
                msg = f"<@&{ROLE_SHB_BADGER}> {message} (Conductor: {username})."
            if stb == 1:
                msg = f"<@&{ROLE_STB_BADGER}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_BADGER, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # deliah server
            print("deliah")
            msg = f"{message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_DELIAH, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # sweeper server
            print("sweeper")
            mentions = {
                "roles": [ROLE_SWEEPER]
            }
            msg = f"<@&{ROLE_SWEEPER}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_SWEEPER, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # unicorn discord
            print("unicorn")
            mentions = {
                "roles": [ROLE_EW_UNICORN, ROLE_SHB_UNICORN, ROLE_STB_UNICORN]
            }
            if l == 0:
                msg = f"<@&{ROLE_EW_UNICORN}> {message} (Conductor: {username})."
            if l == 1:
                msg = f"<@&{ROLE_SHB_UNICORN}> {message} (Conductor: {username})."
            if stb == 1:
                msg = f"<@&{ROLE_STB_UNICORN}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_UNICORN, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # ctlantaa server
            print("ctlantaa")
            msg = f"{message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_CTLANTAA, rate_limit_retry=True, content=msg,
                                     allowed_mentions=mentions, username="Nunyunuwi",
                                     avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # izzy server
            print("izzy")
            msg = f"{message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_IZZY, rate_limit_retry=True, content=msg, allowed_mentions=mentions,
                                     username="Nunyunuwi", avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp = webhook.execute()

            # all sent

            await msg1.delete()
            await ctx.message.add_reaction('✅')


@bot.event
async def on_ready():
    global ready
    print(f'{bot.user} has connected to Discord!')
    ready = 1


@tasks.loop(seconds=60)
async def STLoop():
    now = datetime.datetime.strftime(datetime.datetime.utcnow(), "%H:%M")
    if ready == 1:
        await bot.change_presence(activity=discord.Game(f"Server time: {now}"))


@tasks.loop(seconds=1800)
async def StatusLoop():
    if ready == 1:
        try:
            await periodicstatus()
        except:
            print("statusloop error")


@tasks.loop(seconds=300)
async def SheetLoop():
    await update_from_sheets()


# sonar stuff init
conn = sqlite3.connect('hunt.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

cursor = conn.cursor()

# we're interested in light dc

dc = ("Light",)
sel = "SELECT worlds.id from worlds INNER JOIN dcs ON worlds.datacenterid = dcs.id WHERE dcs.name = ?"
cursor.execute(sel, dc)
r = cursor.fetchall()

worldidlist = []
for w in r:
    worldidlist.append(w[0])

# we're interested in A-rank hunts

cursor.execute('SELECT id from hunts WHERE rank=2')
r = cursor.fetchall()

huntidlist = []
for h in r:
    huntidlist.append(h[0])

# SHB+ A-rank hunts for snipe notifications

cursor.execute('SELECT id from hunts WHERE rank=2 AND expansion>=4')
r = cursor.fetchall()

huntidlist_nuts = []
for h in r:
    huntidlist_nuts.append(h[0])

# S-rank list for special purposes

cursor.execute('SELECT id from hunts WHERE rank=3')
r = cursor.fetchall()

huntidlist_s = []
for h in r:
    huntidlist_s.append(h[0])

check = """SELECT 
    key, huntid, worldid, 
    zoneid, instanceid, players, 
    currenthp, maxhp, lastseen, 
    lastfound, lastkilled, lastupdated, 
    lastuntouched,actorid,status,x,y
    FROM 'hunt' WHERE key = ?"""
ins = """INSERT OR REPLACE INTO 'hunt' (
    key, huntid, worldid, 
    zoneid, instanceid, players, 
    currenthp, maxhp, lastseen, 
    lastfound, lastkilled, lastupdated, 
    lastuntouched,actorid,status,x,y) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""


def relay_to_sql(msg, status):
    return (msg['Relay']['Key'],
            msg['Relay']['Id'],
            msg['Relay']['WorldId'],
            msg['Relay']['ZoneId'],
            msg['Relay']['InstanceId'],
            msg['Relay']['Players'],
            msg['Relay']['CurrentHp'],
            msg['Relay']['MaxHp'],
            msg['LastSeen'],
            msg['LastFound'],
            msg['LastKilled'],
            msg['LastUpdated'],
            msg['LastUntouched'],
            msg['Relay']['ActorId'],
            status,
            msg['Relay']['Coords']['X'],
            msg['Relay']['Coords']['Y']
            )


def sql_to_relay(sql):
    r = {}
    r['Key'] = sql[0]
    r['Id'] = sql[1]
    r['WorldId'] = sql[2]
    r['ZoneId'] = sql[3]
    r['InstanceId'] = sql[4]
    r['Players'] = sql[5]
    r['CurrentHp'] = sql[6]
    r['MaxHp'] = sql[7]
    r['LastSeen'] = sql[8]
    r['LastFound'] = sql[9]
    r['LastKilled'] = sql[10]
    r['LastUpdated'] = sql[11]
    r['LastUntouched'] = sql[12]
    r['ActorId'] = sql[13]
    r['Status'] = sql[14]
    r['x'] = sql[15]
    r['y'] = sql[16]
    return (r)


async def huntname(msg):
    expansions = {1: 'ARR',
                  2: 'HW',
                  3: 'STB',
                  4: 'SHB',
                  5: 'EW'}
    instances = {0: '',
                 1: ' (1)',
                 2: ' (2)',
                 3: ' (3)'}
    sel = "SELECT name,expansion FROM hunts WHERE id = ?"
    h = cursor.execute(sel, (msg["Relay"]["Id"],)).fetchone()
    sel = "SELECT name FROM worlds WHERE id = ?"
    w = cursor.execute(sel, (msg["Relay"]["WorldId"],)).fetchone()
    return ({'exp': expansions[h[1]],
             'world': w[0],
             'name': h[0],
             'instance': instances[int(msg["Relay"]["InstanceId"])]})


@tasks.loop(count=None)
async def websocketrunner():
    await asyncio.sleep(15)
    while True:
        try:
            async with connect(SONAR_WEBSOCKET) as websocket:
                while True:
                    try:
                        s_msg = json.loads(await websocket.recv())
                        if (s_msg["Relay"]["Type"] == "Hunt"):
                            if (s_msg["Relay"]["WorldId"] in worldidlist):
                                if (s_msg["Relay"]["Id"] in huntidlist):
                                    s_msg["LastSeen"] = datetime.datetime.utcfromtimestamp(s_msg["LastSeen"] / 1000)
                                    s_msg["LastFound"] = datetime.datetime.utcfromtimestamp(s_msg["LastFound"] / 1000)
                                    s_msg["LastKilled"] = datetime.datetime.utcfromtimestamp(s_msg["LastKilled"] / 1000)
                                    s_msg["LastUpdated"] = datetime.datetime.utcfromtimestamp(
                                        s_msg["LastUpdated"] / 1000)
                                    s_msg["LastUntouched"] = datetime.datetime.utcfromtimestamp(
                                        s_msg["LastUntouched"] / 1000)

                                    h = cursor.execute(check, (s_msg["Relay"]["Key"],)).fetchone()
                                    if h == None:
                                        d = await huntname(s_msg)
                                        await sonar_log(
                                            f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} spotted first time after database refresh at {int((s_msg["Relay"]["CurrentHp"] / s_msg["Relay"]["MaxHp"]) * 100)}% HP.')
                                        status = 1
                                        if s_msg["LastUpdated"] == s_msg["LastUntouched"]:
                                            status = 2
                                    else:
                                        status = 0
                                        h = sql_to_relay(h)
                                        status = h["Status"]
                                        # actorid changed -> new sighting
                                        if (h["ActorId"] != s_msg["Relay"]["ActorId"]):
                                            d = await huntname(s_msg)
                                            await sonar_log(
                                                f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} spotted with a new actor id at {int((s_msg["Relay"]["CurrentHp"] / s_msg["Relay"]["MaxHp"]) * 100)}% HP.')
                                            status = 1
                                            if s_msg["LastUpdated"] == s_msg["LastUntouched"]:
                                                # untouched
                                                status = 2
                                        if ((s_msg["LastUpdated"] - s_msg[
                                            "LastUntouched"]).total_seconds() > 15 and status != 1):
                                            status = 1
                                            d = await huntname(s_msg)
                                            await sonar_log(
                                                f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} has been pulled and is at {int((s_msg["Relay"]["CurrentHp"] / s_msg["Relay"]["MaxHp"]) * 100)}% HP. ({s_msg["Relay"]["Players"]} players nearby)')
                                            if (s_msg["Relay"]["Players"] < 10 and s_msg["Relay"][
                                                "Id"] in huntidlist_nuts):
                                                await scout_log(
                                                    f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} has been pulled and is at {int((s_msg["Relay"]["CurrentHp"] / s_msg["Relay"]["MaxHp"]) * 100)}% HP. ({s_msg["Relay"]["Players"]} players nearby) (SNIPE?)')
                                        if (s_msg["LastUpdated"] == s_msg["LastUntouched"] and status == 1):
                                            status = 2
                                            d = await huntname(s_msg)
                                            await sonar_log(
                                                f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was reset ({s_msg["Relay"]["Players"]} players nearby).')
                                            if (s_msg["Relay"]["Players"] < 10 and s_msg["Relay"][
                                                "Id"] in huntidlist_nuts):
                                                await scout_log(
                                                    f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was reset ({s_msg["Relay"]["Players"]} players nearby). (SNIPE?)')
                                        if (s_msg["Relay"]["CurrentHp"] == 0 and status != 0):
                                            status = 0
                                            d = await huntname(s_msg)
                                            await sonar_log(
                                                f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was killed ({s_msg["Relay"]["Players"]} players nearby).')
                                            if (s_msg["Relay"]["Players"] < 10 and s_msg["Relay"][
                                                "Id"] in huntidlist_nuts):
                                                await scout_log(
                                                    f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was killed ({s_msg["Relay"]["Players"]} players nearby). (SNIPE?)')
                                    h = relay_to_sql(s_msg, status)
                                    cursor.execute(ins, h)
                                if (s_msg["Relay"]["Id"] in huntidlist_s):
                                    s_msg["LastSeen"] = datetime.datetime.utcfromtimestamp(s_msg["LastSeen"] / 1000)
                                    s_msg["LastFound"] = datetime.datetime.utcfromtimestamp(s_msg["LastFound"] / 1000)
                                    s_msg["LastKilled"] = datetime.datetime.utcfromtimestamp(s_msg["LastKilled"] / 1000)
                                    s_msg["LastUpdated"] = datetime.datetime.utcfromtimestamp(
                                        s_msg["LastUpdated"] / 1000)
                                    s_msg["LastUntouched"] = datetime.datetime.utcfromtimestamp(
                                        s_msg["LastUntouched"] / 1000)

                                    h = cursor.execute(check, (s_msg["Relay"]["Key"],)).fetchone()
                                    if h == None:
                                        d = await huntname(s_msg)
                                        print(
                                            f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} spotted first time after database refresh at {int((s_msg["Relay"]["CurrentHp"] / s_msg["Relay"]["MaxHp"]) * 100)}% HP.')
                                        status = 1
                                        if s_msg["LastUpdated"] == s_msg["LastUntouched"]:
                                            status = 2
                                    else:
                                        status = 0
                                        h = sql_to_relay(h)
                                        status = h["Status"]
                                        # actorid changed -> new sighting
                                        if (h["ActorId"] != s_msg["Relay"]["ActorId"]):
                                            d = await huntname(s_msg)
                                            print(
                                                f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} spotted with a new actor id at {int((s_msg["Relay"]["CurrentHp"] / s_msg["Relay"]["MaxHp"]) * 100)}% HP.')
                                            status = 1
                                            if s_msg["LastUpdated"] == s_msg["LastUntouched"]:
                                                # untouched
                                                status = 2
                                        if ((s_msg["LastUpdated"] - s_msg[
                                            "LastUntouched"]).total_seconds() > 15 and status != 1):
                                            status = 1
                                            d = await huntname(s_msg)
                                            print(
                                                f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} has been pulled and is at {int((s_msg["Relay"]["CurrentHp"] / s_msg["Relay"]["MaxHp"]) * 100)}% HP. ({s_msg["Relay"]["Players"]} players nearby)')
                                            if (s_msg["Relay"]["Players"] < 10):
                                                await spec_log(
                                                    f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} has been pulled and is at {int((s_msg["Relay"]["CurrentHp"] / s_msg["Relay"]["MaxHp"]) * 100)}% HP. ({s_msg["Relay"]["Players"]} players nearby) (SNIPE?)')
                                        if (s_msg["LastUpdated"] == s_msg["LastUntouched"] and status == 1):
                                            status = 2
                                            d = await huntname(s_msg)
                                            print(
                                                f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was reset ({s_msg["Relay"]["Players"]} players nearby).')
                                            if (s_msg["Relay"]["Players"] < 10):
                                                await spec_log(
                                                    f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was reset ({s_msg["Relay"]["Players"]} players nearby). (SNIPE?)')
                                        if (s_msg["Relay"]["CurrentHp"] == 0 and status != 0):
                                            status = 0
                                            d = await huntname(s_msg)
                                            print(
                                                f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was killed ({s_msg["Relay"]["Players"]} players nearby).')
                                            if (s_msg["Relay"]["Players"] < 10):
                                                await spec_log(
                                                    f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was killed ({s_msg["Relay"]["Players"]} players nearby). (SNIPE?)')
                                    h = relay_to_sql(s_msg, status)
                                    cursor.execute(ins, h)

                    except KeyError as errori:
                        print(f"Keyerror tuli: {errori}")
                        pass
                    conn.commit()
        except websockets.exceptions.WebSocketException as errori:
            print(f"Socket error: {errori}")
        await asyncio.sleep(30)


SheetLoop.start()
STLoop.start()
StatusLoop.start()
websocketrunner.start()

bot.run(TOKEN)
