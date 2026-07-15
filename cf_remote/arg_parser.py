def parse_info(sp):
    sp.add_argument(
        "--hosts", "-H", help="Which hosts to get info for", type=str, required=True
    )
    return sp


def parse_install(sp):
    sp.add_argument(
        "--edition",
        "-E",
        choices=["community", "enterprise"],
        help="Enterprise or community packages",
        type=str,
    )
    sp.add_argument(
        "--package", help="Local path to package or URL to download", type=str
    )
    sp.add_argument(
        "--hub-package",
        help="Local path to package or URL to download for --hub",
        type=str,
    )
    sp.add_argument(
        "--client-package",
        help="Local path to package or URL to download for --clients",
        type=str,
    )
    sp.add_argument("--bootstrap", "-B", help="cf-agent --bootstrap argument", type=str)
    sp.add_argument("--clients", "-c", help="Where to install client package", type=str)
    sp.add_argument("--hub", help="Where to install hub package", type=str)
    sp.add_argument(
        "--demo",
        help="Use defaults to make demos smoother (NOT secure)",
        action="store_true",
    )
    sp.add_argument(
        "--call-collect",
        help="Enable call collect in --demo def.json",
        action="store_true",
    )
    sp.add_argument(
        "--remote-download",
        help="Package will be downloaded directly to the target machine",
        action="store_true",
    )
    sp.add_argument(
        "--trust-keys",
        help="Comma-separated list of paths to keys hosts should trust"
        + " (implies '--trust-server no' when boostraping)",
        type=str,
    )
    sp.add_argument(
        "--insecure",
        help="Ignore mismatching checksums when downloading urls",
        action="store_true",
    )
    return sp


def parse_uninstall(sp):
    sp.add_argument("--purge", help="Complete uninstallation", action="store_true")
    sp.add_argument("--clients", "-c", help="Where to uninstall", type=str)
    sp.add_argument("--hub", help="Where to uninstall", type=str)
    sp.add_argument("--hosts", "-H", help="Where to uninstall", type=str)
    return sp


def parse_packages(sp):
    sp.add_argument(
        "--edition",
        "-E",
        choices=["community", "enterprise"],
        help="Enterprise or community packages",
        type=str,
    )
    sp.add_argument("tags", metavar="TAG", nargs="*")
    return sp


def parse_list(sp):
    sp = parse_packages(sp)
    sp.add_argument(
        "--allow-expired", help="Also lists expired packages", action="store_true"
    )
    return sp


def parse_download(sp):
    sp = parse_list(sp)
    sp.add_argument("--output-dir", "-o", help="Where to download", type=str)
    sp.add_argument(
        "--insecure",
        help="Ignore mismatching checksums when downloading urls",
        action="store_true",
    )
    return sp


def parse_run(sp):
    sp.add_argument(
        "--hosts",
        "-H",
        help="Which hosts to run the command on",
        type=str,
        required=True,
    )
    sp.add_argument(
        "--raw", help="Print only output of command itself", action="store_true"
    )
    sp.add_argument(
        "remote_command",
        help="Command to execute on remote host (including args)",
        type=str,
        nargs=1,
    )
    return sp


def parse_sudo(sp):
    return parse_run(sp)


def parse_save(sp):
    sp.add_argument(
        "--role",
        help="Role of the hosts",
        choices=["hub", "hubs", "client", "clients"],
        required=True,
    )
    sp.add_argument(
        "--name",
        help="Name of the group of hosts (can be used in other commands)",
        required=True,
    )
    sp.add_argument(
        "--hosts",
        "-H",
        help="SSH usernames and IPs for SSH and CFEngine in the form of user@ip",
        required=True,
    )
    return sp


def parse_scp(sp):
    sp.add_argument(
        "--hosts", "-H", help="Which hosts to copy the file to", type=str, required=True
    )
    sp.add_argument("args", help="Arguments", type=str, nargs="*")
    return sp


def parse_spawn(sp):
    sp.add_argument(
        "--list-platforms", help="List supported platforms", action="store_true"
    )
    sp.add_argument(
        "--list-boxes", help="List installed vagrant boxes", action="store_true"
    )
    sp.add_argument(
        "--init-config",
        help="Initialize configuration file for spawn functionality",
        action="store_true",
    )
    sp.add_argument("--platform", help="Platform or vagrant box to use", type=str)
    sp.add_argument("--count", default=1, help="How many hosts to spawn", type=int)
    sp.add_argument(
        "--role", help="Role of the hosts", choices=["hub", "hubs", "client", "clients"]
    )
    sp.add_argument(
        "--name", help="Name of the group of hosts (can be used in other commands)"
    )
    sp.add_argument(
        "--append",
        help="Append the new VMs to a pre-existing group",
        action="store_true",
    )
    sp.add_argument(
        "--provider",
        help="VM provider",
        type=str,
        default="aws",
        choices=["aws", "gcp", "vagrant"],
    )
    sp.add_argument("--cpus", help="Number of CPUs of the vagrant instances", type=int)
    sp.add_argument(
        "--sync-folder",
        help="Root folder of synchronized folders of vagrant instance",
        type=str,
    )
    sp.add_argument(
        "--provision",
        help="full path to provision shell script for Vagrant VM",
        type=str,
    )
    sp.add_argument("--size", help="Size/type of the instances", type=str)
    sp.add_argument(
        "--network", help="network/subnet to assign the VMs to (GCP only)", type=str
    )
    sp.add_argument(
        "--no-public-ip",
        help="No public IP needed (GCP only; WARNING: The VMs will only be accessible"
        + " from some other VM in the same cloud/network!)",
        action="store_true",
    )
    # TODO: --region (optional)
    return sp


def parse_show(sp):

    sp = sp.add_argument(
        "--ansible-inventory",
        help="Print Ansible inventory with spawned hosts",
        action="store_true",
    )

    return sp


def parse_destroy(sp):
    sp.add_argument(
        "--all", help="Destroy all hosts spawned in the clouds", action="store_true"
    )
    sp.add_argument("name", help="Name of the group of hosts to destroy", nargs="?")
    return sp


def parse_deploy(sp):
    sp.add_argument("--hub", help="Hub(s) to deploy to", type=str)
    sp.add_argument(
        "masterfiles",
        help="Policy-set location (tarball URL or local path to tarball / directory)",
        type=str,
        nargs="?",
    )
    return sp


def parse_agent(sp):
    sp.add_argument(
        "--hosts",
        "-H",
        help="Which hosts to run cf-agent from",
        type=str,
        required=True,
    )
    sp.add_argument("--bootstrap", "-B", help="Which hub to bootstrap to", type=str)
    return sp


def parse_connect(sp):
    sp.add_argument(
        "--hosts", "-H", help="Host to open the shell on", type=str, required=True
    )
    return sp
