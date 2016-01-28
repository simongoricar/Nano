import os

#try:
#    file = open("save_pid.txt","r")
#    if len(str(file).replace('\n', '')) != 0:
#        pid = str(file).replace("\n","")
#        os.system(str("kill ",pid))
#except FileNotFoundError:
#    pass
#    print("save_pid.txt not found, continuing")
print("Starting...")
os.system("python ayybot.py")