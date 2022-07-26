#! /usr/bin/env python3

# This tool will test if a node has forked
# It compares the headers of the former last block of your own node
# and of other nodes.
# The list of nodes are nodes you trust

import json
import urllib3
import pprint
import time
import datetime
import collections
import os
import glob
import urllib.request as http
import urllib.error
import sys

configfile = "forkconfig.json"
https = urllib3.PoolManager()
pp = pprint.pprint
gettimeout = 2.0 #Waiting time before declare unsuccesfull GET
getpause = 1.0 #0.5 seconds timeout between succesfull GET
startblock = 0 #Former lastblock of blockchain (first validation block)
lastblockshift = 2 #The startblock will become the last block minus this value
rollbackheight = -1 #block which will be rolled back to if fork happened
oosync = False #Detected out of sync (blockheights diff)
fork = False #Detected fork (found block header diff)
forkcounter = 0 #How many nodes differ from my node
rollback_uri = "/debug/rollback" #uri to activate rollback
option_help = [ 'help', 'h', '/h', '?' ]
option_block = "block"
option_rollback = "rollback"
progname = "Forktester"

# read and set variables from config file
with open(configfile, "r") as json_file:

    jsonconfigdata = json.load(json_file)
    ftconf = jsonconfigdata["forktoolsconfig"]
    tgconf = jsonconfigdata["telegramconfig"]
    pconf = jsonconfigdata["thenode"]
    cn = ftconf["controlnodes"]
    auto_rollback = ftconf['auto_rollback']
    mynode = jsonconfigdata["thenode"]["node_api"]
    max_blocks = ftconf['rollback_blocks']
    lastblock_uri = ftconf["lastblockheight"]
    blockheaders_uri = ftconf["blockheaders"]
    tg = tgconf['use']
    tg_token = tgconf['telegram_token']
    tg_chatid = tgconf['telegram_chat_id']
    tg_baseuri = tgconf['telegram_api']
    APIkey = pconf["node_apikey"]
    nodename = pconf['nodename']


# Function to test what options used atr script start
# options:
# - help
# - block <block> : start forktester at specified block (default is current)
# - rollback <block> : rollback to specified block
def check_start_mode():

    global startblock
    global rollbackheight

    a0 = sys.argv[0] #Script name
    cmd_argvs = len(sys.argv) #length of command line arguments (script itself also counted as 1)

    if cmd_argvs == 2: #Entered 1 command line option

        a1 = sys.argv[1].strip('-').lower()

        if a1 in option_help: #Help requested

            print()
            print(" " + progname + " - A tool that detects blockchain deviatens and forks for waves nodes\n")
            print(" usage: " + a0 + " <command options>\n")
            print(" " + a0 + " started without options, collects 5 blocks and compares between")
            print(" your node and the control nodes. It reports if your node forked and which blocks")
            print(" deviated. Default it calls current blockheight and start at height -" + str(lastblockshift) + "\n")
            print(" command options:")
            print(" help              : Show the help screen")
            print(" block    [height] : Start testing from a specific block. Default it starts from lastblock -" + str(lastblockshift))
            print(" rollback [height] : Activate rollback to specified blockheight. You need the node API key for rollback\n")
            print(" forkconfig.json options:\n")
            print(' "thenode"      :')
            print('     "node_api"  : Set your node and API port here, default "http://localhost:6869"')
            print()
            print(' "forktoolsconfig"    :')
            print('     "controlnodes"   : Control nodes to use, default "https://nodes.wavesplatform.com:443" : "up"')
            print('                        Specify multiple nodes as follows  { "http://10.1.2.3:6869"  : "up/down",')
            print('                                                             "https://10.5.6.7:6443" : "up/down" }')
            print('                        If a node is specified as "down", it is not used for validation testing')
            print('    "auto_rollback"   : "yes/no", default "no", Rollback automatically if a fork is detected')
            print('    "lastblockheight" : uri to GET the lastblock height, default "/blocks/height"')
            print('    "blockheaders"    : uri to GET a specific blockheight, default "/blocks/headers/at/"')
            print('    "rollback_blocks" : Max blocks after fork in which rollback can occur, default "2000"')
            print('                        NOTE: Do not change this as it is determined by the node settings')
            print(' "telegramconfig"     :')
            print('    "use"             : "yes/no", default "no", Should telegram be used to send forktesting results')
            print('    "telegram_api"    : API url for the telegrambot, default "https://api.telegram.org/bot"')
            print('    "telegram_token"  : Your bot access token, i.e "551113448:HNyNJkiisS-7YUjkox-vvvvVVVBHJNJ"')
            print('    "telegram_chat_id": Your telegram chat-if, i.e. "123456789"')
            print('    "telegram_group"  : The telegram group where your messages will appear, i.e. "myforkmonitor"')
            print('    "telegram_botuser": "my_fork_bot", the name of telegram bot user')
            print()
            exit()


    if cmd_argvs > 2: #There at least 2 command line options entered

        a1 = sys.argv[1]
        a2 = sys.argv[2]

        if a1 == 'block': #Request forktesting on specific startblock

            startblock = int(a2) #Set global startblock and proceed

        elif a1 == 'rollback': #Request rollback to specific block

            rollbackheight = a2.strip('forked.')

            if rollbackheight.isnumeric() == False: #Error in block number specified
                print("\n Wrong syntax used for rollback block?")
                print(" Try : " + a0 + " rollback <nr>, i.e. 12345\n")
                exit()

            else: #Specified correct numeric block number for rollback
                currentblock = get_current_block(mynode)

                if (int(rollbackheight) + int(max_blocks)) > int(currentblock): #We are within the max blockrange for rollback
                    confirm = input(" Are you sure you want to rollback to block " + rollbackheight + " [y/n]? ")

                    if confirm.lower() not in [ 'y', 'yes' ]:
                        print('\n Rollback cancelled, exit now.\n')
                        exit()

                else: #Max blocks exceeded for rollback
                    print(" Max range of " + max_blocks + " blocks exceeded for rollback.")
                    print(" Exceeded by " + str(int(currentblock) - int(max_blocks) - int(rollbackheight)) + " blocks.")
                    print(" You need to Synchronize the Waves Blockchain completely.\n")
                    exit()


# Function that captures current data & time
# sample output : 02-01-2021 10:55:45
def currentdate():
    now = datetime.datetime.now()
    return now.strftime("%d-%m-%Y %H:%M:%S")

# Function that checks if a rollbackfile exists
# A rollbackfile is created if rollback is requested
def check_ongoing_rollback():

    for name in glob.glob('rollback.[0-9]*'): #Found rollback file, a rollback is currently active
        rollbackfile = name
        rollbackheight = name.strip("rollback.")
        print("\n Oops, rollback file detected  (" + name + ").")
        print(" The blockchain is undergoing a rollback to block " + str(rollbackheight) + ".")
        print(" When rollback has finished, the rollback file '" + str(rollbackfile) + "' will be deleted.")
        print(" If the file is stale then delete it manually.\n")

        tt = '\n Monitoring Alert!\n' +\
             ' -----------------\n' +\
             ' Found rollback file : ' + rollbackfile +\
             ' \nNode : ' + nodename +\
             ' \nRollback active or stale file left behind?\n'

        telegram_bot_sendtext(tt)

        exit()


# Function that checks if a forkfile has been created
# The forkfile reveals to which block we need to rollback
# If the script is started with rollback options, then
# the actual rollback is activated.
# If no forkfile is found, continue.
def check_forkfile(): #Check if forkfile already exists

    global rollbackheight

    name = ""
    need_rollback = False
    cmd_argvs = len(sys.argv) #length of command line arguments (script itself also counted as 1)
    ffcnt = 0 #Forkfile found counter

    if rollbackheight == -1: #No rollback requested on script start

        for name in glob.glob('forked.[0-9]*'): #Seek for forkfiles, pick lowest block to rollback
            if ffcnt == 0:
                forkfile = name
                need_rollback = True

            oldblock = int(forkfile.strip('forked.'))
            newblock = int(name.strip('forked.'))

            if newblock < oldblock: #Found older rollback block
                print(' File "' + forkfile + '" can be deleted. Forkfile "' + name + '" forked first.')
                forkfile = name #Set forkfile to lower block found
            elif newblock > oldblock: #Found newer rollback block
                print(' File "' + name + '" can be deleted. Forkfile "' + forkfile + '" forked first.')

            ffcnt += 1 #Increase forkfile counter

        if ffcnt != 0: #Found forkfiles

            rollbackheight = forkfile.strip("forked.") #Strip string and keep blocknr.
            rollbackfile = "rollback." + str(rollbackheight) #File created when rollback started
            rollbackfinished = "finished." + str(rollbackheight) #File created when rollback finished

            print('\n Found in total ' + str(ffcnt) + ' forkfiles. Selected ' + forkfile + ' as candidate.')

    else: #Rollback was set at script start, blockheight was already stripped to number

        forkfile = 'forked.' + rollbackheight
        rollbackfile = "rollback." + rollbackheight
        rollbackfinished = "finished." + rollbackheight

        if os.path.isfile(forkfile): #Forkfile found, this is correct
            need_rollback = True

        else: #Forkfile not found
            print("\n Forkfile '" + forkfile + "' not found.")
            confirm = input(" Are you sure you want to rollback to block " + rollbackheight + " [y/n]? ")
            if confirm.lower() in [ 'y', 'yes' ]:
                need_rollback = True
                f = open(forkfile,"w+") #Create forkfile
                f.close()

            else: print(" Exit.\n"), exit()

    if need_rollback == True: #The blockchain need to be rolled back before the fork happended (on block 'rollbackheight')

        if cmd_argvs > 2: #There are command line options entered, it is a request for rollback

            print("\n Rollback requested to blockheight " + rollbackheight + ".")

            tt = '\nMonitoring Alert!\n' +\
                 ' -----------------\n' +\
                 ' Rollback to block "' + str(rollbackheight) + '" requested.\n' +\
                 ' node : ' + nodename + '\n'

            telegram_bot_sendtext(tt)

            os.rename(forkfile, rollbackfile) #rename forkfile to rollback file
            rollback_call(mynode,rollbackheight) #Rollback blockchain
            os.rename(rollbackfile, rollbackfinished) #rename rollback file to finished file

            tt = '\nMonitoring Alert!\n' +\
                 ' -----------------\n' +\
                 ' Rollback to block "' + str(rollbackheight) + '" finished.\n' +\
                 ' node : ' + nodename + '\n'

            telegram_bot_sendtext(tt)

            print("\n Rollback finished!\n")

            for name in glob.glob('forked.[0-9]*'): #Found old forkfiles, remove
                print(' Found old forkfile, deleting : ' + name)
                os.remove(name)

            print(" All Done\n")

        else: #No rollback requested by user, but the forkfile was found, will send telegram msg and exit

            currentblock = json.loads(https.request('GET', mynode + lastblock_uri).data)["height"] #Blockheight last block
            blockselapsed = int(currentblock) - int(rollbackheight)
            blocksleft = int(max_blocks) + int(rollbackheight) - int(currentblock)
            hoursleft = round((blocksleft / 60), 2)

            print("\n The blockchain needs rollback to blockheight " + rollbackheight + ".")
            print(" After rollback, the forkfile '" + forkfile + "' needs to be deleted.")
            print("\n Forked at : " + time.ctime(os.path.getctime(forkfile)))

            telegram_text = '\nFORK WARNING!' +\
                        '\nNode : ' + nodename +\
                        '\n-----------------' +\
                        '\nRollback to block ' + str(rollbackheight) +\
                        '\nForktime: ' + time.ctime(os.path.getctime(forkfile)) +\
                        '\n\nRollback within ' + str(hoursleft) + ' hours!'

            telegram_bot_sendtext(telegram_text)

            print(" You can automate rollback with command : '" + sys.argv[0] + " rollback " + str(rollbackheight) + "'\n")
            print(" Exit now.\n")

        print(" ============================================================================")
        exit()


# Function that checks all current blocks blockheights
def get_current_block(node):

    getreq = https.request('GET', node + lastblock_uri) #Get current block (lastblock)

    return json.loads(getreq.data)["height"]


# Function that queries the node for the current blockheight
# If succesfull, the global var startblock will be set
# This will be -1, cause the lastblock will still change,
# until the new last block is created
# If unsuccesfull, alert with telegram message and exit
# params
# - node : the node to get the blocks from
def set_startblock(node):

    global startblock #Var usable at global level

    try:
        getreq = https.request('GET', node + lastblock_uri, timeout=gettimeout)
        status = getreq.status
        if status == 200: #Succesfull retrieval of data
            lastblock = json.loads(getreq.data)["height"] #Blockheight last block
            startblock = lastblock-lastblockshift #Start validation from here (last blocks can change)
        else: #Did not get succesfull https response
            print(' There were problems requesting the last block from ' + node + '.\n' +\
                  ' Terminated forktester.py. No fork testing done!')

            tt = '\nMonitoring Alert!\n' +\
                 '-----------------\n' +\
                 str(sys.argv[0]) + ' terminated!\n' +\
                 'Can not get lastblock from\n' +\
                 'node ' + node + '.\n' +\
                 'node : ' + nodename +\
                 '\n\nNo fork testing done!'

            telegram_bot_sendtext(tt)

            exit()
    except: #node reachability problems
        print("\n Rechability problems for my node '" + node + "'." +\
              "\n No Fork testing done!\n")

        tt = '\nMonitoring Alert!\n' +\
             '-----------------\n' +\
             str(sys.argv[0]) + ' terminated!\n' +\
             'My node "' + node + '" is unreachable!' +\
             '\nnode : ' + nodename +\
             '\n\nNo fork testing done!'

        telegram_bot_sendtext(tt)

        exit()


# Function that queries blocks and headers that will be validated
# The blocks will be added to an ordered dictionary list
# The dictionary list will be returned
# fault handling:
# If no data received from node, send alert message
# params
# - node : the node to GET the blocks from
def get_blocks(node):

    ordered_objdict = collections.OrderedDict()
    failcnt = 0 #Count failures to get blocks

    for blockheight in range(startblock, startblock-5, -1): #Take 5 blocks and query block headers
        print(" GET headers from verification block",blockheight)

        try:
            getreq = https.request('GET', node + blockheaders_uri + str(blockheight), timeout=gettimeout)
            status = getreq.status
            headers = json.loads(getreq.data)
            time.sleep(getpause) #Pause between GET requests, to relax the nodes
            ordered_objdict[blockheight] = headers #Add headers to block (block and headers ordered)
            #if node == mynode: ordered_objdict[startblock-10] = 'unique block' ####### TESTING : generates a unique block for my node
            #if node == mynode: ordered_objdict[startblock-3] = 'my node header' ####### TESTING : generates a unique header for my node
            #if node != mynode: ordered_objdict[startblock-8] = 'unique block' ####### TESTING : generates a unique block for all control node
            #if node != mynode: ordered_objdict[startblock-3] = 'ctrl node header' ####### TESTING : generates a unique header for all control node
            #if node == "https://nodes.wavesplatform.com:443" : ordered_objdict[startblock-4] = 'ctrl node header' ####### TESTING : generates a unique header for 1 control node

        except:
            print(" # Failure for block " + str(blockheight) + " #")
            failcnt += 1

    filename = progname + "." + node[node.find('//')+2:]

    if failcnt != 0: #Failures to get blocks

        filename = filename + ".down"

        if os.path.isfile(filename): #found node down file
            nodealreadydown = True
        else: #No nodedown file found, first time down
            nodealreadydown = False
            f = open(filename,"w+") #create file to secure reachability problems
            f.close()

        print("\n Warning!")
        print(" There were " + str(failcnt) + " failures to get block data from node '" + node + "'")
        print(" If this happens more often, consider not using this node anymore.")
        print(" Do this by removing it from the config or mark it as 'down'.")
        print("\n Alert message send to telegram.")

        tt = '\nMonitoring Alert!\n' +\
             '-----------------\n' +\
             str(sys.argv[0]) + ' problems.\n' +\
             'Node ' + str(node) + "\n" +\
             'reachability problems.\n' +\
             'Consider marking this node "down" in ' +\
             'forkconfig.json, if this is a control node.\n' +\
             'source node : ' + nodename + '\n'

        if nodealreadydown == False: #First time node discovered as down, send message
            telegram_bot_sendtext(tt)

    else: #No failures to get blocks from node

        filename = filename + ".down"
        if os.path.isfile(filename): #found old node unreachable file
            os.remove(filename)

            tt = '\nMonitoring Alert!\n' +\
                 '-----------------\n' +\
                 str(sys.argv[0]) + ' problems.\n' +\
                 'Node ' + str(node) + "\n" +\
                 'reachable again.\n' +\
                 'source node : ' + nodename + '\n'

            telegram_bot_sendtext(tt)

    return ordered_objdict


# Function that loops through all controlnodes and requests all validationblocks
# Use control node only if status is marked 'up' in config file
# The validation blocks are requested per node with function get_blocks().
# Only active nodes are added to the dict list cnblocks. The blocks and headers
# are added as ordered dict per node.
# Alert/send message if no active nodes found.
# params
# - nodearray : The list with all control nodes { "node1" : "up", "node2" : "up" ]
def get_controlnode_blocks(nodearray):

    cnblocks = {} #List with all ACTIVE control nodes and their ordered dict of blockheaders

    for node in nodearray: #cycle through all controlnodes
        nstatus = nodearray[node].lower()
        if nstatus == "up": #Use node to collect
            print("\n GET blocks from Control Node '" + node + "'")
            cnblocks[node] = get_blocks(node)
            if len(cnblocks[node]) == 0: #Control node problems, can be down, slow, firewalled
                cnblocks.pop(node) #Delete node from compare list
        else: print("\n Skipping control node '" + node + "', as it is not marked 'up' in config.")

    if len(cnblocks) == 0: #No active control nodes, alert and quit

        tt = '\nMonitoring Alert!\n' +\
             '-----------------\n' +\
             str(sys.argv[0]) + ' problems.\n' +\
             'node : ' + nodename + '\n'

        if len(cn) == 0: #No nodes in configfile added

            tt += 'Please add control nodes to forkconfig.json.\n'
            print('\n There are no controlnodes added to forkconfig.json. Can not compare.')

        else: #all nodes in config down

            tt += 'No control nodes usable.\n' +\
                  'All marked "down" in forkconfig.json.\n'

            print('\n Seems there are no usable control nodes. All marked down. Can not compare.')

        telegram_bot_sendtext(tt)
        exit()

    print()
    return cnblocks


# Function that compares first the blockchain heights
# Then compares the block headers
# params
# - mnkeys : Ordered dict of blocks/headers of my node
# - cnkeys : List of active controlnodes with ordered dict of blocks/headers
# - mnblocks : ordered dict with validation blocks and headers for mynode
def compare_keys_headers(mnkeys, cnkeys, mnblocks):

    global oosync
    global fork
    global forkcounter
    cncount = len(cnkeys) #How many control nodes do we use
    nodekeydiff = 0 #Counter to see if key sets differ for block heights

    for cn in cnkeys: #Loop through all active control node blocks, compare key set

        blockdiff = 0 #Counter to see if key sets differ for block headers
        cnk = set(cnkeys[cn].keys()) #Set of control node blockheights

        if cnk != mnkeys: #The blockheights deviate for this control node and my node -> OOSync

            oosync = True #Node could be out of sync
            cnkdiffcnt = len(cnk.difference(mnkeys)) #Unique blockheights of ctrl node
            mnkdiffcnt = len(mnkeys.difference(cnk)) #Unique blockheights of my node

            nodekeydiff += 1 #Number of nodes that deviate

            print("\n Warning! Found " + str(cnkdiffcnt+mnkdiffcnt) + " blockheight deviations between a control node and My node.")

            if cnkdiffcnt != 0: #Found blockheights unique to control node
                print(" - Blockheights unique to control node '" + cn + "' :  " + str(cnk.difference(mnkeys)))
                print("   These are not found in my node '" + mynode + "'")
            if mnkdiffcnt != 0: #Found blockheights unique to my node
                print(" - Blockheights unique to my node '" + mynode + "' :  " + str(mnkeys.difference(cnk)))
                print("   These are not found in control node '" + cn + "'")

        else: #Blockheights are in sync for this control node and my node, now check headers

            ck = cnk.intersection(mnkeys) #all common blockheights between a control node and my node

            print(" Compare block headers with control node '" + cn + "'")
            print(" Current active blockheight : " + str(get_current_block(cn)))
            for blockheight in ck: #For every common block, check if headers are equal for this control node and my node

                if cnkeys[cn][blockheight] == mnblocks[blockheight] : #Blockheader control node match blockheader my node
                    print(" Headers of Block",str(blockheight), "are equal. Block is valid.")

                else: #Blockheader control node does not match with my node -> someone forked
                    print(" Warning, Headers of block", str(blockheight), "are different. Block is invalid")

                    fork = True #Fork detected, not sure yet which node (my node or control node)
                    blockdiff += 1 #Increase counter for every deviated block, for this control node

            if blockdiff != 0:
                forkcounter += 1 #If headers deviate, a node has forked, increase global counter
                print("\n Warning, possible fork detected! Blocks deviated : " + str(blockdiff) + "\n --")

        print()

    if oosync == True: #Block numbers are not in sync

        tt = '\n Monitoring Alert!\n' +\
             '------------------\n' +\
             ' Block heights collected are not in sync.\n' +\
             ' ' + str(nodekeydiff) + ' nodes deviate from my node.\n' +\
             ' Nodes are Out of Sync.\n' +\
             ' source node : ' + nodename + '\n'

        telegram_bot_sendtext(tt)


# Function that sends message to telegram bot
# params
# - botmsg : the message to send
def telegram_bot_sendtext(botmsg):

    ### CODING ACTION: add try / except to absorb errors ###
    try:
        if tg == 'yes':
            send_text = tg_baseuri + tg_token + '/sendMessage?chat_id=' + tg_chatid + '&parse_mode=Markdown&text=' + botmsg
            response = https.request('GET', send_text)
            print(' Telegram message send.')
        else:
            print('\n Telegram turned off in config file. No message send.\n')
    except:
        print('\n WARNING' +\
              ' Error while sending telegram message. Telegram service down?\n')

# Function that requests POST rollback api call
# params
# - wavesnode : waves full node to use
# - rollbackblock : blockheight to which rollback occurs
def rollback_call(wavesnode,rollbackblock):

    json_body = {
                    "rollbackTo": int(rollbackblock),
                    "returnTransactionsToUtx": True
                }

    encoded_body = json.dumps(json_body).encode('utf-8')

    request = http.Request(
                            wavesnode + rollback_uri,
                            data=encoded_body,
                            headers={'Content-Type': 'application/json',
                                     'api_key' : APIkey }
                           )
    try:
        response = http.urlopen(request).read()
    except urllib.error.HTTPError as e:
        response = e.reason
        print(" HTTP Failed. " + response)
        pass
    except ConnectionResetError:
        print(" Connection reset error.")
        print(" Probably the POST rollback call works. Give it some time. The Server is very busy now.")
        print(" Check your waves service status. If nothing changes in the log, it is ok. Just give it some time.")
        pass


# Function that checks if the rollbackfile is stale
# If determined stale, delete it and report
def check_rollback_file():
    print()



# Function that triggers actions if a fork was detected
# If clarifies if my node or a control node forked
# If my node forked, touch a forkfile with forkheight and
# alert a telegram message.
# Automatic rollback depends of configfile setting
def fork_actions():

    need_rollback = False
    rollbackheight = startblock-6 #block where to rollback to
    forkfile = "forked." + str(rollbackheight)
    hoursleft = round((int(max_blocks) / 60), 2) #How many hours in which rollback should occur

    if acncnt == 1: #Only 1 active control node, not clear who forked
        print(" =========================================================================\n" +\
              " Warning! Detected a fork!\n" +\
              " However, there is only one active control node : " + list(controlnodeblocks)[0] + ".\n" +\
              " It can not be determined if my node '" + mynode + "' forked or the control node.\n" +\
              " Suggestion : Add more control nodes or explore logs of your node.\n" +\
              " =========================================================================")

        f = open(forkfile,"w+") #create forkfile with rollback blockheight
        f.close()

        tt = '\nMonitoring Alert!\n' +\
             '-----------------\n' +\
             'Fork detected on Waves blockchain!\n' +\
             'However, there is only 1 active controlnode.\n' +\
             'Not clear if my node forked or the control node\n' +\
             'suggestion:\n' +\
             'Add more control nodes or explore\n' +\
             'logs of your node ' + str(mynode) + "'.\n" +\
             'node : ' + nodename + '\n'

    elif acncnt > 1 and acncnt == forkcounter: #multiple control nodes and counted a fork for every node

        need_rollback = True

        print(" =================================================\n" +\
              " Warning! My node '" + mynode + "' forked!!!\n" +\
              " Need Rollback to block '" + str(rollbackheight) + "'\n" +\
              " node : " + nodename + '\n' +\
              " =================================================\n")

        f = open(forkfile,"w+") #create forkfile with rollback blockheight
        f.close()

        tt = '\nMonitoring Alert!\n' +\
             '-----------------\n' +\
             'My Waves node fork at ' + str(currentdate()) + '\n' +\
             "node : '" + mynode + '"\n' +\
             'rollback to block ' + str(rollbackheight) + ' in ' + str(hoursleft) + ' hrs.\n' +\
             'node : ' + nodename + '\n'

    else: #Multiple control nodes and counted more then one forks
        print(" ====================================================\n" +\
              " Detected '" + str(forkcounter) + "' forked nodes.\n" +\
              " However, there are '" + str(acncnt) + "' active control nodes.\n" +\
              " My node is not on fork, take action for control nodes.\n" +\
              " node : " + nodename + '\n' +\
              " ====================================================\n" )

        tt = '\nMonitoring Alert!\n' +\
             ' -----------------\n' +\
             'Detected "' + str(forkcounter) + '" forked nodes!\n' +\
             'However, there are "' + str(acncnt) + '" active control nodes.\n' +\
             'My node is NOT on fork. Take action for control nodes.\n' +\
             'rollback block : ' + str(rollbackheight) + '\n' +\
             'source node : ' + nodename + '\n'

    telegram_bot_sendtext(tt)

    if need_rollback == True and auto_rollback == 'yes': #rollback the blockchain automatically

        rollbackfile = "rollback." + str(rollbackheight)
        rollbackfinished = "finished." + str(rollbackheight)
        print("\n My node is on fork. Auto rollback is desired according forkconfig.json.")
        print(" Will rollback to block '" + str(rollbackheight) + "'.")
        print(" Requesting rollback now to block '" + str(rollbackheight) + "' on node '" + mynode + "'....")

        tt = '\nMonitoring Alert!\n' +\
             ' -----------------\n' +\
             ' Rollback to block "' + str(rollbackheight) + '" requested.\n' +\
             ' node : ' + mynode + '\n' +\
             ' node : ' + nodename + '\n'

        telegram_bot_sendtext(tt)

        os.rename(forkfile, rollbackfile) #rename forkfile to rollback file
        rollback_call(mynode,rollbackheight) #activate rollback
        os.rename(rollbackfile, rollbackfinished) #rename rollback file to finished file

        for name in glob.glob('forked.[0-9]*'): #Found old forkfiles, remove
            print(' Found old forfile, deleting : ' + name)
            os.remove(name)

        tt = '\nMonitoring Alert!\n' +\
             ' -----------------\n' +\
             ' Rollback to block "' + str(rollbackheight) + '" finished.\n' +\
             ' node : ' + mynode + '\n' +\
             ' node : ' + nodename + '\n'

        telegram_bot_sendtext(tt)

        print("\n Rollback finished!\n")

    elif need_rollback == True and auto_rollback =='no': #Need manual rollback

        print(" You can automate rollback with command : '" + sys.argv[0] + " rollback " + str(rollbackheight) + "'\n")


# ========== START MAIN PROGRAM ==========

print("\n Started forktester : " + currentdate())
print(" ----------------------------------------------------------------------------")

check_start_mode()

if startblock == 0: #Normal program start was done

    check_ongoing_rollback() #Check if a rollback is active
    check_forkfile() #Check if a fork was detected and if rollback needs to be done
    set_startblock(mynode) #Call lastblock and set startblock for block validation range

    print("\n Use last block height :", str(startblock+lastblockshift) + "  [ validate blockrange", startblock,"--",startblock-4,"]")

else: #startblock was set manually

    print("\n Start at block height :", str(startblock) + "  [ validate blockrange", startblock,"--",startblock-4,"]")

print("\n GET blocks from My Node '" + mynode + "'")

mynodeblocks = get_blocks(mynode) #Create dict with validation blocks and headers for mynode
controlnodeblocks = get_controlnode_blocks(cn) #Create list with ordered dict of validation blocks and headers for ctrl nodes

cncnt = len(cn) #How many controlnodes do we have in configfile
acncnt = len(controlnodeblocks) #How many active controlnodes do we have

mykeys = set(mynodeblocks.keys()) #ordered set of all blockheights of mynode

compare_keys_headers(mykeys, controlnodeblocks, mynodeblocks) #Compare collected blockheights and headers

if fork == True: #Actions to do if a fork is detected

    fork_actions()


print(" ============================================================================\n")
