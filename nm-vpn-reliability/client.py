import argparse
import itertools
import sys

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
    result = con.up(id=server)
    import pdb; pdb.set_trace()


def vpn_connect(servers,
                auto_reconnect=True,
                external_server='8.8.8.8'):
    # Step 1: Try and connect
    # Step 2: Once connected, verify it works
    # Step 3: If asked to reconnect on failure, do so!
    for server in itertools.cycle(servers):
        connected = server_connect(server)


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
