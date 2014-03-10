import argparse
import itertools
import subprocess
import sys
import time

from nmcli import nm, con


def build_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument(
      "-c", "--connect",
      dest='connect',
      help="Connect to a VPN network",
      action="store_true")

    parser.add_argument(
      "-r", "--auto-reconnect",
      dest='auto_reconnect',
      help="Auto Reconnect to the associated VPN ",
      action="store_false",
      default=True)

    parser.add_argument(
      "-b", "--benchmark",
      dest='benchmark',
      help="Benchmark passed in VPN servers.  If used in conjunction with -c" +
           " will attempt to connect in order of bandwidth available",
      action="store_true")

    parser.add_argument(
      "-v", "--vpn",
      dest='vpnservers',
      help="VPN server to connect to specified by NM name.  Multiple servers" +
           "are used incase the connection to the first fails",
      nargs="+")

    parser.add_argument(
      "-f", "--file",
      dest='vpnfile',
      help="File containing a newline separated list of VPN IDs to use",
      nargs="+")

    parser.add_argument(
        '-x', '--external-server',
        dest='external_server',
        help='External server to use to check connection status via ICMP',
        default='8.8.8.8')

    return parser


def get_servers(args):
    vpns = []
    if args.vpnservers:
        vpns = args.vpnservers

    if args.vpnfile:
        vpns.extend(open(args.vpnfile).read().split())

    return vpns


def server_connect(server):
    print "Connecting to %s..." % server
    try:
        con.up(id=server)
        print "Connected"
        return True
    except:
        return False


def is_nm_active(server):
    try:
        results = con.status(id=server)
    except:
        return False

    if not results:
        return False

    results = results[0]
    return (results.get('STATE') == "activated" and
            results.get('VPN-STATE') == '5 - VPN connected')


def shell(args):
    """Execute args and returns status code, stdout and stderr

    Any exceptions in running subprocess are allowed to raise to caller
    """
    process = subprocess.Popen(args, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    retcode = process.returncode

    return retcode, stdout, stderr


def loop_while_connected(vpnserver, pingserver):
    had_internet = False
    while True:
        if not is_nm_active(vpnserver):
            print 'VPN dropped on its own!'
            return had_internet

        print "Start ping to %s" % pingserver
        retcode, _, _ = shell(["ping", '-c', '2', pingserver])
        print "Ping Ret: %s" % retcode
        if retcode:
            return had_internet

        had_internet = True
        time.sleep(3)

    return had_internet


def vpn_connect(servers,
                auto_reconnect=True,
                external_server='8.8.8.8'):
    # Step 1: Try and connect
    # Step 2: Once connected, verify it works
    # Step 3: If asked to reconnect on failure, do so!
    for server in itertools.cycle(servers):
        if not is_nm_active(server):
            if not  server_connect(server):
                print "Failed server connect.  Trying another..."
                continue

        connected = is_nm_active(server)
        if connected:
            had_internet = loop_while_connected(server, external_server)

        print had_internet, auto_reconnect
        if had_internet and not auto_reconnect:
            return


if __name__ == '__main__':
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:])

    servers = get_servers(args)
    if args.benchmark:
        servers = do_benchmark(servers)

    if args.connect:
        vpn_connect(
        servers,
        auto_reconnect=args.auto_reconnect,
        external_server=args.external_server)
