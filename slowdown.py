import os
from dataclasses import dataclass
import math

with open('print.gcode', 'r') as f:
    gcodeStr = f.read()

lines = gcodeStr.splitlines()

def updateWithMove(x, y):
    dx = x - state.x
    dy = y - state.y
    deltaDist = math.sqrt(dx*dx+dy*dy)
    state.x = x
    state.y = y
    state.distance += deltaDist
    return deltaDist

def isRetraction(line):
    return ('G1' in line) and ('E-' in line)

blocks = []
block = []

for line in lines:

    if isRetraction(line):
        block.append(line)
        blocks.append(block)
        block = []
    else:
        block.append(line)
if len(block) > 0:
    blocks.append(block)

def isComment(line): 
    return line.startswith(';')   

def isInitBlock(block):
    for line in block:
        if isComment(line):
            continue
        if 'G28' in line:
            return True
    return False

def splitComment(line):
    return line.split(';', 1)

def isXYMoveCommand(line):
    if isComment(line):
        return False
    if 'E-' in line:
        return False
    if not line.startswith('G1'):
        return False
    theLine = splitComment(line)
    parts = theLine[0].split(' ')
    for part in parts:
        if part.startswith('X'):
            return True
        if part.startswith('Y'):
            return True
    return False

def parseXY(line):
    theLine = splitComment(line)
    parts = theLine[0].split(' ')
    x = -1
    y = -1
    for part in parts:
        if part.startswith('X'):
            x = float(part[1:])
        if part.startswith('Y'):
            y = float(part[1:])
    if (x == -1) or (y == -1):
        print('Found partial G1 command')
        print(line)
    return [x, y]

def blockFinalPosition(block):
    for line in reversed(block):
        if isXYMoveCommand(line):
            return parseXY(line)
    print('Found block with no position')
    return [0.0, 0.0]

def isFinalBlock(block):
    for line in block:
        if isComment(line):
            continue
        if 'M84' in line:
            return True
    return False

def replaceXY(line, x, y):
    theLine = splitComment(line)
    parts = theLine[0].split(' ')
    result = []
    for part in parts:
        if part.startswith('X'):
            result.append('X{}'.format(x))
        elif part.startswith('Y'):
            result.append('Y{}'.format(y))
        else:
            result.append(part)
    theLine[0] = ' '.join(result)
    return ';'.join(theLine)

TARGET_SLOWDOWN_DISTANCE = 10.0
SLOWDOWN_COMMAND = 'G1 F900'

def executeMove(line, x, y):
    if isXYMoveCommand(line):
        nextPosition = parseXY(line)
        dx = nextPosition[0] - x
        dy = nextPosition[1] - y
        delta = math.sqrt(dx*dx + dy*dy)
        return {
            'x': nextPosition[0],
            'y': nextPosition[1],
            'delta': delta
        }
    return {
        'x': x,
        'y': y,
        'delta': 0.0
    }

def blockTotalDistance(block, startX, startY):
    distanceTravelled = 0.0
    for line in block:
        move = executeMove(line, startX, startY)
        startX = move['x']
        startY = move['y']
        distanceTravelled += move['delta']
    return {
        'distanceTravelled': distanceTravelled,
        'x': startX,
        'y': startY
    }

state = {
    'x': 0.0,
    'y': 0.0
}

def processBlock(block):
    initialX = state['x']
    initialY = state['y']
    blockDistance = blockTotalDistance(block, state['x'], state['y'])
    travelled = blockDistance['distanceTravelled']
    state['x'] = blockDistance['x']
    state['y'] = blockDistance['y']
    print('Block travelled {}'.format(travelled))


    if isInitBlock(block):
        print('Init block processed')
        return block
    if isFinalBlock(block):
        print('Final block processed')
        return block
    
    if travelled < TARGET_SLOWDOWN_DISTANCE:
        # Small block, slowdown everything
        return [SLOWDOWN_COMMAND + ' ; Small block full slowdown'] + block
    
    # Big block, find slowdown point
    targetSlowdownDistancePoint = travelled - TARGET_SLOWDOWN_DISTANCE
    x = initialX
    y = initialY
    delta = 0.0
    newBlock = []
    slowdownExecuted = False
    for line in block:
        if slowdownExecuted:
            newBlock.append(line)
            continue
        move = executeMove(line, x, y)
        x = move['x']
        y = move['y']
        delta += move['delta']
        if delta >= targetSlowdownDistancePoint:
            newBlock.append(SLOWDOWN_COMMAND + ' ; slowdown at {} before retract'.format(travelled - delta + move['delta']))
            slowdownExecuted = True
        newBlock.append(line)
    return newBlock
    # position = blockFinalPosition(block)
    # targetDistance = 10.0
    # distanceFromRetraction = 0.0
    # slowdownProcessed = False
    # result = [] # lines
    # for line in reversed(block):
    #     if slowdownProcessed:
    #         result.append(line)
    #         continue
    #     if isComment(line):
    #         result.append(line)
    #         continue
    #     if isRetraction(line):
    #         result.append(line)
    #         continue
    #     if not isXYMoveCommand(line):
    #         result.append(line)
    #         continue
    #     prevPosition = parseXY(line)
    #     dx = prevPosition[0] - position[0]
    #     dy = prevPosition[1] - position[1]
    #     deltaDistance = math.sqrt(dx*dx + dy*dy)
    #     distanceFromRetraction += deltaDistance
    #     if distanceFromRetraction >= targetDistance:
    #         # Split current line and insert slowdown code
    #         slowdownProcessed = True
    #         splitPointFromLineEnd = distanceFromRetraction - targetDistance
    #         splitPointFromLineBeginning = deltaDistance - splitPointFromLineEnd
    #         splitPointRelative = splitPointFromLineBeginning / deltaDistance
    #         # Segment 1
    #         seg1X = prevPosition[0] + (splitPointRelative * dx)
    #         seg1Y = prevPosition[1] + (splitPointRelative * dy)
    #         # Reverse order append
    #         result.append(line) # segment 2 is the same as original line!
    #         result.append(SLOWDOWN_COMMAND + ' ; Pre retract slowdown') # slowdown
    #         result.append('G1 X{} Y{}'.format(seg1X, seg1Y)) # segment 1
    #     else:
    #         result.append(line)
    # if not slowdownProcessed:
    #     result.append(SLOWDOWN_COMMAND + ' ; Slowdown entire block')
    # return reversed(result)


processedBlocks = []
for block in blocks:
    processedBlocks.append(processBlock(block))

with open('processed.gcode', 'w') as f:
    for block in processedBlocks:
        f.write('\n'.join(block))
        f.write('\n')