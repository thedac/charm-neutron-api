import os
import subprocess
import glob
from charmhelpers.fetch import (
    apt_install,
    filter_installed_packages
)
from charmhelpers.core.host import (
    lsb_release
)
# TODO: fixup localized gnupg
import gnupg

LOCAL_ARCHIVE_ROOT = '/var/lib/local-archive'


def get_key(gpg, uid):
    ''' Retrieve existing key or generate a new one '''
    key = None
    for k in gpg.list_keys():
        for u in k['uids']:
            if uid in u:
                return k
    if not key:
        # Generate the key for use
        os.environ['USERNAME'] = 'juju'
        input_data = gpg.gen_key_input(name_email=uid)
        key = gpg.gen_key(input_data)
        return get_key(gpg, uid)


def get_host_arch():
    return subprocess.check_output(['dpkg-architecture',
                                    '-qDEB_HOST_ARCH']).strip()


def get_host_release():
    return lsb_release()['DISTRIB_CODENAME']


CONF = '''Origin: Ubuntu-Local
Label: local-archive
Suite: {suite}
Codename: {codename}
Version: 3.0
Architectures: {arch}
Components: main
Description: Juju managed local archive
SignWith: {signwith}
'''


def create_archive(name):
    gpg_dir = os.path.join(LOCAL_ARCHIVE_ROOT, 'gpg')
    if not os.path.exists(gpg_dir):
        os.makedirs(gpg_dir, 0700)
    archive_dir = os.path.join(LOCAL_ARCHIVE_ROOT, name)
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir, 0755)
    gpg = gnupg.GPG(gnupghome=os.path.join(LOCAL_ARCHIVE_ROOT, 'gpg'))
    key_email = '{}@juju.local'.format(name)
    key = get_key(gpg, key_email)
    conf_dir = os.path.join(archive_dir, 'conf')
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir, 0700)
    with open(os.path.join(conf_dir, 'distributions'), 'w') as dists:
        dists.write(CONF.format(signwith=key['keyid'][8:],
                                suite=get_host_release(),
                                codename=get_host_release(),
                                arch=get_host_arch()))
    with open(os.path.join(conf_dir, 'pub.key'), 'w') as pub_key:
        pub_key.write(gpg.export_keys(key['keyid']))


def install():
    # TODO: review use of haveged - gnupg sucks without it in
    # virtual environment
    apt_install(filter_installed_packages(['reprepro',
                                           'dpkg-dev', 'haveged']),
                fatal=True)


def include_deb(name, path):
    debs = glob.glob('{}/*.deb'.format(path))
    archive = os.path.join(LOCAL_ARCHIVE_ROOT, name)
    cmd = [
        'reprepro', '-b', archive,
        '--gnupghome', os.path.join(LOCAL_ARCHIVE_ROOT, 'gpg'),
        'includedeb', get_host_release()]
    if len(debs) > 0:
        cmd.extend(debs)
        subprocess.check_call(cmd)


SOURCE_LINE = \
    '''deb [arch={arch}] file:///var/lib/local-archive/{name} {release} main'''

PREFERENCES = '''Package: *
Pin: release o=Ubuntu-Local
Pin-Priority: {}
'''


def configure_local_source(name, priority=1000):
    with open('/etc/apt/preferences.d/50-local-archive', 'w') as pref:
        pref.write(PREFERENCES.format(priority))
    with open('/etc/apt/sources.list.d/{}.list'.format(name),
              'w') as source:
        source.write(SOURCE_LINE.format(name=name,
                                        arch=get_host_arch(),
                                        release=get_host_release()))
    conf_dir = os.path.join(LOCAL_ARCHIVE_ROOT, name, 'conf')
    subprocess.check_call(['apt-key', 'add',
                           os.path.join(conf_dir, 'pub.key')])
