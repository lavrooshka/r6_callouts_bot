# Telegram & Discord bots to train your map calls in R6 siege
These are two bots with the same goal: help you improve your map calls in Rainbow Six Siege  

## Usage
### Telegram
Simply call @R6_callout_bot and follow chose on of the following buttons:
* view map callouts. Outputs schematics for available R6 maps. Some schematics are missing (either due to recent map rework or me being unhappy with quality for available maps)
* quiz. Bot will let you chose from one of the available maps or go for a random pull of callouts. Each quiz consists of 5 questions. No time limit 

any command can be stopped at any time with 
```
/cancel
```


### Discord
I'll add a list of servers running this bot. However you can always add bot to your server. Follow the installation guide.
You can start quiz with the following command 
````
!quiz BANK 10
````
which will queue 10 question for, you guess it, BANK map. Replace BANK with the map you want and 10 with any positive integer to queue for any other map.
Your can also go for
````
!quiz all 15
```` 
to get questions from all maps pool.

After quiz starts you'll have 6 options and 6 reactions for the question. React on the corresponding emoji you believe represents the correct answer.
Time limit is set to 10 second per question. 

Bot can be ran in two mods: Direct messages and Channel chats. A few differences between mods:
* DM mode will evaluate your answer
* Channel mode will just spit the answer after 10 seconds
* DM mode will output the next question right after you react to the previous, while in Channel everyone will have to wait until the timer is done

any running quiz can by stopped any time with
````
!stop
````
or
````
!cancel
````

## Installation

```
git clone https://github.com/lavrooshka/r6_callouts_bot.git
cd r6_callouts_bot
pip install -r requirements.txt
# set your bot token in discord_r6_callouts_bot.py for self.TOKEN var 
python discord_r6_callouts_bot.py
```


### todo
- [ ] add map schematic output to discord bot
- [ ] add answer evaluation to the channel mode for discord bot (not sure about that one)
- [x] allow user to modify timer for quiz questions for discord bot
- [ ] add unique users and quiz runs count



## credits
I *borrowed* some map schematics from reddit post by u/The_Vicious
and from lovely resources 
* http://www.r6maps.com/
* https://r6guides.com/maps 
