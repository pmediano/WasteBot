import telegram
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters

import sys
import numpy.random as rn

from Crypto.Cipher import AES
import base64

"""
TODO list:
    - Implement persistent leaderboard
    - Command to print current poll state
    - Put token in separate encrypted file (to push to Github)
    - Ensassiment
"""

ENCODED_TOKEN  = 'LTB/7iAGE/OG4isvyJ7Nsr/zJ1kdqWqq2sEYqWPFJB6RF6PU6HURRqQc+oSa7lbF36ZyJSZi+/WrCAG9PQFIZw=='
votes = {}
leaderboard = {}
users = []
candidate = None
IDLE = 0
TELLING = 1
POLLING = 2
STATE = IDLE

cant_begin_phrases = ['Finish the previous story first',
                      'For fucks sake, let the other story finish',
                      'Shut up and let us listen to the previous story']

def begin_callback(bot, update):
    print 'begin'
    global candidate, STATE
    group_id = update.message.chat_id
    if STATE != IDLE:
        bot.send_message(chat_id=group_id, text=rn.choice(cant_begin_phrases))
    else:
        STATE = TELLING
        users.append(update.effective_user)
        candidate = update.effective_user
        print 'candidate', candidate
        print 'users', users
        sender_name = update.effective_user.first_name
        bot.send_message(chat_id=update.message.chat_id, text='Everyone shut up and listen to ' + sender_name)

def end_callback(bot, update):
    print 'end'
    global STATE
    sender = update.effective_user.id
    group_id = update.message.chat_id

    if STATE != TELLING:
        bot.send_message(chat_id=group_id, text='No story to end')
        return

    if sender != candidate.id:
        bot.send_message(chat_id=group_id, text='Ssssh. Let ' + candidate.first_name + ' finish the story')
        return
    votes = {}
    bot.send_message(chat_id=group_id, text='Cool story bro')
    bot.send_message(chat_id=group_id, text='Let the waste games begin!')
    STATE = POLLING

def vote_callback(bot, update, vote):
    sender = update.effective_user.id
    sender_name = update.effective_user.first_name
    if STATE != POLLING:
        bot.send_message(chat_id=update.message.chat_id, text=sender_name + ' is stoopid and thinks he can vote whenever he wants')
    elif sender == candidate.id:
        bot.send_message(chat_id=update.message.chat_id, text='Voting on your own story, you cheeky cunt')
    else:
        bot.send_message(chat_id=update.message.chat_id, text=sender_name + ' voted')
        votes[sender] = vote
        check_result(bot, update)

def leaderboard_callback(bot, update):
    print 'leader'
    bot.send_message(chat_id=update.message.chat_id, text=str(leaderboard))

def check_result(bot, update):
    print 'check'
    try:
        waste_votes = len(filter(lambda x: x > 0, votes.values()))
        nah_votes = len(filter(lambda x: x < 0, votes.values()))
        # Do not count the bot or the poster himself
        # TODO: would be better to not count any bots
        group_id = update.message.chat_id
        nb_group_members = bot.get_chat_members_count(group_id) - 2
        quorum = int(nb_group_members/2) + 1
        if waste_votes >= quorum:
            finish_poll(bot, update, True)
        if nah_votes >= quorum:
            finish_poll(bot, update, False)
    except:
        print 'Something got fucked'

def finish_poll(bot, update, is_waste):
    print 'Finish poll'
    global votes, STATE
    STATE = IDLE
    votes = {}
    if is_waste:
        bot.send_message(chat_id=update.message.chat_id, text='You are waste')
        if candidate.id in leaderboard:
            leaderboard[candidate.id] += 1
        else:
            leaderboard[candidate.id] = 1
    else:
        bot.send_message(chat_id=update.message.chat_id, text='Not waste enough. Try again next time.')

def votequery_callback(bot, update):
    print 'query'
    group_id = update.message.chat_id
    if STATE != POLLING:
        bot.send_message(chat_id=group_id, text='Not polling')
    else:
        print 'Print query'
        waste_votes = len(filter(lambda x: x > 0, votes.values()))
        print 'waste_votes'
        nah_votes = len(filter(lambda x: x < 0, votes.values()))
        print 'nah_votes'
        nb_group_members = bot.get_chat_members_count(group_id) - 2
        print 'nb_group_members'
        quorum = int(nb_group_members/2) + 1
        print 'quorum'
        s = 'Votes for waste: ' + str(waste_votes) + '\nVotes against: ' + str(nah_votes) + '\nVotes needed: ' + str(quorum)
        print s
        bot.send_message(chat_id=group_id, text=s)

def unknown(bot, update):
    print 'unknown'
    bot.send_message(chat_id=update.message.chat_id, text='Wtf u talking about?')

def main():

    args = sys.argv

    if len(args) < 2:
        print 'Need a key'
        sys.exit()

    secret_key = args[1].rjust(16)

    cipher = AES.new(secret_key,AES.MODE_ECB)
    decoded = cipher.decrypt(base64.b64decode(ENCODED_TOKEN))
    token = decoded.strip()

    # Botfathers's WasteBot token
    updater = Updater(token=token)
    dispatcher = updater.dispatcher

    begin_handler = CommandHandler('beginwaste', begin_callback)
    dispatcher.add_handler(begin_handler)

    end_handler = CommandHandler('endwaste', end_callback)
    dispatcher.add_handler(end_handler)

    upvote_handler = CommandHandler('waste', lambda b,u: vote_callback(b, u, +1))
    dispatcher.add_handler(upvote_handler)

    downvote_handler = CommandHandler('nah', lambda b,u: vote_callback(b, u, -1))
    dispatcher.add_handler(downvote_handler)

    votequery_handler = CommandHandler('votes', votequery_callback)
    dispatcher.add_handler(votequery_handler)

    leaderboard_handler = CommandHandler('leaderboard', leaderboard_callback)
    dispatcher.add_handler(leaderboard_handler)

    dispatcher.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling(timeout=1)

    # Block until SIGINT/TERM is received
    updater.idle()


if __name__ == '__main__':
    main()

