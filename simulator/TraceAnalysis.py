from asyncio.subprocess import PIPE
#from turtle import color, left, position, right
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import argparse
import time
import os
import sys


def get_immediate_subdirectories(a_dir):
    return [name for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]


cwd = os.getcwd()
print(cwd)
subdirs = get_immediate_subdirectories(cwd)

# Create the parser
parser = argparse.ArgumentParser()
# Add an argument
parser.add_argument('--f', type=str, required=True,
                    help="Folder containing NVMain simulation results.")
parser.add_argument('--m', type=str, required=False, default="all",
                    help="Memmory region (text|ro|data|bss|heap|stack|all) to analyse, defaults to 'all'.")
parser.add_argument('--w', type=str, required=False, default="64",
                    help="Window size to calculate AEW (Input: 8|16|32|64|all), defaults to '64'.")
parser.add_argument('--p', type=bool, required=False, default=False,
                    help="Turn on/off plotting, defaults to plot AEW of '64'.")
# Parse the argument
args = parser.parse_args()
print(args)
sysTerm = args.f + '/m5out/system.terminal'

trace = args.f + '/nvmain.nvt'


def merge_inputs_sorted(input_patched, input_rot):
    merged_input = np.zeros(
        (np.shape(input_rot)[0] + np.shape(input_patched)[0], int(9)), dtype=int)
    i = 0
    j = 0
    k = 0
    while True:
        if input_rot[i][0] == input_patched[j][0]:
            appendee = np.array([input_rot[i][0],  # Adresse
                                 input_rot[i][1],  # wAcces
                                 input_rot[i][2],  # bFlips
                                 input_rot[i][3],  # CacheLevelAccess
                                 input_rot[i][4],  # CacheLevelFlips
                                 input_patched[j][1],
                                 input_patched[j][2],
                                 input_patched[j][3],
                                 input_patched[j][4]])
            j += 1
            i += 1
        elif input_rot[i][0] < input_patched[j][0]:
            appendee = np.array([input_rot[i][0],
                                 input_rot[i][1],
                                 input_rot[i][2],
                                 input_rot[i][3],
                                 input_rot[i][4],
                                 0,
                                 0,
                                 0,
                                 0])
            i += 1
        else:
            appendee = np.array([input_patched[j][0],
                                 0,
                                 0,
                                 0,
                                 0,
                                 input_patched[j][1],
                                 input_patched[j][2],
                                 input_patched[j][3],
                                 input_patched[j][4]])
            j += 1
        merged_input[k] = appendee
        k += 1
        if i == np.shape(input_rot)[0] and j == np.shape(input_patched)[0]:
            break
    return np.resize(merged_input, (k, 9))


def merge_inputs_sorted_new(input1):
    merged_input = np.zeros((np.shape(input1)[0], int(11)), dtype=int)
    shape = np.shape(input1)
    for i in range(0, shape[0]):
        appendee = np.array([input1[i][0],  # Address
                             input1[i][1],  # wAcces
                             input1[i][2],  # bFlips
                             input1[i][3],  # CacheLevelAccess
                             input1[i][4],  # CacheLevelFlips
                             input1[i][5],  # CacheLevelAccessOV
                             input1[i][6],  # CacheLevelFlipOV
                             input1[i][7],  # PageLevelAccess
                             input1[i][8],  # PageLevelFlips
                             input1[i][9],  # PageLevelAccessOV
                             input1[i][10],  # PageLevelFlipOV
                             ])  # PageLevelFlipOV
        merged_input[i] = appendee
        if i == np.shape(input1)[0]:
            break
    return np.resize(merged_input, (i, 11))


def getAddress(addressString, file):
    ret = subprocess.run(
        ["grep", '-i', addressString, file], stdout=PIPE)
    string = ret.stdout
    string = string.strip()
    string = string.lstrip()
    string = string.split(bytes("8", encoding='UTF-8'), 1)[1]
    return int(int(string, base=16)*8)


def calcMetrics(bitflipsIn, wAccesses, start, stop, length):
    bitflips = bitflipsIn[start:stop]
    wAccesses = wAccesses[start:stop:64]
    sum = np.sum(bitflips)
    sumAccesses = np.sum(wAccesses)
    maxflips = 0
    N = 0
    for i in range(0, np.size(bitflips)):
        if not(bitflips[i] == 0):
            N += 1
        if bitflips[i] > maxflips:
            maxflips = bitflips[i]
    meanflips = np.sum(bitflips)/length / np.max(bitflips)
    return meanflips/maxflips, sumAccesses/meanflips, sum


def calcWordMetrics(bitflipsIn, wAccesses, start, stop):
    bitflips = bitflipsIn[start:stop]
    wAccesses = wAccesses[start:stop:64]
    sum = np.sum(bitflips)
    sumAccesses = np.sum(wAccesses)
    maxflips = 0
    N = 0
    for i in range(0, np.size(bitflips)):
        if not(bitflips[i] == 0):
            N += 1
        if bitflips[i] > maxflips:
            maxflips = bitflips[i]
    meanflips = np.mean(bitflips)
    return meanflips/maxflips, sumAccesses/meanflips, sum


# =====================================
# =====Getting Memory Addresses========
# =====================================
# Get memory addresses
textStart = getAddress("__apptext_start", sysTerm)
textEnd = getAddress("__apptext_end", sysTerm)
roStart = getAddress("__approdata_start", sysTerm)
roEnd = getAddress("__approdata_end", sysTerm)
dataStart = getAddress("__appdata_start", sysTerm)
dataEnd = getAddress("appdata_end", sysTerm)
bssStart = getAddress("appbss_start", sysTerm)
bssEnd = getAddress("__appbss_end", sysTerm)
heapStart = getAddress("__appheap_start", sysTerm)
heapEnd = getAddress("__appheap_end", sysTerm)
stackStart = getAddress("__appstack_start", sysTerm)
stackEnd = getAddress("__appstack_end", sysTerm)

# =====================================
# =====Parsing Input===============
# =====================================

print("Importing trace.")
startTime = time.time()
try:
    data = np.load(args.f + "/trace" + ".npz")
    inputTrace = data['a']
except:
    print("Importing for the first time. Compressing trace.")
    inputTemp = np.loadtxt(trace, delimiter=',', dtype=int)
    inputTrace = merge_inputs_sorted_new(inputTemp)
    np.savez_compressed(args.f + "/trace" + ".npz",
                        a=inputTrace)
finally:
    timetaken = time.time() - startTime
    print("Import took: " + str(int(timetaken)) + " seconds")


# =====================================
# =====Normalizing Input===============
# =====================================
startTime = time.time()
print("Starting Calculations.")
input = inputTrace
textStartIndex = np.where(input[:, 0:1] >= textStart)
textEndIndex = np.where(input[:, 0:1] >= textEnd-1)

dataRoStartIndex = np.where(input[:, 0:1] >= roStart)
dataRoEndIndex = np.where(input[:, 0:1] >= roEnd-1)

dataStartIndex = np.where(input[:, 0:1] >= dataStart)
dataEndIndex = np.where(input[:, 0:1] >= dataEnd-1)

bssStartIndex = np.where(input[:, 0:1] >= bssStart)
bssEndIndex = np.where(input[:, 0:1] >= bssEnd-1)

heapStartIndex = np.where(input[:, 0:1] >= heapStart)
heapEndIndex = np.where(input[:, 0:1] >= heapEnd-1)

stackStartIndex = np.where(input[:, 0:1] >= stackStart)
stackEndIndex = np.where(input[:, 0:1] >= stackEnd-1)


accesses = input[:, 1:2]+1
bits = np.arange(0, np.size(accesses), 1, dtype=int)
flips = input[:, 2:3]+1
# accessesC = input[:, 5:6]+1
#flipsC = input[:, 6:7]+1
# accessesP = input[:, 9:10]+1
# flipsP = input[:, 10:11]+1
# flipsOptC = input[:, 4:5]+1
# flipsOptP = input[:, 8:9]+1
start = 0
np.transpose(bits)
end = np.size(bits)


# =====================================
# =====Calculate Metrics===============
# =====================================

#Calculating AEW with given start/endindex and windowsize
#IMPORTANT: The algorithm searches for the minimum value but the values are named MAX through out the script! (not very smart)
def calculateAEW(startIndex, endIndex, windowSize):
    leftBound = 0
    rightBound = 0
    count = 0
    maxWindowValue = sys.maxsize
    for i in range(startIndex, endIndex):
        if i+windowSize < endIndex:
            aeWindow = (np.sum(flips[i:i+windowSize])/np.shape(flips)[0]) / np.max(flips[i:i+windowSize])
            if aeWindow < maxWindowValue:
                maxWindowValue = aeWindow
                leftBound = i
                rightBound = i+windowSize
                count = 0
            #Counts if there are multiple maxAEW for the trace (might be interesting)
            elif aeWindow == maxWindowValue:
                count+1
        else:
            break
    print("Same AEW " + str(count))
    return maxWindowValue, leftBound, rightBound
#for i in range(0, np.size(flips)):
    #aeWindow = (np.sum(flips[i:i+windowSize])/np.shape(flips)[0]) / np.max(flips[i:i+windowSize])
    #if(aeWindow == maxWindowValue):
        #print("left: " + " right ", i, i+windowSize)

# =====================================
# Some more fancy calculations should go here.
# =====================================

timetaken = time.time() - startTime
print("Calculating took: " + str(int(timetaken)) + " seconds")


#Filtering memory index for calculation
segment = args.m
print("Chosen segment: " + segment)
def memory_region():
    match segment:
        case "text":
            return textStartIndex[0][0], textEndIndex[0][0]
        case "ro":
            return dataRoStartIndex[0][0], dataRoEndIndex[0][0]
        case "data":
            return dataStartIndex[0][0], dataEndIndex[0][0]
        case "bss":
            return bssStartIndex[0][0], bssEndIndex[0][0]
        case "heap":
             return heapStartIndex[0][0], heapEndIndex[0][0]
        case "stack":
             return stackStartIndex[0][0], end
        case "all":
            return textStartIndex[0][0], end

startindex, endindex = memory_region()
# =============================
# =====Print Metrics===========
# =============================

#Calculating stuff like AE and AEW in all sizes

achievedEndurance = (np.sum(flips[startindex:endindex])/np.shape(flips)[0]) / np.max(flips[startindex:endindex])

print("Chosen size for AEW: " + args.w + "\n\n")

#Filtering for --w input to calculate wanted AEW

if args.w == "8":
    aewMax8, leftindex8, rightindex8 = calculateAEW(startindex,endindex,7)
    print("FOR N=8 and " + segment + " segment!")
    print("AE: " + str(achievedEndurance))
    print("AEW: " + str(aewMax8))
    print("AE/AEW " + str(achievedEndurance/aewMax8))
    print("AEW/AE " + str(aewMax8/achievedEndurance))
    print("left and right " + str(leftindex8), str(rightindex8))
    print("\n\n")

elif args.w == "16":
    aewMax16, leftindex16, rightindex16 = calculateAEW(startindex,endindex,15)
    print("FOR N=16 and " + segment + " segment!")
    print("AE: " + str(achievedEndurance))
    print("AEW: " + str(aewMax16))
    print("AE/AEW " + str(achievedEndurance/aewMax16))
    print("AEW/AE " + str(aewMax16/achievedEndurance))
    print("left and right " + str(leftindex16), str(rightindex16))
    print("\n\n")
elif args.w == "32":
    aewMax32, leftindex32, rightindex32 = calculateAEW(startindex,endindex,31)
    print("FOR N=32 and " + segment + " segment!")
    print("AE: " + str(achievedEndurance))
    print("AEW: " + str(aewMax32))
    print("AE/AEW " + str(achievedEndurance/aewMax32))
    print("AEW/AE " + str(aewMax32/achievedEndurance))
    print("left and right " + str(leftindex32), str(rightindex32))
    print("\n\n")

elif args.w == "all":
    print("AE: " + str(achievedEndurance))
    aewMax8, leftindex8, rightindex8 = calculateAEW(startindex,endindex,7)
    print("FOR N=8 and " + segment + " segment!")
    print("AEW: " + str(aewMax8))
    print("AE/AEW " + str(achievedEndurance/aewMax8))
    print("AEW/AE " + str(aewMax8/achievedEndurance))
    print("left and right " + str(leftindex8), str(rightindex8))
    print("\n\n")
    aewMax16, leftindex16, rightindex16 = calculateAEW(startindex,endindex,15)
    print("FOR N=16 and " + segment + " segment!")
    print("AEW: " + str(aewMax16))
    print("AE/AEW " + str(achievedEndurance/aewMax16))
    print("AEW/AE " + str(aewMax16/achievedEndurance))
    print("left and right " + str(leftindex16), str(rightindex16))
    print("\n\n")
    aewMax32, leftindex32, rightindex32 = calculateAEW(startindex,endindex,31)
    print("FOR N=32 and " + segment + " segment!")
    print("AEW: " + str(aewMax32))
    print("AE/AEW " + str(achievedEndurance/aewMax32))
    print("AEW/AE " + str(aewMax32/achievedEndurance))
    print("left and right " + str(leftindex32), str(rightindex32))
    print("\n\n")
    aewMax64, leftindex64, rightindex64 = calculateAEW(startindex,endindex,63)
    print("FOR N=64 and " + segment + " segment!")
    print("AEW: " + str(aewMax64))
    print("AE/AEW " + str(achievedEndurance/aewMax64))
    print("AEW/AE " + str(aewMax64/achievedEndurance))
    print("left and right " + str(leftindex64), str(rightindex64))
    print("\n\n")

else:
    aewMax64, leftindex64, rightindex64 = calculateAEW(startindex,endindex,63)
    print("FOR N=64 and " + segment + " segment!")
    print("AE: " + str(achievedEndurance))
    print("AEW: " + str(aewMax64))
    print("AE/AEW " + str(achievedEndurance/aewMax64))
    print("AEW/AE " + str(aewMax64/achievedEndurance))
    print("left and right " + str(leftindex64), str(rightindex64))
    print("\n\n")

# =====================================
# ===== Plotting ======================
# =====================================

#======MemoryTracesPlot======

#======WHOLE MEMORY TRACE====

fig1, ax1 = plt.subplots()
ax1.set_title("")
ax1.set_xlabel("Adressess")
ax1.set_ylabel("Flips")
ax1.legend()
ax1.spines["right"].set_visible(False)
ax1.spines["top"].set_visible(False)
ax1.grid(True, which="both", linestyle='--', axis="y")
ax1.semilogy(bits[start:end], accesses[start:end], '-r', linewidth=0.3, label="Accesses")
ax1.semilogy(bits[textStartIndex[0][0]:textEndIndex[0][0]],flips[textStartIndex[0][0]:textEndIndex[0][0]], 'g.', linewidth=0.1, label='FlipsText')
ax1.semilogy(bits[dataRoStartIndex[0][0]:dataRoEndIndex[0][0]],flips[dataRoStartIndex[0][0]:dataRoEndIndex[0][0]],'k.', label='FlipsRoData')
ax1.semilogy(bits[dataStartIndex[0][0]:dataEndIndex[0][0]],flips[dataStartIndex[0][0]:dataEndIndex[0][0]],'k.', label='FlipsData')
ax1.semilogy(bits[bssStartIndex[0][0]:bssEndIndex[0][0]],flips[bssStartIndex[0][0]:bssEndIndex[0][0]],'b.', label='FlipsBss')
#ax1.semilogy(bits[heapStartIndex[0][0]:heapEndIndex[0][0]],flips[heapStartIndex[0][0]:heapEndIndex[0][0]],'m.', label='FlipsHeap')
#ax1.semilogy(bits[stackEndIndex[0][0]:stackStartIndex[0][0]],flips[stackStartIndex[0][0]:stackEndIndex[0][0]], 'y.', label='FlipsStack')
ax1.semilogy(bits[heapStartIndex[0][0]:end], flips[heapStartIndex[0][0]:end],'m.', label='FlipsRuntime')
ax1.legend()
ax1.ticklabel_format(style='sci', axis='x', scilimits=(0, 0))
ax1.xaxis.set_tick_params(which='both', labelbottom=True)
ax1.yaxis.set_tick_params(which='both', labelbottom=True)


#======AEW64Plot======

if args.w == "64" or "all":

    fig2, ax2 = plt.subplots()
    ax2.set_title("")
    ax2.set_ylabel("Flips")
    ax2.set_xlabel("Address")
    ax2.spines["right"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax2.grid(True, which="both", linestyle='--', axis="y")
    ax2.semilogy(accesses[start:endindex], '-r', label='Accesses')
    ax2.semilogy(bits[startindex:leftindex64], flips[startindex:leftindex64], 'c.', label='Flips')
    ax2.semilogy(bits[leftindex64:rightindex64], flips[leftindex64:rightindex64], 'go', label='FlipsAEW')
    ax2.semilogy(bits[rightindex64:endindex], flips[rightindex64:endindex], 'c.')
    ax2.legend(loc='upper right')
    ax2.ticklabel_format(style='sci', axis='x', scilimits=(0, 0))



#======AEW32Plot======

elif args.w == "32":

    fig2, ax2 = plt.subplots()
    ax2.set_title("")
    ax2.set_xlabel("Flips")
    ax2.set_ylabel("Address")
    ax2.spines["right"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax2.grid(True, which="both", linestyle='--', axis="y")
    ax2.semilogy(accesses[start:endindex], '-r')
    ax2.semilogy(bits[startindex:leftindex32], flips[startindex:leftindex32], 'c.', label='Flips')
    ax2.semilogy(bits[leftindex32:rightindex32], flips[leftindex32:rightindex32], 'go', label='FlipsAEW')
    ax2.semilogy(bits[rightindex32:endindex], flips[rightindex32:endindex], 'c.')
    ax2.legend()
    ax2.ticklabel_format(style='sci', axis='x', scilimits=(0, 0))



#======AEW16Plot======

elif args.w == "16":

    fig3, ax3 = plt.subplots()
    ax3.set_title("")
    ax3.set_xlabel("Flips")
    ax3.set_ylabel("Address")
    ax3.spines["right"].set_visible(False)
    ax3.spines["top"].set_visible(False)
    ax3.grid(True, which="both", linestyle='--', axis="y")
    ax3.semilogy(accesses[start:endindex], '-r')
    ax3.semilogy(bits[startindex:leftindex16], flips[startindex:leftindex16], 'c.', label='Flips')
    ax3.semilogy(bits[leftindex16:rightindex16], flips[leftindex16:rightindex16], 'go', label='FlipsAEW')
    ax3.semilogy(bits[rightindex16:endindex], flips[rightindex16:endindex], 'c.')
    ax3.legend()
    ax3.ticklabel_format(style='sci', axis='x', scilimits=(0, 0))


#======AEW8Plot======

elif args.w == "8":

    fi4, ax4 = plt.subplots()
    ax4.set_title("")
    ax4.set_xlabel("Flips")
    ax4.set_ylabel("Address")
    ax4.spines["right"].set_visible(False)
    ax4.spines["top"].set_visible(False)
    ax4.grid(True, which="both", linestyle='--', axis="y")
    ax4.semilogy(accesses[start:endindex], '-r')
    ax4.semilogy(bits[startindex:leftindex8], flips[startindex:leftindex8], 'c.', label='Flips')
    ax4.semilogy(bits[leftindex8:rightindex8], flips[leftindex8:rightindex8], 'go', label='FlipsAEW')
    ax4.semilogy(bits[rightindex8:endindex], flips[rightindex8:endindex], 'c.')
    ax4.legend()
    ax4.ticklabel_format(style='sci', axis='x', scilimits=(0, 0))

    # ax5.set_title("")
    # ax5.set_xlabel("Adressess")
    # ax5.set_ylabel("Flips")
    # ax5.spines["right"].set_visible(False)
    # ax5.spines["top"].set_visible(False)
    # ax5.grid(True, which="both", linestyle='--', axis="y")
    # ax5.semilogy(bits[start:end], accesses[start:end],
    #   5                 '-r', linewidth=0.3, label="#Accesses")
    # ax5.ticklabel_format(style='sci', axis='x', scilimits=(0, 0))
    # ax5.xaxis.set_tick_params(which='both', labelbottom=True)
    # ax5.yaxis.set_tick_params(which='both', labelbottom=True)

    # fig5, (ax5, ax1) = plt.subplots(1,2)
    # fig5.set_size_inches(11.5,4.5)

#if args.p:
plt.savefig(args.f + '/plot.png')
