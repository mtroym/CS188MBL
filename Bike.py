import simpy
import random
import math

import Scheduler

ALL_STATIONS = {}

NUM_STATIONS = 3
SLICES = 72

CALL_SCHEDULER = []

SAMPLES = []
REWARDS = []

def init_samples():
    for _ in range(NUM_STATIONS):
        SAMPLES.append([])
        for _ in range(SLICES):
            SAMPLES.append(0)

def init_rewards():
    for _ in range(NUM_STATIONS):
        REWARDS.append(0)

def init_caller(env):
    for i in range(NUM_STATIONS):
        CALL_SCHEDULER[i] = env.event()

def out_distri_uniform(a, b):
    return random.randint(a, b)

def normalize(distribution):
    s = 0
    nDistribution = {}
    for location in distribution.keys():
        s += distribution[location]
    for location in distribution.keys():
        nDistribution[location] = distribution[location] / s
    return nDistribution

def getStationFromIndex(idx):
    return ALL_STATIONS[idx]

def computeTransitionTime(start, end):
    distance = computeDistance(start, end)

    ''' The distribution would be modified upon hypothesis '''
    lower = min(1, distance - 2)
    return out_distri_uniform(lower, distance + 1) + 0.5
    ''' --- --- --- --- --- --- --- --- --- --- --- --- -- '''

def computeDistance(start, end):
    xs, sy = start.getPosition()
    es, ey = end.getPosition()
    return abs(xs - es) + abs(sy - ey)

def generateDispatcherDistribution(start):
    start_id = start.getIndex()
    distribution = {}
    for station in ALL_STATIONS.values():
        end_id = station.getIndex()

        # Not going to the start station
        if start_id == end_id:
            continue

        ''' The distribution would be modified upon hypothesis '''
        distance = computeDistance(start, station)
        distribution[end_id] = math.exp(-0.5 * distance)
        ''' --- --- --- --- --- --- --- --- --- --- --- --- -- '''

    # Normalize the distribution
    distribution = normalize(distribution)

    return distribution

def generateDispatcherNumbers(start, nBikes):
    if start.dispatch_distribution == None:
        start.dispatch_distribution = generateDispatcherDistribution(start)

    # generate number of bikes using sampling
    numbers = {}
    for _ in range(nBikes):
        sample = random.random()
        possiblility = 0
        for location in start.dispatch_distribution.keys():
            possiblility += start.dispatch_distribution[location]
            if sample < possiblility:
                # Add a sample
                if location in numbers.keys():
                    numbers[location] += 1
                else:
                    numbers[location] = 1
                break

    return numbers

class BikeScheduler:
    def __init__(self, env):
        self.env = env
        self.process = env.process(self.scheduler())

    def bikeScheduler(self, remains, rewards):
        schedules = []
        return schedules # A set of how much bikes for each station

    def scheduler(self):
        # The process scheduling the bikes at the end of the day
        while True:
            # Wait for call schedulers
            yield simpy.events.AllOf(self.env, CALL_SCHEDULER)
            init_caller(self.env) # Recreate caller triggers
            # print("DAY")

            # Call scheduler's algorithm
            schedules = self.bikeScheduler(SAMPLES, REWARDS)

class Buffer:
    def __init__(self):
        self.buffer = []

    def push(self, elem):
        self.buffer.append(elem)

    def pop(self):
        assert(len(self.buffer) != 0)
        return self.buffer.pop(0)

    def isNULL(self):
        return len(self.buffer) == 0

class Map:
    def __init__(self, env):
        self.env = env
        for i in range(NUM_STATIONS):
            pos_x = i
            pos_y = i + 1
            init_bike = 100
            ALL_STATIONS[i] = Station(env, (pos_x, pos_y), i, init_bike)
            CALL_SCHEDULER.append(env.event())

class Station:
    def __init__(self, env, position, idx, initial):
        self.env = env
        self.position = position # Position should be a tuple (x, y)
        self.idx = idx
        self.bikes = simpy.Container(env, init = initial)
        self.buf = Buffer()
        self.dispatch_distribution = None

        self.process = env.process(self.run())
        self.dispatcher = env.process(self.dispatcher())
        self.going = env.event()

    def run(self):
        while True:
            # Running one day of bike riding
            yield self.env.process(self.one_day())
            # Make sure the last dispatch of day finished
            while not self.buf.isNULL:
                yield self.env.timeout(20)
            # Tell scheduler that this station is ready
            CALL_SCHEDULER[self.getIndex()].succeed()
            yield self.env.timeout(20)

    def dispatcher(self):
        while True:
            yield self.going
            
            scheme = generateDispatcherNumbers(self,self.buf.pop())
            preorder = {}
            for sid in scheme.keys():
                preorder[sid] = computeTransitionTime(self, ALL_STATIONS[sid])

            # Dispatch bikes
            order = sorted(preorder.items(), key = lambda item:item[1])
            time = 0
            for dest in order:
                yield self.env.timeout(dest[1] - time)
                time = dest[1]
                s = getStationFromIndex(dest[0])
                s.bikes.put(scheme[dest[0]])

    def one_day(self):
        for i in range(SLICES):
            # Going out
            print("time: " + str(self.env.now))
            print(str(self.idx)+": "+str(self.bikes.level))

            ''' The distribution would be modified upon hypothesis '''
            outBike = out_distri_uniform(1, 20)
            ''' --- --- --- --- --- --- --- --- --- --- --- --- -- '''

            if outBike <= self.bikes.level:
                yield self.bikes.get(outBike)
            else:
                if self.bikes.level != 0:
                    outBike = self.bikes.level
                    yield self.bikes.get(outBike)
                else:
                    outBike = 0

            print("time: " + str(self.env.now))
            print(str(self.idx)+": "+str(self.bikes.level))

            # Dispatcher
            self.buf.push(outBike)
            self.going.succeed()
            self.going = self.env.event()

            # State unit time
            yield self.env.timeout(10)

    def getPosition(self):
        return self.position

    def getIndex(self):
        return self.idx

def main():
    init_samples()
    init_rewards()
    env = simpy.Environment()
    Map(env)
    BikeScheduler(env)
    env.run(until=800)

if __name__ == '__main__':
    main()