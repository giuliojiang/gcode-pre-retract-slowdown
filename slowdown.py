import math
import os

def isRetraction(line):
    return ('G1' in line) and ('E-' in line)

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

def processBlock(block, state):
    initialX = state['x']
    initialY = state['y']
    blockDistance = blockTotalDistance(block, state['x'], state['y'])
    travelled = blockDistance['distanceTravelled']
    state['x'] = blockDistance['x']
    state['y'] = blockDistance['y']

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

def transform(inputPath):
    with open(inputPath, 'r') as f:
        gcodeStr = f.read()
    lines = gcodeStr.splitlines()
    state = {
        'x': 0.0,
        'y': 0.0
    }
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
    processedBlocks = []
    for block in blocks:
        processedBlocks.append(processBlock(block, state))
    inputName, inputExt = os.path.splitext(inputPath)
    outputName = inputName + '_unstring'
    with open(outputName + inputExt, 'w') as f:
        for block in processedBlocks:
            f.write('\n'.join(block))
            f.write('\n')

def main():
    filePaths = os.listdir('.')
    for filePath in filePaths:
        fileName, ext = os.path.splitext(filePath)
        if (ext == '.gcode') and (not (fileName.endswith('_unstring'))):
            transform(filePath)

main()