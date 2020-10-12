import telebot
import random
import json
import logging
from logging.handlers import RotatingFileHandler
from telebot import types
from os import walk, path


# logging config
log_file = "files/r6_callouts_bot.log"
max_log_file_size = 10  # max log file size in MB
max_log_files = 5
logger = logging.getLogger('r6_callouts')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s -  %(levelname)s - %(message)s', datefmt='%d.%m.%Y %H:%M:%S')
handler = logging.handlers.RotatingFileHandler(log_file, mode='a', maxBytes=max_log_file_size*1024*1024,
                                               backupCount=max_log_files, encoding='utf-8', delay=False)
handler.setFormatter(formatter)
logger.addHandler(handler)


class R6CalloutsBot:
    def __init__(self):
        self.config_file = "files/config.txt"
        self.users_file = "files/users.txt"
        self.quiz_file = "files/quiz.txt"
        with open(self.config_file, "r") as of:  # no handling here. Let  it crush if there's a problem with cfg
            self.cfg = json.load(of)
        try:
            with open(self.users_file, "r") as of:
                self.users = json.load(of)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.users = {}
        try:
            with open(self.quiz_file, "r") as of:
                self.quiz_separate_data = json.load(of)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.users = {}
        self.commands = None
        self.main_sticker_pull = None
        self.b_back_to_main_menu = None
        self.token = None
        self.quiz_questions = None
        self.b_all_maps = None
        self.b_main_menu = None
        self.all_maps_val = 'all maps!'
        self.quiz_options_amount = 5  # total amount of 'salt' options in a quiz question
        self.quiz_questions_amount = 5  # total amount of questions per quiz
        # default sticker to reply to other stickers. TODO: create a list of related stickers and send random.choice
        self.default_sticker = 'CAACAgIAAxkBAAIYfF-EJoGsAdKOgZr3kZkqNMU_PVDyAAIjAQACTptkAr1WNvj9PwrCGwQ'

        self.read_cfg()

        self.cancel_cmd = '/cancel'
        self.confirm_cmd = '/done'
        self.help_cmd = '/help'

        self.author = '@lavrooshka'

        # initiate bot
        self.bot = telebot.TeleBot(self.token)

        @self.bot.message_handler(commands=list(self.commands.keys()))
        def welcome(message):
            """command handler. Add new commands here if necessary"""
            if message.text == '/help':
                self.send_help_response(message)
            elif message.text == '/contact':
                self.contact_dev(message)
            elif message.text == '/cancel':
                self.cancel_handler(message)
            elif message.text == '/debug':
                output = "nope :)"
                self.bot.send_message(message.chat.id, output)
                # self.debug()

        @self.bot.message_handler(content_types=['text'])
        def replies(message):
            """message handler. Basically, processes 99% of bot activities: requests, special commands, etc."""
            msg_txt = message.text.lower()
            if msg_txt in self.commands:
                if msg_txt == 'view map callouts':
                    self.view_map_callouts(message=message, navigation="map pick")
                elif msg_txt == 'quiz':
                    self.quiz(message=message, navigation='map pick', total_questions=self.quiz_questions_amount)
                elif msg_txt == 'disclaimer':
                    self.send_disclaimer(message=message)
                elif msg_txt == '/debug':
                    output = "nope :)"
                    self.bot.send_message(message.chat.id, output)
                elif msg_txt == '/start':
                    if message.chat.id not in self.users:
                        self.users[message.chat.id] = message.chat.username
                        # dump into file
                        with open("files/users.txt", "w") as wf:
                            json.dump(self.users, wf)
                    output = "Welcome!"
                    self.main_menu(message=message, text=output)
                elif msg_txt == '/contact':
                    self.main_menu(message=message, text="work in progress for now")  # TODO reroute messages to @author
            elif message.text.lower() == 'hi':
                self.bot.send_message(message.chat.id, 'hello')
            elif message.text == '/whoami':
                output = f"name: {message.chat.username}\nchat ID: {message.chat.id}"
                self.bot.reply_to(message, output)
            # handle messages that cannot be treated as commands with some preset text
            else:
                output = "Let's stick to buttons at the botton for now"
                self.main_menu(message=message, text=output)

        # sticker handler. Replies with random sticker from prepared list
        @self.bot.message_handler(content_types=['sticker'])
        def get_sticker_id(message):
            logger.info(f"used sticker: {message.sticker.file_id}")
            self.bot.send_sticker(message.chat.id, self.default_sticker)
            # self.send_sticker(message)

    def debug(self):
        """just a placeholder for whatever we need to debug a running bot"""
        pass

    def read_cfg(self):
        """read all main self.* variables outside of __init__ to be able to re-read config after it was changed
        without restarting the bot."""
        self.commands = self.cfg['MAIN']['COMMANDS']
        self.b_back_to_main_menu = self.cfg['BUTTONS']['BACK_TO_MAIN_MENU']
        self.b_main_menu = self.cfg['BUTTONS']['MAIN_MENU']
        self.b_all_maps = self.cfg['BUTTONS']['ALL_MAPS']
        maps_buffer = {}
        for key, val in self.quiz_separate_data.items():
            for k, v in val.items():
                maps_buffer[k] = f"{key}/{v}"
        self.quiz_separate_data[self.all_maps_val] = maps_buffer
        # telegram bot token. Is used to connect to tg API
        self.token = self.cfg['MAIN']['TOKEN']

    def create_markup(self, buttons, width=2, back_to_main_menu=False, cancel_cmd=False, confirm_cmd=False):
        """create markup for provided buttons and width
        this automates bot's buttons creation for every submenu"""
        # since create_markup is inaccessible to users from telegram chat, no need to check incoming data
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=width)
        # creates custom markup for all buttons in provided list and customised row width
        iters = -(-len(buttons) // width)  # // operator, but for "ceiling".
        for i in range(1, iters + 1):
            btn_row = []
            for btn in range(1, width + 1):
                btn_pos = i * width - btn
                try:
                    btn_row.append(types.KeyboardButton(buttons[btn_pos]))
                except IndexError:
                    pass
            btn_row.reverse()
            markup.row(*btn_row)
        # add back to the main menu button if requested
        if back_to_main_menu:
            markup.add(types.KeyboardButton(self.b_back_to_main_menu))
        if cancel_cmd:
            markup.add(types.KeyboardButton(self.cancel_cmd))
        if confirm_cmd:
            markup.add(types.KeyboardButton(self.confirm_cmd))
        return markup

    def main_menu(self, message, text="Yes?"):
        """get back to the main menu and "restart" your session, so you won't get any navigation errors"""
        markup = self.create_markup(buttons=self.b_main_menu, cancel_cmd=False)
        self.bot.send_message(message.chat.id, text, reply_markup=markup)

    def view_map_callouts(self, message, navigation):
        typ = message.content_type
        if typ != 'text':
            output = "let's stick to buttons, ok?"
            msg = self.bot.reply_to(message=message, text=output)
            self.bot.register_next_step_handler(msg, self.view_map_callouts, navigation=navigation)
            return
        name = message.text.upper()
        if name == self.cancel_cmd.upper():
            self.cancel_handler(message)
            return
        if navigation == "map pick":
            output = "Which map?"
            markup = self.create_markup(buttons=self.b_all_maps, cancel_cmd=True)
            msg = self.bot.reply_to(message=message, text=output, reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.view_map_callouts, navigation="send map")
        elif navigation == "send map":
            pic_path = f"files/maps/{name}"
            if path.exists(pic_path):
                # send all related pics
                for root, dirs, files in walk(pic_path):
                    for file in files:
                        if file.endswith('png'):
                            pic_name = f"{pic_path}/{file}"
                            with open(pic_name, 'rb') as pic:
                                self.bot.send_photo(message.chat.id, pic)
                self.main_menu(message=message, text="Here you go")
            else:
                self.main_menu(message=message, text=f"Sorry, no schematics for {name} yet")
                logger.warning(f"No schematics found for {name}")

    def quiz(self, message, navigation, total_questions=None):
        """Send {total_questions} quiz messages with X answer options. Reply to each answer"""
        name = message.text
        typ = message.content_type
        if typ != 'text':
            output = "let's stick to buttons, ok?"
            msg = self.bot.reply_to(message=message, text=output)
            self.bot.register_next_step_handler(msg, self.quiz, navigation=navigation)
            return
        if name == self.cancel_cmd:
            self.cancel_handler(message)
            return
        if navigation == 'map pick':  # just got here
            output = "Choose a map or play with every map pull"
            quiz_buttons = list(self.b_all_maps)
            quiz_buttons.insert(0, self.all_maps_val)
            markup = self.create_markup(buttons=quiz_buttons, cancel_cmd=True)
            msg = self.bot.reply_to(message=message, text=output, reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.quiz, navigation='start polling')
        elif navigation == 'start polling':  # map picked
            try:
                _ = self.quiz_separate_data[name]
            except KeyError:
                output = f"huh, I cannot find {name} map. Weird, right?\nAnyway, let's try again."
                logger.warning(f"No map schematics for {name}")
                quiz_buttons = list(self.b_all_maps)
                quiz_buttons.insert(0, self.all_maps_val)
                markup = self.create_markup(buttons=quiz_buttons, cancel_cmd=True)
                msg = self.bot.reply_to(message=message, text=output, reply_markup=markup)
                self.bot.register_next_step_handler(msg, self.quiz, navigation='start polling')
                return
            if not total_questions:
                total_questions = self.quiz_questions_amount
            quiz_questions = self.create_list_of_quiz_questions(quiz_length=total_questions, map_name=name,
                                                                total_options=self.quiz_options_amount)
            self.quiz_polling(message=message, map_name=name, quiz_questions=quiz_questions)
        else:
            self.main_menu(message=message, text="ugh... I'm a bit lost. Let's start again")

    def quiz_polling(self, message, map_name, quiz_questions):
        """Poll all the quiz questions"""
        name = message.text
        typ = message.content_type
        if typ != 'text':
            output = "let's stick to buttons, ok?"
            msg = self.bot.reply_to(message=message, text=output)
            self.bot.register_next_step_handler(msg, self.view_map_callouts)
            return
        if name == self.cancel_cmd:
            self.cancel_handler(message)
            return
        if quiz_questions:
            self.check_answer(message=message, navigation='ask', quiz_questions=quiz_questions, map_name=map_name)
        else:
            output = "Once more?"
            self.main_menu(message=message, text=output)

    def check_answer(self, message, navigation, quiz_questions, map_name, correct_answer=None):
        name = message.text
        typ = message.content_type
        if typ != 'text':
            output = "let's stick to buttons, ok?"
            msg = self.bot.reply_to(message=message, text=output)
            self.bot.register_next_step_handler(msg, self.check_answer, navigation=navigation,
                                                quiz_questions=quiz_questions, map_name=map_name,
                                                correct_answer=correct_answer)
            return
        if name == self.cancel_cmd:
            self.cancel_handler(message)
            return
        if navigation == 'ask':
            output = "so, what's the callout?"
            q = quiz_questions[0]
            correct_answer = q[0]  # always first option
            random.shuffle(q)
            markup = self.create_markup(buttons=q, cancel_cmd=True)
            pic_name = self.quiz_separate_data[map_name][correct_answer]
            try:
                if map_name == self.all_maps_val:
                    with open(f"files/quiz/{pic_name}", 'rb') as pic:
                        self.bot.send_photo(message.chat.id, pic)
                else:
                    with open(f"files/quiz/{map_name}/{pic_name}", 'rb') as pic:
                        self.bot.send_photo(message.chat.id, pic)
            except FileNotFoundError:
                output = f"huh... I couldn't find proper picture for files/quiz/{map_name}/{pic_name}"
                logger.warning(f"No quiz picture for files/quiz/{map_name}/{pic_name}")
            msg = self.bot.send_message(message.chat.id, text=output, reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.check_answer, navigation='check', quiz_questions=quiz_questions,
                                                map_name=map_name, correct_answer=correct_answer)
        elif navigation == 'check':
            if name == correct_answer:  # correct
                output = "Good job!"
            else:  # incorrect answer
                output = f"Nope! It's called *{correct_answer}*"
            self.bot.send_message(message.chat.id, text=output, parse_mode="Markdown")
            # continue polling
            self.quiz_polling(message=message, map_name=map_name, quiz_questions=quiz_questions[1:])

    def create_list_of_quiz_questions(self, quiz_length, map_name,  total_options):
        all_questions = []
        chosen_options = []  # quiz options already picked up by random
        true_quiz_length = min(quiz_length, len(self.quiz_separate_data[map_name].items()))
        for _ in range(true_quiz_length):
            # get random option
            try:
                correct_answer = random.choice(
                    [i for i in self.quiz_separate_data[map_name].keys() if i not in chosen_options])
            except IndexError:
                return all_questions
            if correct_answer:
                quiz_options = [i for i in self.quiz_separate_data[map_name].keys() if i != correct_answer]
                true_total_options = min(total_options, len(quiz_options))
                quiz_options = random.sample(quiz_options, true_total_options)
                # correct answer is always the first element
                quiz_options.insert(0, correct_answer)
                chosen_options.append(correct_answer)
                all_questions.append(quiz_options)
            else:
                pass
        return all_questions

    def send_help_response(self, message):
        """ /help command processor. Basically just lists all available commands for user"""
        self.main_menu(message=message, text="I'll just send you back to main menu for easy navigation")

    def send_disclaimer(self, message):
        """output predefined disclaimer text to user"""
        output = "This is a small bot to practise your callouts Rainbow Six Siege maps.\n" \
                 "I understand that many sites have different names that might even contradict each other," \
                 " however I tried to stick to the most popular and widely accepted callouts.\nAs far as I know, " \
                 "KiXSTAr is working on the universal callout guide so when it's released.\nI'm planning on" \
                 " refreshing schematics and quizzes.\nIf you're felling that a quiz question has incorrect answer, " \
                 "or have any suggestions on improving the bot's behavior, feel free to /contact the developer. " \
                 "Some parts of the bot are still work in progress, so you could encounter placeholders.\n" \
                 "Map schematics credits to:\nu/The_Vicious\nhttp://www.r6maps.com/\nhttps://r6guides.com/maps"
        self.main_menu(message=message, text=output)

    def send_sticker(self, message, st_id=None):
        if st_id:
            sticker_id = st_id
        else:
            sticker_id = random.choice(self.main_sticker_pull)
        self.bot.send_sticker(message.chat.id, sticker_id)

    def contact_dev(self, message, incoming_message=None):  # TODO well, implement that
        """forward messages to @author"""
        name = message.text
        typ = message.content_type
        if typ not in ('text', 'pic'):
            output = "let's stick to text and pictures, ok?"
            msg = self.bot.reply_to(message=message, text=output)
            self.bot.register_next_step_handler(msg, self.contact_dev, incoming_message="placeholder")  # need to put something proper here
            return
        if name == self.cancel_cmd:
            self.cancel_handler(message)
            return
        if not incoming_message:
            output = f"Ok, tell me what's on your mind. You can send multiple messages, including pictures " \
                     f"(please keep it civil)!\nPress {self.confirm_cmd} when you're ready to send your message, or" \
                     f"{self.cancel_cmd} if you changed your mind"
            markup = self.create_markup(buttons=[self.confirm_cmd, self.cancel_cmd])
            msg = self.bot.send_message(message.chat.id, text=output, reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.contact_dev, incoming_message="Message start\n")
        else:
            # TODO separate picture and text processing
            incoming_message += name
            output = "You can send more messages or pictures if you need"
            markup = self.create_markup(buttons=[self.confirm_cmd, self.cancel_cmd])
            msg = self.bot.send_message(message.chat.id, text=output, reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.contact_dev, incoming_message=incoming_message)

    def cancel_handler(self, message):
        self.main_menu(message, "Ok")

    def start_bot(self):
        self.bot.infinity_polling()


logger.info("start the bot!")
c_bot = R6CalloutsBot()
c_bot.start_bot()
