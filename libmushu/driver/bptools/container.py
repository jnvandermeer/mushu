'''

I'd like to make a container class. The container should just be based on
a numpy array.

The Container is EEG data - so there should be some header info as well as
data info

It should have some methods to allow for communication (Possibly using
multithreading cues)

It should have some automated methods, called whenever something happens

For now... it should just accept stuff from a Process
The Process will be called 'ReadInputStream', and it should read BVA amp.


This is a very special type of container, in that the most recent data points..
ALWAYS come first!
it also monitors block.. and if it's something other than from memory..
it'll fix it.


This is the fast implementation of the Container class.

'''

import numpy as np


# I should process this, somehow: (channelCount, samplingInterval, resolutions, channelNames)
# samplingInterval is the time between 2 samples - in MICROSEC
# resolutions - obvious - 0.5 microvolts
# channelNames - need to fix
# channelcount - # of channels, which is 64 - for now. For me it'd be 72.

# points = always 20000 / samplingInterval
# srate = 1000000/samplingInterval

class DataContainer(object):
    # i made several other functions... but in this case, I guess it makes sense
    # to process header info and do all initializations forst.
    # then I can collect data from here on out.
    def __init__(self, maxlength_in_seconds=100):

        self.pass_data_initialized = False
        self.maxlength_in_seconds = maxlength_in_seconds
        self.maxlength = 0
        self.lastblock = 0
        self.firstblock = 0
        self.blockposition = 0

    # resolve all the passing of stuff. This will call pass_hdr and pass_data.
    def handle_queue_item(self, queue_item):

        if 'hdr' in queue_item.keys():
            self.pass_hdr(queue_item['hdr'])
        if 'd' in queue_item.keys():
            # print queue_item['block']
            self.pass_data(queue_item['d'], queue_item['markers'], queue_item['block'])

    # @profile
    def pass_hdr(self, hdr):

        # the header divulges NCHAN, etc etc.
        self.hdr = hdr

        # hdr.keys()
        # Out[5]: ['samplingInterval', 'channelCount', 'resolutions', 'channelNames']

        # do stuff...
        # calculate how many data points, pls. we want to have maxlength_in_seconds
        # data points. How many data points within 1 second?
        # samplingInterval is given in microseconds... if needed we may need
        # to move this somewhere lese
        maxlength = int(self.maxlength_in_seconds * 1000000 / hdr['samplingInterval']);
        self.maxlength = maxlength

        # so we'll use m as our data matrix. But it's not a data MATRIX object
        # it's an NDarray object in numpy. So we don't get confused. ....
        # this is CRUCIAL - increase allocated memory matrix by factor of 2.
        m = np.empty((maxlength * 2, hdr['channelCount']))
        self.m = m

        self.missedblocks = []
        self.receivedblocks = []

        # this is the critical part, counting where we are in the matrix.
        self.middle_matrix_pos = self.maxlength

    # @profile
    def pass_data(self, data, markers, block):

        # get a sense of how many data points there are?
        # I don't need to do this for each function call - once it's set it should
        # remain the same.
        # not ideal situation ,but... the header doesn't tell me how big each data
        # chunk is.
        if self.pass_data_initialized == False:
            # make sure not to call this again. This is further initialialization
            # that you can only do once you've already got some data sent.
            self.pass_data_initialized = True

            # this is what we needed
            self.points = data.shape[0]

            # another essential of our fast matrix operation.
            self.internal_matrix_pos = self.middle_matrix_pos

            # define what happens when we might need to append some zeros
            self.zerodata = np.zeros((self.points, self.hdr['channelCount']))

            # or not-a-number
            self.nandata = self.zerodata * np.nan

            self.maxblocks_in_matrix = round(self.maxlength / self.points)
            # speed optimization - prevent recreating the array each and every time
            # so make the big data container HERE. And many sure its memory never changes.
            # self.m=np.zeros(self.maxlength,self.hdr['channelCount'])
            # big data matrix is already initialized.

            # to keep track of last blocks --> we start with the # of the first data pass-over.
            self.firstblock = block
            self.lastblock = block
            self.blockposition = block

            print('Initialized and Starting Data Collection')

        # check our blocks, pls?
        # this is our own internal block counter.

        # fix the blocks - revised
        while self.lastblock + 1 < block:
            # log the missing block, pls?
            # self.m = np.concatenate((self.nandata,self.m))
            # so instead of cocatenation, we will reshuffle our array.
            self.append(self.zerodata)  # to make confusion --> missedblocks is a list.
            self.missedblocks.append(self.lastblock)
            # self.lastblock += 1  do NOT do this here --> append will take care of it.

        # using magic Append function, now
        self.append(data)
        self.receivedblocks.append(block)
        # add the matrix here.
        # do latest first (slicing operation)

        # speed = don't create a new array. So copy downwards again:
        # so this is now critical.

        # this needs to radically change.
        # we'd need an INTERNAL counter of where we are, know how many blocks
        # would fit into the matrix, etc.

    def append(self, data):

        # print(t)
        # might be a memory leak - use another notation: m[::-1] = should be same
        # speed.
        # data=np.flipud(data)

        # assign once, at the MIDDLE through the BEGINNING
        self.internal_matrix_pos -= self.points
        b = self.internal_matrix_pos
        e = b + self.points
        self.m[b:e, :] = data[::-1]  # last ones go first

        # the SAME - at the END through the MIDDLE
        b += self.middle_matrix_pos
        e += self.middle_matrix_pos
        self.m[b:e, :] = data[::-1]

        if self.internal_matrix_pos == 0:
            # this is the crucial part - here we reverse positions in the matrix
            # and so make sure that all indexing from internal_matrix_pos onwards
            # are the MOST RECENT 100 or 25 seconds of data, sorted LAST ARRIVED
            # FIRST INDEXED.
            self.internal_matrix_pos = self.middle_matrix_pos
            print('FLIPPING/GOING THE THE MIDDLE AGAIN')

        self.lastblock += 1

        # self.m[self.internal_matrix_pos:self.internal_matrix_pos+self.points]=np.flipud(data)

        # self.m[self.points:,:]=self.m[:-self.points,:]

        # self.m[:self.points,:]=np.flipud(data)


        # self.m = np.concatenate((np.flipud(data),self.m))
        #
        # we now don't ever have to do this!!!! - yay.
        # if self.m.shape[0] > self.maxlength:
        #    # get rid of the tail..., by re-assigning to this...
        #    # alternative... np.delete(m,[0,1],axis=0)
        #    self.m = self.m[:self.maxlength,]

    #  the following two functions assume that data is received through UDP/TCP/IP
    #  in blocks of a certain length.
    def get_last_block(self):
        # these two functions will help tremendously with housekeeping of the data.
        return self.lastblock

    def get_first_block(self):
        # these two functions will help tremendously with housekeeping of the data.
        return self.firstblock

    #    ' we make sure that now, we can slice the object any which way.
    #    def __getitem__(self, given):
    #        if isinstance(given, slice):
    #            # do your handling for a slice object:
    #            print(given.start, given.stop, given.step)
    #        else:
    #            # Do your handling for a plain index
    #            print(given)
    #

    def set_block_position(self,pos):
        self.blockposition=pos

    def get_block_position(self):
        return self.blockposition

    def get_samples_in_block(self):
        return self.points

    def __getitem__(self, *args, **kwargs):

        print('args:')
        print(*args)
        print('kwargs')
        print(**kwargs)
        # print(args[0])
        # print(args[1])
        # args = *args
        # print(args[0][0])

        # Determine first argument - if it's a tuple, get the first one
        # otherwise just take the args.
        if isinstance(args[0], tuple):
            firstarg = args[0][0]
        elif isinstance(args[0], slice):
            firstarg = args[0]
        elif isinstance(args[0], int):
            firstarg = args[0]

        print('firstarg:')
        print(type(firstarg))
        print(firstarg)

        # return args

        if isinstance(firstarg, int):
            newval = self.internal_matrix_pos + firstarg

            # replacefirst argument - int!
            if firstarg > self.maxlength:
                raise Exception('Error: indexing exceeds max defined data length!')

                # replace with new number
            newval = firstarg + self.internal_matrix_pos



        elif isinstance(firstarg, slice):
            # newslice=slice(None) # init a new slice?

            # negative numbers, pls??

            # handle the start of the indexing
            if firstarg.start == None:
                newslice_start = self.internal_matrix_pos
            else:
                newslice_start = firstarg.start + self.internal_matrix_pos

            # handle the stop of the indexing
            if firstarg.stop == None:
                newslice_stop = self.internal_matrix_pos + self.maxlength
            else:
                # saveguard, usually never happens tho. Requires < 1micros of comp time.
                if firstarg.stop > self.maxlength:
                    raise Exception('Error: indexing exceeds max defined data length!')

                if firstarg.stop >= 0:
                    newslice_stop = firstarg.stop + self.internal_matrix_pos
                else:
                    newslice_stop = self.internal_matrix_pos + self.maxlength + firstarg.stop

            # step remains unchanged
            newslice_step = firstarg.step

            # define newslice for me..
            newslice = slice(newslice_start, newslice_stop, newslice_step)

        # now return some things... using same logic as before...
        if isinstance(*args, tuple):
            return self.m.__getitem__((newslice, args[0][1]), **kwargs)
        elif isinstance(*args, slice):
            return self.m.__getitem__(newslice, **kwargs)
        elif isinstance(*args, int):
            return self.m.__getitem__(newval, **kwargs)


            #
            #
            #
            #        if len(*args) == 0:
            #            return self.m.__getitem__(**kwargs)
            #        elif len(*args) == 1:
            #            return self.m.__getitem__(newval,**kwargs)
            #        elif len(*args) == 2:
            #            return self.m.__getitem__(newslice,*args[1],**kwargs)

            # [self[ii] for ii in xrange(*key.indices(m+1))]

            # elif isinstance( key, int ) :
            #   return self.m.
            # Handle int indices

# def __getitem__(self, index):
#    if isinstance(index, int):
#        # ...    # process index as an integer
#        return c.m[index,]
#
#
#    elif isinstance(index, slice):
#        start, stop, step = index.indices(len(self))    # index is a slice
#        ...    # process slice
#    else:
#        raise TypeError("index must be int or slice")

