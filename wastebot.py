import telegram
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters, BaseFilter

import sys
import pickle
import numpy.random as rn

from Crypto.Cipher import AES
import base64

"""
TODO list:
    - Do not count other bots when calculating quorum
    - Store media with wasteman stories
    - Ensassiment
        * Randomised responses
        * Stickerrrrrs
        * Pretty leaderboard print

"""

"""
Command names and descriptions, as sent to the Botfather

beginwaste - Start telling waste story
endwaste - Finish telling waste story
waste - Approve story's wastemanship
nah - Story wasn't that great
votes - Get current vote count
leaderboard - Print wasteman leaderboard
"""

ENCODED_TOKEN  = 'LTB/7iAGE/OG4isvyJ7Nsr/zJ1kdqWqq2sEYqWPFJB6RF6PU6HURRqQc+oSa7lbF36ZyJSZi+/WrCAG9PQFIZw=='
votes = {}
candidate = None
storylog = []
IDLE = 0
TELLING = 1
POLLING = 2
STATE = IDLE

cant_begin_phrases = ['Finish the previous story first',
                      'For fucks sake, let the other story finish',
                      'Shut up and let us listen to the previous story']

#--------------------------------------------------------------#
#                          UTILS                               #
#--------------------------------------------------------------#
def load_leaderboard():
    try:
        with open('leaderboard.pkl', 'r') as f:
            leaderboard, users = pickle.load(f)
    except:
        leaderboard = {}
        users = {}
    return leaderboard, users


def save_leaderboard(leaderboard, users):
    with open('leaderboard.pkl', 'w') as f:
        pickle.dump((leaderboard, users), f)


def check_result(bot, update):
    """
    Check whether current poll reached quorum and can be ended.
    """
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


def finish_poll(bot, update, is_waste):
    """
    End current poll and update leaderboard.
    """
    global votes, STATE
    STATE = IDLE
    votes = {}
    if is_waste:
        bot.send_message(chat_id=update.message.chat_id, text='You are waste')
        leaderboard, users = load_leaderboard()
        if candidate.id in leaderboard:
            leaderboard[candidate.id] += 1
        else:
            leaderboard[candidate.id] = 1
            users[candidate.id] = candidate.first_name
        with open('leaderboard.pkl', 'w') as f:
            pickle.dump((leaderboard, users), f)
        with open(candidate.first_name + str(leaderboard[candidate.id]) + '.pkl', 'w') as f:
            pickle.dump(storylog, f)
    else:
        bot.send_message(chat_id=update.message.chat_id, text='Not waste enough. Try again next time.')


#--------------------------------------------------------------#
#                       CALLBACKS                              #
#--------------------------------------------------------------#
def begin_callback(bot, update):
    """
    Start telling a story and make the storyteller a wasteman candidate.
    Does nothing if STATE != IDLE.
    """
    global candidate, STATE, storylog
    group_id = update.message.chat_id
    if STATE != IDLE:
        bot.send_message(chat_id=group_id, text=rn.choice(cant_begin_phrases))
    else:
        STATE = TELLING
        candidate = update.effective_user
        sender_name = candidate.first_name
        storylog = []
        bot.send_message(chat_id=group_id, text='Everyone shut up and listen to ' + sender_name)


def end_callback(bot, update):
    """
    Finish a wasteman story and start poll.
    """
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
    """
    Load from file and print current wasteman leaderboard.
    """
    leaderboard, users = load_leaderboard()
    group_id = update.message.chat_id
    if len(leaderboard) < 1:
        bot.send_message(chat_id=group_id, text='Empty leaderboard')
    else:
        msg = ''
        for uid in leaderboard:
            name = users[uid]
            score = leaderboard[uid]
            msg += name + ': ' + str(score) + '\n'
        bot.send_message(chat_id=group_id, text=msg)


def votequery_callback(bot, update):
    """
    Print current state of poll and number of votes needed for quorum.
    """
    group_id = update.message.chat_id
    if STATE != POLLING:
        bot.send_message(chat_id=group_id, text='Not polling')
    else:
        waste_votes = len(filter(lambda x: x > 0, votes.values()))
        nah_votes = len(filter(lambda x: x < 0, votes.values()))
        nb_group_members = bot.get_chat_members_count(group_id) - 2
        quorum = int(nb_group_members/2) + 1
        s = 'Votes for waste: ' + str(waste_votes) + '\nVotes against: ' + str(nah_votes) + '\nVotes needed: ' + str(quorum)
        bot.send_message(chat_id=group_id, text=s)


def unknown(bot, update):
    """
    Default reply to an unknown command.
    """
    bot.send_message(chat_id=update.message.chat_id, text='Wtf u talking about?')


def log_callback(bot, update):
    storylog.append(update.message)


def story_callback(bot, update, args):
    group_id = update.message.chat_id
    if len(args) != 1:
        bot.send_message(chat_id=group_id, text='Send me exactly one story name')

    story_name = args[0]
    with open(story_name + '.pkl', 'r') as f:
        log = pickle.load(f)

    for msg in log:
        sender = msg.from_user.first_name
        txt = msg.text
        bot.send_message(chat_id=group_id, text='*' + sender + '*: ' + txt, parse_mode=telegram.ParseMode.MARKDOWN)


class StoryFilter(BaseFilter):
    def filter(self, message):
        return STATE == TELLING


def main():

    args = sys.argv

    if len(args) < 2:
        print 'Need a key'
        sys.exit()

    secret_key = args[1].rjust(16)

    # Use AES decryption to obtain bot API
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

    tell_handler = CommandHandler('tell_story', story_callback, pass_args=True)
    dispatcher.add_handler(tell_handler)

    dispatcher.add_handler(MessageHandler(Filters.command, unknown))

    log_handler = MessageHandler(StoryFilter() & Filters.text, log_callback)
    dispatcher.add_handler(log_handler)

    updater.start_polling(timeout=1)

    # Block until SIGINT/TERM is received
    updater.idle()


if __name__ == '__main__':
    main()

