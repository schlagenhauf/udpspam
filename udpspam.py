#!/usr/bin/env python

import click
from progress.spinner import PixelSpinner
import logging
import signal
import trio

logging.basicConfig(filename='udpspam.log',
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)


async def send(address, port, rate):
    message_id = 0
    sock = trio.socket.socket(trio.socket.AF_INET,  # Internet
                              trio.socket.SOCK_DGRAM)  # UDP

    while True:
        payload = str(message_id).encode()
        await sock.sendto(payload, (address, port))
        message_id += 1
        await trio.sleep(1/rate)
        logger.info(f'Sent message: {message_id}, to: {address}:{port}')


async def receive(address, port):
    sock = trio.socket.socket(trio.socket.AF_INET,  # Internet
                              trio.socket.SOCK_DGRAM)  # UDP
    await sock.bind((address, port))

    while True:
        data, address = await sock.recvfrom(2048)  # buffer size is 1024 bytes
        logger.info(f'Received message: {data.decode()}, from: {address[0]}:{address[1]}')


async def bounce(address, destport, recvport):
    sock = trio.socket.socket(trio.socket.AF_INET,  # Internet
                              trio.socket.SOCK_DGRAM)  # UDP
    await sock.bind((address, destport))

    while True:
        recv_data, recv_addr = await sock.recvfrom(int(2**16))
        #print(f'Received {recv_data.decode()} from {recv_addr}')
        logger.info(f'Received message: {recv_data.decode()}, from: {recv_addr[0]}:{recv_addr[1]}'
                    f' at {address}:{destport}. Sending back to: {recv_addr[0]}:{recvport}')
        await sock.sendto(recv_data, (recv_addr[0], recvport))


async def spin(title):
    spinner = PixelSpinner(title)
    while True:
        spinner.next()
        await trio.sleep(0.1)


@click.group()
def cli():
    pass


@click.command('spam')
@click.argument('address', default='localhost')
@click.argument('destport', default=40000)
@click.argument('recvport', default=40001)
@click.option('--rate', default=1.0, help='Packets per second.')
def spam_cmd(address, destport, recvport, rate):
    print(f'Destination: {address}:{recvport}')
    print(f'This:        {"localhost"}:{destport}')

    fh = logging.FileHandler('spam.log')
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    async def trio_main():

        async with trio.open_nursery() as nursery:
            nursery.start_soon(send, address, recvport, rate)
            nursery.start_soon(receive, "localhost", destport)
            nursery.start_soon(spin, 'Spamming ')

            with trio.open_signal_receiver(signal.SIGINT) as signal_aiter:
                async for signum in signal_aiter:
                    assert signum == signal.SIGINT
                    nursery.cancel_scope.cancel()

    trio.run(trio_main)


@click.command('bounce')
@click.argument('address', default='localhost')
@click.argument('destport', default=40001)
@click.argument('recvport', default=40000)
def bounce_cmd(address, destport, recvport):
    print(f'Destination: {address}:{recvport}')
    print(f'This:        {"localhost"}:{destport}')

    async def trio_main():

        async with trio.open_nursery() as nursery:
            nursery.start_soon(bounce, address, destport, recvport)
            nursery.start_soon(spin, 'Bouncing ')

            with trio.open_signal_receiver(signal.SIGINT) as signal_aiter:
                async for signum in signal_aiter:
                    assert signum == signal.SIGINT
                    nursery.cancel_scope.cancel()

    trio.run(trio_main)


cli.add_command(spam_cmd)
cli.add_command(bounce_cmd)

if __name__ == '__main__':
    cli()
