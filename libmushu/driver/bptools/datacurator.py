from libmushu.driver.bptools.bptools import Receiver
from libmushu.driver.bptools.container import DataContainer



import multiprocessing

import asyncio


# f1 --> grab stuff from the receiver queue, put it into the container.
# the container class functions as the buffer. it's basically a numpy array.
async def put_into_container(container, queue_incoming):
    # make the container handle the queue item. In other words, the Receiver
    # captured some data and put it into the queue. This will use this process's
    # computational resources to make the container handle that new data
    # package.
    container.handle_queue_item(queue_incoming.get())

    # and.. yield back the control.
    await async.sleep(0.001)


# f2 --> check if there's a 'get_data' instruction in the queue, and then deal with that.
async def get_from_container(container, queue_instructions, queue_outgoing, datasent):
    # check whether there's anything in the queue.
    while queue_instructions.qsize() > 0:

        # probably can do better --> implement this in container?
        points_in_block = container.get_samples_in_block()
        # handle queue requests
        queue_item = queue_instructions.get()

        if queue_item == 'get_data':

            # this is the interaction --> a counter in container which gets updated
            nblocks = container.get_last_block() - container.get_block_position()

            if nblocks > 1:
                data = container[nblocks * points_in_block, :]

                queue_outgoing.put(data)

                # tell the other (i.e. main) process that this function has done its job.
                datasent.set()

                container.set_block_position(container.get_last_block())

    # yield back control...
    await async.sleep(0.001)


async def print_something():
    while True:
        print('test')
        await asyncio.sleep(1)


# i.e. gracefully exiting the main event loop within the Process. So we can exit/join it again.
async def kill_loop(loop, event):
    while True:
        print(event.is_set())
        if event.is_set():
            loop.stop()
        await asyncio.sleep(0.001)


        # so .. this is the loop...


def starting_up_the_loop(container, queue_incoming, queue_instructions, queue_outgoing, curatorstop, datasent):
    loop = asyncio.get_event_loop()
    loop.create_task(put_into_container(container, queue_incoming))
    loop.create_task(get_from_container(container, queue_instructions, queue_outgoing, datasent))
    loop.create_task(kill_loop(loop, curatorstop))
    loop.create_task(print_something())
    loop.run_forever()


