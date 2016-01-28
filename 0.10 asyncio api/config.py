useful = {
    "!ping": "Pong!"
}
meme = {
    "!johncena": "O_O https://www.youtube.com/watch?v=58mah_0Y8TU",
    "!allstar": "https://www.youtube.com/watch?v=L_jWHffIx5E",
    "!ayylmao" : "Ayy lmao! ( ͡° ͜ʖ ͡°) 👾 ",
    "!ayy": "Ayyyyy lmao!",
    "!wot": "<@{usr}> U wot m8?",
    "!synagoge": "DIE ALTEE-SYNAGOGE",
    "!thecakeisalie": "<@{usr}> : Rick roll'd https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "!butwait" : "*But wait, there's more!*"
}

#
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

filterwords = [
    "beeyotch","biatch","bitch","chink","crip","cunt","dago","daygo","dego","dick","dyke","fag","fatass","fatso","gash",
    "gimp","golliwog","gook","homo","hooker","kike","kraut","lame","lesbo","negro","nigga","nigger","pussy","retard",
    "skank","slut","spade","spic","spook","tard","tits","titt","tranny","twat","wetback","whore","wop","jebi se",
    "fuck off",""]

eightball = [
    "It is certain","It is surely so","Without a doubt","You may rely on it","Most likely","Yes",
    "Ask again later","Cannot predict now","Concentrate and ask again","I would say yes","JUST DO IT",
    "My reply is no","My sources say no","Signs point to yes"]

helpmsg1 = ("""\
!help useful - displays available commands
!help fun - funny commands
!hello - says hi
!listmembers - displays all members on the server
!uptime - displays bot uptime
!avatar ""@<usr>"" returns a link to mentioned person's avatar or yours if there is no mention
!user @mention - returns info about the user
!role mod/removemod/members @mentions - modifies roles
ayybot.sleep/wake - self explanatory, isn't it?
ayybot.kill - stops the bot
!cmd add <trigger> <response>
!cmd list
!cmd remove !<name>
!credits - author, etc.
""")

creditsmsg = ("""\
**DiscordBot {__version__}**
Made by *DefaltSimon* with discord.py API
""")

jokemsg = ("""\
!gif <name> - returns a gif from Giphy
!roll <number> - random number
!dice - like !roll but 0 - 6
!decide word word - decides between two words
!quote - returns a random quote
""")

memelist = ("""\
!ayy - ayy lmao
!ayylmao - even more ayy lmao with lenny face
!wot - u wot m8
!allstar just try it ( ͡° ͜ʖ ͡°)
!johncena dis too ( ͡° ͜ʖ ͡°)
!thecakeisalie - want it?
!kappa - kappa
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
