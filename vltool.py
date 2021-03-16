from paramiko import SSHClient, AutoAddPolicy
import argparse
import yaml
import pathlib


def load_config():
    path = str(pathlib.Path(__file__).parent.absolute()) + "/config.yml"
    return yaml.safe_load(open(path))


def remote_drush(target, commands, sites, base_dir, drush, user, host, password, verbose):
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password)
    except Exception:
        print("Cant connect :(")
        exit(6)

    for site in sites:
        for command in commands:
            chan = client.get_transport().open_session()
            chan.exec_command("cd " + base_dir + site + "; " + drush + " " + command)
            print(target + "$> drush " + command + " [" + site + "] -> ", end="")
            if chan.recv_exit_status() == 0:
                print("ok")
                if verbose:
                    # TODO: Dosent work now, investigate.
                    stdout = chan.makefile('rb', -1)
                    for line in stdout.read().splitlines():
                        print(line)
            else:
                print("ERROR")
                print(chan.recv_stderr(4096).decode('ascii'))

    client.close()


def get_args(domains):
    if domains is None:
        print("No damain settings")
        exit(1)

    params = dict()

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--target', help='Target environment [stage|prod]', default="stage")
    parser.add_argument('-v', '--verbose', help='Show full output', action='store_true')
    parser.add_argument('-s', '--site', action='append', help='Target domains [co.uk|de|fr|...], if not specified all will be used')
    parser.add_argument('commands', nargs='*', default="cc all")

    args = parser.parse_args()
    params['verbose'] = args.verbose
    params['target'] = args.target

    if type(args.commands) is str:
        params['commands'] = [args.commands]
    elif type(args.commands) is list:
        params['commands'] = args.commands

    if type(args.site) is str:
        if not (domains.get('aliases') is None or domains.get('aliases').get(args.site) is None):
            params['sites'] = list(domains['aliases'][args.site])
    elif type(args.site) is list:
        params['sites'] = [domains['aliases'][site] for site in args.site if not (domains.get('aliases') is None or domains['aliases'].get(site) is None)]
    else:
        params['sites'] = domains['sites']

    if params['sites'] is None or len(params) == 0:
        print("No damain settings")
        exit(2)

    return params


if __name__ == "__main__":
    config = load_config()
    args = get_args(config.get('domains'))
    if config.get('system') is None or \
       config['system'].get('targets') is None or \
       config['system']['targets'].get(args['target']) is None:
        print("No target settings")
        exit(3)
    args['base_dir'] = config['system']['targets'][args['target']]

    if config.get('system') is None or \
       config['system'].get('drush') is None:
        print("No drush settings")
        exit(4)
    args['drush'] = config['system']['drush']

    if config.get('connection') is None or \
       config['connection'].get('host') is None or \
       config['connection'].get('user') is None:
        print("No credential settings")
        exit(5)

    args['host'] = config['connection']['host']
    args['user'] = config['connection']['user']
    args['password'] = config['connection'].get('password')

    remote_drush(**args)
