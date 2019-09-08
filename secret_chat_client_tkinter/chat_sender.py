import asyncio
import sys
import argparse
import json
import os
from dotenv import load_dotenv

from services import log_to_file
from services import install_logs_parameters
from services import sanitize_message
from services import set_and_check_connection


class AutorisationError(TypeError):
    pass


def get_account_hash_and_nickname(registration_data):
    try:
        reply_json = json.loads(registration_data)
        return reply_json['account_hash'], reply_json['nickname']
    except json.decoder.JSONDecodeError:
        return None


async def register(new_name, host, port):
    hash_and_nickname = None
    attempts = 5
    reader, writer = await set_and_check_connection(host=host, port=port)
    try:
        writer.write(b'\n')
        await writer.drain()
        if await reader.readline():
            _name = str.encode(f'{new_name}\n')
            writer.write(_name)
            await writer.drain()
            await reader.readline()
            registration_data = await reader.readline()
            for attempt in range(attempts):
                hash_and_nickname = \
                    get_account_hash_and_nickname(registration_data)
                if hash_and_nickname:
                    break
        return hash_and_nickname
    except UnicodeDecodeError:
        pass
    finally:
        writer.close()


def get_args_parser():
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=formatter_class)

    parser.add_argument('-r', '--registration', action='store_true',
                        default=False, help='chat registration mode')

    parser.add_argument('-H', '--host', type=str, default=os.getenv("HOST"),
                        help='chat connection hostname')

    parser.add_argument('-P', '--port_sender', type=int,
                        default=os.getenv("PORT_SENDER"),
                        help='chat connection sender port')

    parser.add_argument('-u', '--user', type=str, default=None,
                        help='sender username')

    parser.add_argument('-t', '--token', type=str, default=os.getenv("TOKEN"),
                        help='chat autorization token')

    parser.add_argument('-m', '--msg', type=str, default=None,
                        help='single message into the chat')

    parser.add_argument('-l', '--logs', action='store_true', default=True,
                        help='set logging')
    return parser


def main():
    load_dotenv()
    parser = get_args_parser()
    args = parser.parse_args()
    install_logs_parameters(args.logs)

    try:
        if args.registration:
            coro_register = register(new_name=args.msg,
                                     host=args.host,
                                     port=args.port_sender)
            token, name = asyncio.run(coro_register)
            args.token = token
            args.user = name
            args.registration = False
            args.msg = None
            print(f'registration name is {name}, token is {token}')

        if not args.registration:
            while True:
                if not args.msg:
                    print('Input your chat message here: ')
                message = input() if not args.msg else args.msg

                if message:
                    coro_send_message = submit_message(msg=message,
                                                       host=args.host,
                                                       port=args.port_sender,
                                                       token=args.token)

                    asyncio.run(coro_send_message)
                if args.msg:
                    break  # only single argument message!

    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == '__main__':
    main()
