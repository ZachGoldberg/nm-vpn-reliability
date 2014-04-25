import argparse
import itertools
import random
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
      help="File containing a newline separated list of VPN IDs to use")

    parser.add_argument(
        '-x', '--external-server',
        dest='external_server',
        help='External server to use to check connection status via ICMP',
        default='8.8.8.8')

    parser.add_argument(
        '-q', '--random',
        dest='random',
        help='Use servers in a random order.  Ignored with --benchmark.',
        action='store_true')

    return parser


def get_servers(args):
    vpns = []
    if args.vpnservers:
        vpns = args.vpnservers

    if args.vpnfile:
        vpns.extend(open(args.vpnfile).readlines())
        vpns = [v.strip() for v in vpns]

    return vpns


def server_connect(server):
    print "Connecting to %s..." % server
    for _ in range(1, 3):
        try:
            con.up(id=server)
            # Ensure everything settles
            time.sleep(3)
            print "Connected to %s" % server
            return True
        except:
            import traceback
            traceback.print_exc()
            print "Connection to %s Failed!" % server
            time.sleep(1)
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


def ping_ok(pingserver):
    retcode, _, _ = shell(["ping", '-c', '2', pingserver])
    return not bool(retcode)


def loop_while_connected(vpnserver, pingserver):
    had_internet = False
    print "Start connection loop..."
    while True:
        if not is_nm_active(vpnserver):
            print 'VPN dropped on its own!'
            return had_internet

        if not ping_ok(pingserver):
            print "Ping failed"
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
        connected = is_nm_active(server)
        if not connected:
            if not server_connect(server):
                print "Failed server connect.  Trying another..."
                continue

        had_internet = loop_while_connected(server, external_server)

        print "Internet lost.  Had internet: %s, Auto reconnect: %s" % (
            had_internet, auto_reconnect)
        if had_internet and not auto_reconnect:
            return


def get_current_speed():
    try:
        retcode, stdout, stderr = shell(
            ["python", "speedtest_cli.py", "--simple"])
        data = stdout.split("\n")
        # ping = data[0].split(" ")[1]
        dl = data[1].split(" ")[1]
        ul = data[2].split(" ")[1]
        return dl, ul
    except:
        return 0, 0


def kill_vpns():
    status = con.status()
    for connection in status:
        if connection['VPN'] == 'yes':
            print "Disconnecting from %s" % connection['NAME']
            con.down(id=connection['NAME'])


def do_benchmark(vpnservers, pingserver):
    server_speed = {}
    for server in vpnservers:
        kill_vpns()

        if not server_connect(server):
            continue

        if not ping_ok(pingserver):
            continue

        print "Testing %s..." % server
        dl_speed, ul_speed = get_current_speed()

        if is_nm_active(server):
            print "%s: %s Mb/s, %s Mb/s" % (server, dl_speed, ul_speed)
            server_speed[server] = (dl_speed, ul_speed)
        else:
            print "VPN Failed during speedtest, ignoring results"

    print server_speed
    return sorted(server_speed, key=lambda x: x[1])


if __name__ == '__main__':
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:])

    servers = get_servers(args)

    if args.random:
        random.shuffle(servers)

    print servers
    if args.benchmark:
        # Kill any current VPNs
        kill_vpns()
        print "Beginning benchmark"
        servers = do_benchmark(servers,
                               args.external_server)

    print servers
    if args.connect:
        vpn_connect(
        servers,
        auto_reconnect=args.auto_reconnect,
        external_server=args.external_server)
