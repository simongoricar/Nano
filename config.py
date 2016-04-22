__author__ = "DefaltSimon"

# Variable file for AyyBot

customcmd = {
    "+johncena": "O_O https://www.youtube.com/watch?v=58mah_0Y8TU",
    "+allstar": "https://www.youtube.com/watch?v=L_jWHffIx5E",
    "+ayylmao" : "Ayy lmao! ( ͡° ͜ʖ ͡°) 👾 ",
    "+ayy": "Ayyyyy lmao!",
    "+wot": "<@{usr}> U wot m8?",
    "+synagoge": "DIE ALTEE-SYNAGOGE",
    "+thecakeisalie": "<@{usr}> : Rick roll'd https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "+butwait" : "*But wait, there's more!*",
    "+ping": "Pong!"
}

# Adding commands:
#
# Just add them with the help of a template:
#
# "<yourtriggercommand>": "<whatYouWantToPrint>",
#                                               ^ everywhere except the last line
#
# <whatYouWantToPrint> can include <@{usr}> to mention the author.
# Use \n anywhere for new line in the same message.
#
# OR JUST SIMPLY USE !cmd add <name> <content> while the bot is running
#

conversation = {
    "are you real":"you think?",
    "die":"nope.avi",
    "do you want to build a snowman":"Come on lets go and play!",
    "hi":"hi",
    "hello":":wave:",
    "stop":"Nein, nein, nein."}

# Words that should / will be filtered
filterwords = [
    "beeyotch","biatch","bitch","chink","crip","cunt","dago","daygo","dego","dick","dyke","fag","fatass","fatso","gash",
    "gimp","golliwog","gook","homo","hooker","kike","kraut","lame","lesbo","negro","nigga","nigger","pussy","retard",
    "skank","slut","spade","spic","spook","tard","tits","titt","tranny","twat","wetback","whore","wop","jebi se",
    "fuck off","dickhead"]

eightball = [
    "It is certain","It is surely so","Without a doubt","You may rely on it","Most likely","Yes",
    "Ask again later","Cannot predict now","Concentrate and ask again","I would say yes","JUST DO IT",
    "My reply is no","My sources say no","Signs point to yes"]

helpmsg1 = ("""\
+help useful - displays available commands
+help fun - funny commands
+help admin - admin commands
+help meme - meme commands
+help all - send all the commands to you via private message
+hello <mention>(optional) - greets you or whoever was mentioned
+wiki/+define <term> - returns a summary of a term from Wikipedia
+urban <term> - returns a summary of a term from Urban dictionary
+avatar <mention>(optional) - posts a link of your of mentioned person's avatar
+games - Makes use of the new game time module and tells you what game you have played and how much
+uptime - time since start
+credits - because the bot didn't make himself :)
""")

adminmsg = ("""\
+ping - checks if the bot is working +kick <mention> - kicks the person
+ban <mention> - bans the person
+unban <mention> - unbans the person
+vote start <name>++<option1>""<option2>""... (up to 5 choices, will be updated) - starts a public vote
+vote end - ends an ongoing vote and displays the results
+playing <status> - changes the status message
+members - lists all members on the server (WARNING: do not use on big servers, the list will be too long!)
+role add/remove/replacewith <rolename> <mention> - does things with roles
+cmd add <trigger> <response> - adds custom commands
+cmd remove <trigger> - removes the command
+cmd list - returns a list of all custom commands

ayybot.sleep/wake - hibernates/wakes the bot
ayybot.whitelist/config.reload - reloads whitelist or config
ayybot.server.setup - generates a server file
ayybot.settings <keyword> <var> - manages server settings
ayybot.blacklistchannel <channel> - blacklists a channel
ayybot.displaysettings - displays current server settings
ayybot.admins add/remove <mention> - adds/removes a person from server admins (meaning that they can use admin commands)
ayybot.admins list - lists current admins
ayybot.invitelink - sends you an OAuth2 link to invite the bot to your server (must be the owner)
ayybot.leaveserver - leaves the current server
""")
infomsg = ("""\
**AyyBot {}**
By: DefaltSimon
api: discord.py
Full commands list can be found at https://github.com/DefaltSimon/AyyBot/wiki/Commands-list
""")

jokemsg = ("""\
+roll <number> - rolls a number from 0 to
+dice - just like roll, but 1 to 6
+decide <word1> <word2> - decides between multiple words
+8ball <question> - "answers" your question in an 8ball-way.
+gif <tag> - sends a random gif with a matching from Giphy +quote - returns a random quote to help you lighten up your day :P
""")

memelist = ("""\
+cats - cuz cats are cute
+ayy - ayy lmao
+ayy lmao - even more ayy lmao
+wot - you what?
+thecakeisalie - is it really?
+allstar - just something
+johncena - da original John Cena meme
+butwait - But wait!. There's more.
""")

quotes = [
    "You miss 100% of the shots you don’t take. –Wayne Gretzky",
    "The most difficult thing is the decision to act, the rest is merely tenacity. –Amelia Earhart",
    "Twenty years from now you will be more disappointed by the things that you didn’t do than by the ones you did do, so throw off the bowlines, sail away from safe harbor, catch the trade winds in your sails.  Explore, Dream, Discover. –Mark Twain",
    "Life is 10% what happens to me and 90% of how I react to it. –Charles Swindoll",
    "Eighty percent of success is showing up. –Woody Allen",
    "The best time to plant a tree was 20 years ago. The second best time is now. –Chinese Proverb",
    "Winning isn’t everything, but wanting to win is. –Vince Lombardi",
    "I’ve learned that people will forget what you said, people will forget what you did, but people will never forget how you made them feel. –Maya Angelou",
    "The two most important days in your life are the day you are born and the day you find out why. –Mark Twain",
    "People often say that motivation doesn’t last. Well, neither does bathing.  That’s why we recommend it daily. –Zig Ziglar",
    "Everything you’ve ever wanted is on the other side of fear. –George Addair",
    "We can easily forgive a child who is afraid of the dark; the real tragedy of life is when men are afraid of the light. –Plato",
    "When I was 5 years old, my mother always told me that happiness was the key to life.  When I went to school, they asked me what I wanted to be when I grew up.  I wrote down ‘happy’.  They told me I didn’t understand the assignment, and I told them they didn’t understand life. –John Lennon",
    "When one door of happiness closes, another opens, but often we look so long at the closed door that we do not see the one that has been opened for us. –Helen Keller",
    "Life is not measured by the number of breaths we take, but by the moments that take our breath away. –Maya Angelou",
    "Too many of us are not living our dreams because we are living our fears. –Les Brown",
    "I didn’t fail the test. I just found 100 ways to do it wrong. –Benjamin Franklin",
    "A person who never made a mistake never tried anything new. – Albert Einstein",
    "A truly rich man is one whose children run into his arms when his hands are empty. –Unknown",
    "If you want your children to turn out well, spend twice as much time with them, and half as much money. –Abigail Van Buren",
    "It does not matter how slowly you go as long as you do not stop. –Confucius",
    "You can’t use up creativity.  The more you use, the more you have. –Maya Angelou",
    "Do what you can, where you are, with what you have. –Teddy Roosevelt",
    "You may be disappointed if you fail, but you are doomed if you don’t try. –Beverly Sills",
]