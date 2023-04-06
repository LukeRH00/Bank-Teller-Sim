from threading import *
import time
import random, os

TELLER_NUM = 3
CUSTOM_NUM = 100

Tsetup = Semaphore(1)       #set to 1; used when teller is setting ID and choosing station
Csetup = Semaphore(1)       #set to 1; used when a customer is setting ID and determining transaction type
leaveLine = Semaphore(TELLER_NUM)    #set to number of active tellers in bank
selectTeller = Semaphore(1) #keep as 1; so if multiple customers are selecting at same time, don't interfere
inSafe = Semaphore(2)       #keep as 2; only 2 tellers in safe at once
withManager = Semaphore(1)  #keep as 1; only 1 teller discussing with manager at once
TwaitC = [Semaphore(0) for _ in range(TELLER_NUM)]    #used for making each teller wait for a customer; array is size of the number of tellers
Twait = [Semaphore(0) for _ in range(TELLER_NUM)]    #used for making each teller wait during interactions; array is size of the number of tellers
Cwait = [Semaphore(0) for _ in range(TELLER_NUM)]    #used for making each customer wait when interacting with a teller; array is size of the number of tellers
Tfinal = Semaphore(1)

tTracker = 0    #counter used to keep track of teller states across all of them
tDone = 0
bankOpen = False    #used to determine state of bank
tID = 0
cID = 0
count = CUSTOM_NUM
stations = [[-1,-1] for _ in range(TELLER_NUM)]

def Teller():
    #start of setup; assign ID, select station
    global tTracker
    global count
    Tsetup.acquire()
    global tID
    id = tID
    tID = tID + 1
    print("Teller " + str(id) + " is ready to serve.")
    i = 0
    while(stations[i][0] != -1):
        i = i + 1
    stations[i][0] = id
    stationID = i
    print("Teller " + str(id) + " is waiting for a customer.")
    tTracker = tTracker + 1 #indicates that another teller is ready
    Tsetup.release()

    global bankOpen
    if(tTracker >= TELLER_NUM): #open bank if all tellers are ready
        bankOpen = True

    while(count > 0): #continues while possible customers still remain
        TwaitC[stationID].acquire() #wait for customer
        if(stations[stationID][1] == -1): #means that another teller signaled end of customers
            pass
        else:
            #got customer, decrement counter
            count = count - 1
            custID = stations[stationID][1] #retrieve customer id from introduction
            print("Teller " + str(id) + " is serving Customer " + str(custID) + ".")

            #ask for transaction
            stations[stationID][1] = "What is your transaction?"
            Cwait[stationID].release() #signal customer of question
            Twait[stationID].acquire() #wait for customer response

            #get response from customer
            transaction = stations[stationID][1]
            if(transaction == "withdrawal"):
                print("Teller " + str(id) + " is handling the withdrawal transaction.")
                #go to manager to get withdrawal permission
                print("Teller " + str(id) + " is going to the manager.")

                withManager.acquire() #only 1 at a time
                print("Teller " + str(id) + " is getting the manager's permission.")

                #time spent asking manager's permission
                mWaitTime = (int)((random.random() * 25) + 5)
                mWaitTime = mWaitTime / 1000
                time.sleep(mWaitTime)
                print("Teller " + str(id) + " is got the manager's permission.")
                withManager.release()
            else:
                if(transaction == "deposit"):
                    print("Teller " + str(id) + " is handling the withdrawal transaction.")
                else:
                    print("ERROR - customer transaction type unreadable:: " + str(transaction))
                    os._exit(1)
            
            #regardless of type, manually go to safe to perform transaction
            print("Teller " + str(id) + " is going to the safe.")

            inSafe.acquire() #only 1 at a time
            print("Teller " + str(id) + " is in the safe.")

            #take time in safe, then leave
            sWaitTime = (int)((random.random() * 40) + 10)
            sWaitTime = sWaitTime / 1000
            time.sleep(sWaitTime)
            print("Teller " + str(id) + " is leaving the safe.")
            inSafe.release()

            #inform customer of transaction complete
            stations[stationID][1] = "done"
            print("Teller " + str(id) + " finishes Customer " + str(custID) + "'s " + transaction + " transaction.")
            Cwait[stationID].release()
            Twait[stationID].acquire()

            #clean up work to prepare for next customer
            stations[i][1] = -1
            print("Teller " + str(id) + " is ready to serve.")
            print("Teller " + str(id) + " is waiting for a customer.")
            leaveLine.release()
    
    #if the while loop has exited, that means THIS thread for teller checked for customers when no more are left over for the whole day
    #it is possible that other tellers are still locked IF multiple were waiting for customers when there were only 1 or 2 possible customers that could appear for the day
    #therefore, need to release all TwaitC instances just in case
    #This is the reason TwaitC was separated from Twait; needed a teller thread to be able to unblock other teller threads without interfering with tellers actively serving customers still
    Tfinal.acquire()
    if(tTracker >= TELLER_NUM): #check if this is the first teller to be done
        tTracker = tTracker - 1
        for y in range(TELLER_NUM): #release all other tellers; stations[i][1] should still be -1 if they were indefinitely waiting
            TwaitC[y].release()
    else: #just decrement the counter
        tTracker = tTracker - 1
    Tfinal.release()

    #busy wait until all tellers are done
    while(tTracker > 0):
        pass

    print("Teller " + str(id) + " is leaving for the day.")

    global tDone
    Tfinal.acquire()
    tDone = tDone + 1
    if(tDone >= TELLER_NUM):
        print("The bank closes for the day.") #close bank if last teller
    Tfinal.release()



def Customer():
    #set up customer ID and transaction type
    Csetup.acquire()
    global cID
    id = cID
    cID = cID + 1
    choice = random.randrange(2)
    transType =''
    if(choice == 1):
        transType = "withdrawal"
        print("Customer " + str(id) + " wants to perform a withdrawal transaction.")
    else:
        transType = "deposit"
        print("Customer " + str(id) + " wants to perform a deposit transaction.")
    Csetup.release()

    #randomize wait time for customer to go to bank
    waitTime = (int)(random.random() * 5000)
    waitTime = waitTime / 1000
    time.sleep(waitTime)

    #go to bank after done waiting
    print("Customer " + str(id) + " is going to the bank.")
    global bankOpen
    while(not(bankOpen)):
        #cannot enter while bank not open
        pass

    #get in line, find teller if ready to serve
    print("Customer " + str(id) + " is getting in line.")
    leaveLine.acquire() #means a teller is ready to serve
    selectTeller.acquire() #used so if there are multiple customers simultaneously selecting, do not interfere with each other
    print("Customer " + str(id) + " is selecting a teller.")
    i = 0
    while(stations[i][1] != -1):
        i = i + 1
    stations[i][1] = id
    stationNum = i
    selectTeller.release() #done with selection, already chose station by putting down id
    tellerID = stations[stationNum][0]
    print("Customer " + str(id) + " goes to Teller " + str(tellerID) + ".")
    print("Customer " + str(id) + " introduces itself to Teller " + str(tellerID) + ".") #already done when putting down id
    TwaitC[stationNum].release() #alert teller
    Cwait[stationNum].acquire() #wait for teller

    #Check teller's prompt, respond with transaction type
    if(stations[i][1] == "What is your transaction?"):
        stations[i][1] = transType
        print("Customer " + str(id) + " asks for a " + transType + " transaction.")
    else:
        print("ERROR - Teller prompt unreadable")
        os._exit(1)
    
    Twait[stationNum].release() #alert teller
    Cwait[stationNum].acquire() #wait until teller gives permission to leave

    #get info from teller about transaction
    if(stations[i][1] == "done"):
        print("Customer " + str(id) + " thanks Teller " + str(tellerID) + " and leaves.")
    else:
        print("ERROR - Transaction completion unreadable")
        os._exit(1)

    Twait[stationNum].release() #leave station and unblock teller




if __name__ == '__main__':
    for x in range(TELLER_NUM):
        t = Thread(target = Teller, args = ())
        t.start()

    for x in range(CUSTOM_NUM):
        c = Thread(target = Customer, args = ())
        c.start()