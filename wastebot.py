import telegram
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters, BaseFilter

import sys
from glob import glob
import pickle
import numpy.random as rn
import logging
import datetime

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

beginwaste  - Start telling waste story
endwaste    - Finish telling waste story
waste       - Approve story's wastemanship
nah         - Story wasn't that great
votes       - Get current vote count
leaderboard - Print wasteman leaderboard
story       - Tell me a truly wasteful story
extend      - Allow people to vote for another day

"""

ENCODED_TOKEN = 'LTB/7iAGE/OG4isvyJ7Nsr/zJ1kdqWqq2sEYqWPFJB6RF6PU6HURRqQc+oSa7lbF36ZyJSZi+/WrCAG9PQFIZw=='
votes         = {}
candidate     = None
storylog      = []
IDLE          = 0
TELLING       = 1
POLLING       = 2
STATE         = IDLE

logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)


#--------------------------------------------------------------#
#                       CHATTINESS                             #
#--------------------------------------------------------------#
max_days_init       = 2
max_extensions      = 3

cant_begin_phrases  = [ 'Finish the previous story first',
                        'For fucks sake, let the other story finish',
                        'Shut up and let us listen to the previous story']

ext_allowed_phrases = [ 'Because you\'ve asked me nicely, you get more time to vote. Use \extend',
                        'Only if politicians had your luck! Use \extend to get one more day at the polls',
                        'You\'ve opened Pandora\'s box. I hope you\'re proud. Use \extend' ]

ext_denied_phrases  = [ 'You cheeky cunt, you want even more time to vote!? Extension denied.',
                        'You\'re as undecided as a third world country government. Extension denied.' ]

ext_allowed_confirm =   'You have one more day to vote for this story.'
ext_denied_confirm  =   'Your request is DENIED.'


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
    global extensions_allowed

    waste_votes = len(filter(lambda x: x > 0, votes.values()))
    nah_votes = len(filter(lambda x: x < 0, votes.values()))
    # Do not count the bot or the poster himself
    # TODO: would be better to not count any bots
    group_id = update.message.chat_id
    nb_group_members = bot.get_chat_members_count(group_id) - 2
    quorum = int(nb_group_members/2) + 1
    if waste_votes >= quorum:
        finish_poll(bot, update, True)
    elif nah_votes >= quorum:
        finish_poll(bot, update, False)
    elif check_expiry():
        if (extensions_allowed < max_extensions):
            bot.send_message(chat_id=group_id, text=rn.choice(ext_allowed_phrases))
        else:
            bot.send_message(chat_id=group_id, text=rn.choice(ext_denied_phrases))


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
        with open('stories/' + candidate.first_name + str(leaderboard[candidate.id]) + '.pkl', 'w') as f:
            pickle.dump(storylog, f)
    else:
        bot.send_message(chat_id=update.message.chat_id, text='Not waste enough. Try again next time.')


def check_expiry():
    """
    Check whether current poll has become stale
    """
    global start_time, max_days
    now_time = datetime.datetime.now()
    day_diff = (now_time - start_time).days
    return (day_diff > max_days)


#--------------------------------------------------------------#
#                       CALLBACKS                              #
#--------------------------------------------------------------#
def begin_callback(bot, update):
    """
    Start telling a story and make the storyteller a wasteman candidate.
    Also log the date and time for supporting extensions.
    Does nothing if STATE != IDLE.
    """
    global candidate, STATE, storylog, start_time, max_days
    group_id = update.message.chat_id
    if STATE != IDLE:
        bot.send_message(chat_id=group_id, text=rn.choice(cant_begin_phrases))
    else:
        STATE       = TELLING
        candidate   = update.effective_user
        start_time  = datetime.datetime.now()
        max_days    = max_days_init
        sender_name = candidate.first_name
        storylog    = []
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
        bot.send_message(chat_id=update.message.chat_id, text=sender_name + ', you\'re stoopid and you think you can vote whenever you want')
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

    if len(args) > 1:
        bot.send_message(chat_id=group_id, text='Send me exactly one story name')

    elif len(args) == 0:
        all_stories = glob('stories/*pkl')
        msg = 'Available stories:\n'
        for i,n in enumerate(all_stories):
            msg += str(i) + ': ' + n.split('/')[1][:-4] + '\n'
        bot.send_message(chat_id=group_id, text=msg)

    elif len(args) == 1:
        story_name = args[0]
        with open('stories/' + story_name + '.pkl', 'r') as f:
            log = pickle.load(f)

        msg = ''
        for m in log:
            sender = m.from_user.first_name
            txt = m.text
            msg += '*' + sender + '*:\n' + txt + '\n\n'
        bot.send_message(chat_id=group_id, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)


def extend_callback(bot, update):
    """
    Allow the quorum time to be extended by a day, but only 3 times
    """
    global extensions_requested, max_days

    group_id = update.message.chat_id
    if (extensions_requested < max_extensions):
        extensions_requested += 1
        max_days += 1
        bot.send_message(chat_id=group_id, text=ext_allowed_confirm)
    else:
        bot.send_message(chat_id=group_id, text=ext_denied_confirm)


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

    story_handler = CommandHandler('story', story_callback, pass_args=True)
    dispatcher.add_handler(story_handler)

    extend_handler = CommandHandler('extend', extend_callback, pass_args=True)
    dispatcher.add_handler(extend_handler)

    dispatcher.add_handler(MessageHandler(Filters.command, unknown))

    log_handler = MessageHandler(StoryFilter() & Filters.text, log_callback)
    dispatcher.add_handler(log_handler)

    updater.start_polling(timeout=1)

    # Block until SIGINT/TERM is received
    updater.idle()


if __name__ == '__main__':
    main()

