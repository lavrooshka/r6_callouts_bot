import discord
import json
import random
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from discord.ext import commands


"""Discord bot to learn Rainbow Six Siege maps callouts"""

__author__ = "Sergei Vorobev <s.vorobev101@gmail.com>"
__version__ = "0.2"

# logging config
log_file = "files/log/discord_callouts_bot.log"
max_log_file_size = 10  # max log file size in MB
max_log_files = 5
logger = logging.getLogger('discord_r6_callouts')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s -  %(levelname)s - %(message)s', datefmt='%d.%m.%Y %H:%M:%S')
handler = logging.handlers.RotatingFileHandler(log_file, mode='a', maxBytes=max_log_file_size*1024*1024,
                                               backupCount=max_log_files, encoding='utf-8', delay=False)
handler.setFormatter(formatter)
logger.addHandler(handler)


class R6Callouts:
    def __init__(self):
        self.TOKEN = "your token"
        self.bot_cmd_prefix = "!"
        self.quiz_file = "files/quiz.txt"
        try:
            with open(self.quiz_file, "r") as of:
                self.quiz_separate_data = json.load(of)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.quiz_separate_data = {}
        self.bot = commands.Bot(command_prefix=self.bot_cmd_prefix)
        self.active_quizzes = {}
        self.emoji_dict = {0: "\U00000030\U000020E3",
                           1: "\U00000031\U000020E3",
                           2: "\U00000032\U000020E3",
                           3: "\U00000033\U000020E3",
                           4: "\U00000034\U000020E3",
                           5: "\U00000035\U000020E3",
                           6: "\U00000036\U000020E3",
                           7: "\U00000037\U000020E3",
                           8: "\U00000038\U000020E3",
                           9: "\U00000039\U000020E3"
                           }
        self.emoji_dict.setdefault("cross", "\U0000274C")
        self.b_all_maps = None
        self.all_maps_val = "all maps!"
        self.quiz_question_timer = 10
        self.quiz_start_timer = 3
        self.default_quiz_question_amount = 5
        self.max_quiz_timer = 30
        try:
            with open(self.quiz_file, "r") as of:
                self.quiz_separate_data = json.load(of)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.quiz_separate_data = {}
        self.read_cfg()
        self.bot_name = "r6_callouts_bot"

        @self.bot.command(name="maps")
        async def map_quiz(ctx):
            """List maps, available for quiz"""
            embed = discord.Embed(title="R6 callouts quiz")
            nm = "The following maps are available now"
            val = "\n".join(list(self.b_all_maps)[:-1])
            embed.add_field(name=nm, value=val)
            await ctx.send(embed=embed)

        @self.bot.command(name="stop")  # todo there's probably a better way to handle separate commands in the same way
        async def stop_quiz(ctx):
            """Cancel currently running quiz. Alias: cancel"""
            await self.cancel_processor(ctx)

        @self.bot.command(name="cancel")
        async def cancel_quiz(ctx):
            """Cancel currently running quiz. Alias: stop"""
            await self.cancel_processor(ctx)

        @self.bot.command(name="quiz")
        async def start_quiz_polling(ctx):
            """Try naming all spots on R6 maps. Use '!help quiz' for detailed info
            Usage: '!quiz KAFE 7'. You can pick any map from '!maps' pool
            or go for a random set of questions using 'all' instead of map name.
            To answer a question just react on the emoji number you believe is correct.
            You'll have 10 seconds to answer each question, or if you pass the 3rd parameter
            you can set your own timer. E.g. '!quiz KANAL 10 5'
            will start the quiz on KANAL for 10 questions and 5 second window to answer"""
            # Quiz polling only allowed in DM and text channels
            message_channel = ctx.channel
            if isinstance(message_channel, discord.channel.TextChannel):
                chat_type = "channel"
            elif isinstance(message_channel, discord.channel.DMChannel):
                chat_type = "DM"
            else:
                await ctx.send("Sorry, this command only supported in text channels and DMs")
                return
            message_split = ctx.message.content.split()
            map_name = self.list_get(message_split, 1, None)
            amount_of_questions = self.list_get(message_split, 2, None)
            quiz_timer = self.list_get(message_split, 3, None)
            if not map_name:
                await ctx.send(f"Not like this.\nThe bot has 2 parameters: map name (check out !maps command) "
                               f"and the amount of questions in the quiz.\nExample: '!quiz BANK 5'")
                return
            # a bit more civil way to start quiz for the whole map pool
            elif map_name.upper() in ("RANDOM", "ALL", "ANY", "RND", "EVERYTHING"):
                map_name = self.all_maps_val
            elif map_name.upper() not in self.b_all_maps:
                await ctx.send(f"Sorry, I don't know {map_name}.\n!maps command will list all the available quizzes")
                return
            else:
                map_name = map_name.upper()
            if not amount_of_questions:  # let user know, they can use
                await ctx.send(f"By the way, you can also add 2nd parameter: the amount of questions in a quiz. "
                               f"e.g. '!quiz BANK 10'.\nFor now we'll start with {self.default_quiz_question_amount} "
                               f"questions")
                amount_of_questions = self.default_quiz_question_amount
            if self.is_positive_integer(amount_of_questions):
                amount_of_questions = int(amount_of_questions)
            else:
                await ctx.send(f"Kudos for exploratory testing, but no, the 2nd parameter should be"
                               f"a positive integer\nWe'll start with {self.default_quiz_question_amount} questions")
                amount_of_questions = self.default_quiz_question_amount
            if self.is_positive_integer(quiz_timer):
                quiz_timer = min(int(quiz_timer), self.max_quiz_timer)  # limit max question time
            else:
                quiz_timer = self.quiz_question_timer
            # check if quiz is already running in this channel
            chat_id = message_channel.id
            if not self.active_quizzes.get(chat_id, False):
                self.active_quizzes[chat_id] = True
            else:
                await ctx.send(f"{ctx.message.author.mention} chill! We already have a quiz running")
                logger.info(f"{chat_id} attempted multiple instance of quiz! shame!")
                return
            quiz_questions = self.create_list_of_quiz_questions(amount_of_questions, map_name, 5)
            embed = discord.Embed(title="Starting quiz!", color=0x00ff00)
            av = f"You're playing on {map_name}"
            res = f" You'll have to answer {len(quiz_questions)} questions within {quiz_timer} seconds " \
                f"timer window.\n Quiz starts in {self.quiz_start_timer} seconds.\nGood luck!"
            embed.add_field(name=av, value=res, inline=False)
            await ctx.send(embed=embed)
            end_output = "Once more?"
            await asyncio.sleep(self.quiz_start_timer)
            logger.info(f"{chat_id} started quiz on {map_name} for {amount_of_questions} questions")
            for i, question in enumerate(quiz_questions):
                # check if user cancels the quiz
                if self.active_quizzes[chat_id] == "cancel":
                    end_output = "Quiz stopped.\n~~The mission, the nightmares... they're finally... over~~"
                    break
                await self.quiz_polling(ctx=ctx, map_name=map_name, quiz_question=question,
                                        question_number=(i + 1, len(quiz_questions)), chat_id=chat_id,
                                        chat_type=chat_type, quiz_timer=quiz_timer)
            self.active_quizzes[chat_id] = False  # exclude from active quizzes
            await ctx.send(end_output)

    def read_cfg(self):
        """read all main self.* variables outside of __init__ to be able to re-read config after it was changed
        without restarting the bot."""
        self.b_all_maps = self.quiz_separate_data.keys()
        maps_buffer = {}
        for key, val in self.quiz_separate_data.items():
            for k, v in val.items():
                maps_buffer[k] = f"{key}/{v}"
        self.quiz_separate_data[self.all_maps_val] = maps_buffer

    async def cancel_processor(self, ctx):
        """raises cancel flag that stops current quiz for user or channel"""
        message_channel = ctx.channel
        chat_id = ctx.channel.id
        if type(message_channel) in (discord.channel.TextChannel, discord.channel.DMChannel):
            if not self.active_quizzes.get(chat_id, False):
                output = "Quiz isn't running here"
            elif self.active_quizzes.get(chat_id, None) == "cancel":  # already called for stop
                output = f"{ctx.message.author.mention} yeah, this quiz is being stopped now. It'll be over soon"
            else:
                self.active_quizzes[chat_id] = "cancel"
                output = "Ok, stopping the quiz..."
                logger.info(f"{chat_id} cancelled their quiz")
        else:
            output = "Sorry, this command only supported in text channels and DMs"
        await ctx.send(output)

    def create_list_of_quiz_questions(self, quiz_length, map_name, total_options):
        """composes list of quiz question options. First element is always the correct answer. The're total 1 +
        self.quiz_options_amount options for each question and total of self.quiz_questions_amount questions per quiz.
        Each quiz run each question is randomized from the quiz pull (for any chosen map all for all supported maps"""
        all_questions = []
        chosen_options = []
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

    async def quiz_polling(self, ctx, map_name, quiz_question, question_number, chat_id, chat_type, quiz_timer):
        """poll quiz for a DM chat or channel"""
        output = f"Question # {question_number[0]}/{question_number[1]}."
        correct_answer = quiz_question[0]  # always first option
        random.shuffle(quiz_question)
        pic_name = self.quiz_separate_data[map_name][correct_answer]
        try:
            if map_name == self.all_maps_val:
                with open(f"files/quiz/{pic_name}", 'rb') as pic:
                    quiz_pic = discord.File(pic)
            else:
                with open(f"files/quiz/{map_name}/{pic_name}", 'rb') as pic:
                    quiz_pic = discord.File(pic)
        except FileNotFoundError:
            logger.warning(f"Picture missing for files/quiz/{map_name}/{pic_name}")
            output = f"huh... I couldn't find proper picture for files/quiz/{map_name}/{pic_name}"
            with open("files/misc/not_found.png", "rb") as pic:
                quiz_pic = discord.File(pic)
        emoji_options = self.num_to_emoji(range(1, len(quiz_question) + 1))
        output += "\n"*2
        pretty_options = dict(zip(emoji_options, quiz_question))
        pretty_options = [f" {emoji}   {opt}" for emoji, opt in pretty_options.items()]
        output += "\n".join(pretty_options)
        msg = await ctx.send(content=output, file=quiz_pic)
        for option in emoji_options:
            await msg.add_reaction(option)
        # no need to check for correct answer in channel call. Just spit out the answer after wait time.
        # this basically makes reaction reading mechanic less efficient since there will be no user input evaluation
        # but this should be fine for group chats
        if chat_type == "channel":
            await asyncio.sleep(quiz_timer)
            await ctx.send(f"It was # {quiz_question.index(correct_answer) + 1}: {correct_answer}")
            return
        # proceed with DMs and reaction evaluation
        await self.wait_for_reaction(ctx, msg.id, chat_id, quiz_timer)
        if self.active_quizzes.get(chat_id, None) == "cancel":  # don't show correct answer if quiz was cancelled
            return
        msg_after = await ctx.fetch_message(msg.id)
        reactions = []
        for reaction in msg_after.reactions:
            reactions.append(reaction.count - 1)
        if reactions.count(1) > 1:
            await ctx.send("No-no, just 1 answer allowed!")
            return
        elif reactions.count(1) == 0:
            await ctx.send(f"Time's out!\nIt was # {quiz_question.index(correct_answer) + 1}: {correct_answer}")
            return
        chosen_answer = reactions.index(1)
        if quiz_question[chosen_answer] == correct_answer:
            await ctx.send("Good job!")
        else:
            await ctx.send(f"Nope, sorry, not {quiz_question[chosen_answer]}. It's actually {correct_answer}")

    async def wait_for_reaction(self, ctx, message_id, user_id, wait_time):
        """a primitive way to speed up quiz so user won't have to wait 10 seconds after each question"""
        for _ in range(1, wait_time + 1):
            await asyncio.sleep(1)
            msg_later = await ctx.fetch_message(message_id)
            if any(reaction.count == 2 for reaction in msg_later.reactions) or \
                    self.active_quizzes.get(user_id, None) == "cancel":
                break

    def num_to_emoji(self, iterator):
        """converts numbers into emoji representation"""
        emoji_numbers = []
        for entry in iterator:
            if isinstance(entry, int):
                emoji_number = ""
                for digit in str(entry):
                    emoji_number += self.emoji_dict.get(int(digit))
                emoji_numbers.append(emoji_number)
            else:
                logger.warning(f"{entry} doesn't look like a number with that pesky {type(entry)} type")
        return emoji_numbers

    @staticmethod
    def is_positive_integer(val=0):
        """quick check if passed value is a positive integer for whenever we need to check for quiz amount, timer and
        other parameters."""
        try:
            val = int(val)  # cut floats. It's fine
            if val > 0:
                return True
            else:
                return False
        except (ValueError, TypeError):
            return False

    @staticmethod
    def reaction_reader(reactions, allow_multiple=False, allow_none=False):
        """parses message reactions and runs basic checks"""
        if reactions.count(1) > 1 and not allow_multiple:
            multiple_answers = True
        else:
            multiple_answers = False
        if reactions.count(1) == 0 and not allow_none:
            no_answer = True
        else:
            no_answer = False
        return multiple_answers, no_answer

    @staticmethod
    def list_get(list_in, index, default):
        """a version of .get() method for lists"""
        try:
            return list_in[index]
        except IndexError:
            return default

    def run_bot(self):
        self.bot.run(self.TOKEN)


logger.info("Start the bot!")
bot = R6Callouts()
bot.run_bot()

