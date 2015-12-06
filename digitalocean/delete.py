#!/usr/bin/env python3

import argparse
import digitalocean


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--token',
                        action='store',
                        dest='token',
                        required=True)

    parser_results = parser.parse_args()
    token = parser_results.token

    manager = digitalocean.Manager(token=token)
    my_droplets = manager.get_all_droplets()
    for droplet in my_droplets:
        print(droplet.destroy())


if __name__ == '__main__':
    exit(main())
