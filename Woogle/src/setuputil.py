from distutils.core import setup
import py2exe

setup(console=[ 'scanbinfile.py', 'scanxmlfile.py'], options={"py2exe":{"includes":["sip"]}})