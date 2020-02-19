#!/usr/bin/env python

import os
import logging
import feedparser
import sqlite3

import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def replyHelpList(update, context):
    update.message.reply_text('''Command:
/sub
/unsub
/list
/help''')


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def replyLastUpdate(update, context):
    url = update.message.text.split('/sub ')[1]
    url_parse = feedparser.parse(url)
    site_title = url_parse.feed.title
    last_title = url_parse.entries[0].title
    last_link = url_parse.entries[0].link

    update.message.reply_text(
        '<b>{}</b>\n<a href="{}">{}</a>'.format(
            site_title, last_link, last_title),
        parse_mode=telegram.ParseMode.HTML,
        disable_web_page_preview=True
    )


def sqlite3Exec(sqlCommand):
    conn = sqlite3.connect('rssbot.db')
    c = conn.cursor()
    c.execute(sqlCommand)
    logger.info(sqlCommand)
    conn.commit()
    c.close()
    conn.close()


def addUser(update, context):
    user_id = update.message.chat.id
    command = '''CREATE TABLE IF NOT EXISTS USER_%s (
        SITELINK TEXT,
        SITETITLE TEXT,
        LASTLINK TEXT,
        LASTTITLE TEXT);''' % (user_id)
    sqlite3Exec(command)


def rowCount(uid):
    conn = sqlite3.connect('rssbot.db')
    c = conn.cursor()
    row_count = c.execute('SELECT COUNT() FROM USER_%s' % (uid)).fetchone()[0]
    conn.commit()
    c.close()
    conn.close()
    return row_count


def getFeedsList(uid):
    conn = sqlite3.connect('rssbot.db')
    c = conn.cursor()
    feedsList = c.execute('SELECT * FROM USER_%s;' % (uid)).fetchall()
    conn.commit()
    c.close()
    conn.close()
    return feedsList


def feedIsExist(feedsList, site_link):
    exist = False
    for feed in feedsList:
        if site_link == feed[0]:
            exist = True
    return exist


def addFeed(update, context):
    try:
        url = update.message.text.split('/sub ')[1]
    except:
        replyHelpList(update, context)
        return

    try:
        url_parse = feedparser.parse(url)
        site_title = url_parse.feed.title
        site_link = url
        last_title = url_parse.entries[0].title
        last_link = url_parse.entries[0].link
    except:
        update.message.reply_text("Can't parse feed: {}".format(url))
        return

    uid = update.message.chat.id

    exist = feedIsExist(getFeedsList(uid), site_link)
    if (exist):
        update.message.reply_text(
            '<a href="{}">{}</a> already subscribed.'.format(
                site_link, site_title),
            parse_mode=telegram.ParseMode.HTML
        )
        return

    # sqlite3Exec('''INSERT INTO USER_%s (SITELINK, SITETITLE, LASTLINK, LASTTITLE) VALUES ('%s', '%s', '%s', '%s');''' % (
    sqlite3Exec('''INSERT INTO USER_%s VALUES ('%s', '%s', '%s', '%s');''' % (
        uid, site_link, site_title, last_link, last_title))

    update.message.reply_text(
        '<a href="{}">{}</a> subscribe successed.'.format(
            site_link, site_title),
        parse_mode=telegram.ParseMode.HTML
    )


def listFeeds(update, context):
    feedsList = getFeedsList(uid=update.message.chat.id)

    reply_list = "<b>feeds list:</b>"
    for feed in feedsList:
        reply_list += '\n<a href="{}">{}</a>'.format(feed[0], feed[1])

    update.message.reply_text(
        reply_list, parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=True)


def delFeed(update, context):
    try:
        url = update.message.text.split('/unsub ')[1]
    except:
        replyHelpList(update, context)
        return

    try:
        url_parse = feedparser.parse(url)
        site_title = url_parse.feed.title
        site_link = url
        last_title = url_parse.entries[0].title
        last_link = url_parse.entries[0].link
    except:
        update.message.reply_text("Can't parse feed: {}".format(url))
        return

    uid = update.message.chat.id

    exist = feedIsExist(getFeedsList(uid), site_link)

    if (exist):
        sqlite3Exec(
            "DELETE FROM USER_{} WHERE SITELINK = '{}';".format(uid, site_link))
    else:
        update.message.reply_text('<a href="{}">{}</a> have not subscribed.'.format(
            site_link, site_title), parse_mode=telegram.ParseMode.HTML)
        return

    exist = feedIsExist(getFeedsList(uid), site_link)

    if (exist):
        update.message.reply_text(
            '<a href="{}">{}</a> unsubscribe failed.'.format(
                site_link, site_title),
            parse_mode=telegram.ParseMode.HTML
        )
    else:
        update.message.reply_text(
            '<a href="{}">{}</a> unsubscribe successed.'.format(
                site_link, site_title),
            parse_mode=telegram.ParseMode.HTML
        )


# def updateFeed(update, context):
#     uid = update.message.chat.id
#     feedsList = getFeedsList(uid)

#     try:
#         url_parse = feedparser.parse(url)
#         site_title = url_parse.feed.title
#         site_link = url
#         last_title = url_parse.entries[0].title
#         last_link = url_parse.entries[0].link
#     except:
#         update.message.reply_text("Can't parse feed: {}".format(url))
#         return

#     for feed in feedsList:
#         url_parse = feedparser.parse(url)
#         last_link = url_parse.entries[0].link
#         last_link_in_db = feed[2]

#         if last_link != last_link_in_db:
#             pass
#             # 更改


def main():
    token = os.getenv("TOKEN")
    updater = Updater(token, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", addUser))
    dp.add_handler(CommandHandler("sub", addFeed))
    dp.add_handler(CommandHandler("unsub", delFeed))
    dp.add_handler(CommandHandler("list", listFeeds))
    dp.add_handler(CommandHandler("help", replyHelpList))
    # dp.add_handler(CommandHandler("update", updateFeed))

    dp.add_handler(MessageHandler(Filters.text, echo))

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
