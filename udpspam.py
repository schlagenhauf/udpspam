#!/usr/bin/env python

import click
from progress.spinner import Spinner
import csv
import numpy as np

import socket
import time
import signal
import os


@click.group()
def cli():
    pass


@click.command('spam')
@click.argument('address', default='185.82.21.12')
@click.argument('port', default=4000)
@click.option('--rate', default=1, help='Packets per second.')
@click.option('--timeout', default=1, help='Timeout in seconds.')
@click.option('--filename', default='udpspam.log', help='Timeout in seconds.')
def spam(address, port, rate, timeout, filename):
    # Error cases
    # - Cannot send package (Network not reachable)
    # - Package does not get to target / back from target
    print(address, port, rate, timeout, filename)

    spinner = Spinner('Spamming ')
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.settimeout(timeout)

    with open(filename, 'w') as file_obj:
        csv_writer = csv.writer(file_obj, delimiter=',')

        def signal_handler(signal, frame):
            file_obj.close()
            print('Quit.')
            os._exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        message_id = 0

        while True:
            payload = str(message_id).encode()
            send_time_in_secs = time.time()

            try:
                send_sock.sendto(payload, (address, port))
                send_state = 'OK'
            except RuntimeError as re:
                send_state = str(re)

            csv_writer.writerow(("out", send_time_in_secs, message_id, send_state))

            try:
                recv_data, addr = send_sock.recvfrom(int(2**16))
                recv_time_in_secs = time.time()
                recv_state = 'OK'
            except RuntimeError as re:
                recv_state = str(re)

            csv_writer.writerow(("in", recv_time_in_secs, int(recv_data.decode()), recv_state))

            message_id += 1
            spinner.next()
            time.sleep(0.01)


@click.command()
@click.option('--filename', default='udpspam.log', help='Timeout in seconds.')
def print_stats(filename):
    message_pairs = {}
    with open(filename, 'r') as file_obj:
        reader = csv.reader(file_obj, delimiter=',')
        for io, t, pl in reader:
            if io == 'out':
                if pl in message_pairs:
                    print('Sent message ID "%s" already in index. Looks like a bug' % pl)
                    continue
                message_pairs[pl] = [float(t), None]
            else:
                if pl not in message_pairs:
                    print('Received message ID "%s" not in index. Looks like a bug' % pl)
                    continue
                message_pairs[pl][1] = float(t)

    # produce stats
    delays = [v[1] - v[0] for k,v in message_pairs.items() if v[1] is not None]
    print('Delay (median/mean/stddev): %f/%f/%f' % (np.median(delays), np.mean(delays), np.std(delays)))

    dropped_packets = sum([t_recv is None for _, t_recv in message_pairs.values()])
    #print('Number of dropped packages: %i' % sum(dropped_packets))


cli.add_command(spam)
cli.add_command(print_stats)

if __name__ == '__main__':
    cli()
