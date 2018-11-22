#!/usr/bin/python
# Hiu, Yen-Onn
# yenonn@gmail.com
# ssh implementation for multiple ssh client to be connected and
# issue the same commands at the same time.
# Oct 29 2013
import paramiko
import cmd
import sys
import subprocess
import socket
import re
import os
import getpass
import datetime
import time


class RunCommand(cmd.Cmd):

  """ Simple shell to run command on the host """

  prompt = 'ssh > '
  intro = "-- Welcome to ssh paramiko --"

  def __init__(self):
    cmd.Cmd.__init__(self)
    self.hosts = []
    self.connections = []

    # Setting up the credential
    #self.uid = os.getlogin()
    self.uid = ""
    while not self.uid:
      self.uid = raw_input("User: ")
    print "Connecting via [%s]" % self.uid
    self.password = ""
    while not self.password:
      self.password = getpass.getpass()

    # Setting logging file
    timestamp = datetime.datetime.fromtimestamp(
        time.time()).strftime('%Y-%m-%d-%H:%M:%S')
    self.logname = os.getcwd() + "/ssh-paramiko-" + timestamp + ".log"
    self.logfile = open(self.logname, 'a')
    self.logfile.write("Time: %s\n" % timestamp)
    self.logfile.close()

  def do_help(self, args):
    print "Usage - pyssh.py"
    print " addhost      - add host with the comma delimitter"
    print " addhostfile  - add host with a absolute path of a file"
    print " rmhost       - remove host with the comma delimitter"
    print " lshost       - list hosts"
    print " ping         - do a ping test to the added host list"
    print " connect      - establish ssh connection to the added host list"
    print " run          - run a specific command on the connected host"
    print " close        - close the ssh connect to the added host list"
    print " put          - copy files over the host"
    print " get          - get files over the host"
    print " quit         - quit the session"

  def emptyline(self):
    pass
    # print "HELP"
    # self.do_help(self)
    # return cmd.Cmd.emptyline(self)

  def do_addhost(self, args):
    """ Add the host to the host list """
    add_item_hosts = args.split(",")
    for h in add_item_hosts:
      add_item = h.strip()
      if add_item not in self.hosts:
        self.hosts.append(add_item)
      else:
        print "host is skipped: %s" % add_item
    print "host added: %s" % self.hosts

  def do_rmhost(self, args):
    """ Remove the host to the host list """
    remove_item_hosts = args.split(",")
    for h in remove_item_hosts:
      remove_item = h.strip()
      if remove_item in self.hosts:
        self.hosts.remove(remove_item)
        print "host removed: %s" % remove_item
      else:
        print "host not found: %s" % remove_item

  def do_lshost(self, args):
    """ List out the host in the host list """
    if len(self.hosts) == 0:
      print "No host is added"
    else:
      for item_host in self.hosts:
        print "host: %s " % item_host
      print "Total added hosts: %s" % len(self.hosts)

  def do_addhostfile(self, args):
    """ Add a file that connect the host list """
    hostfile = args.strip()
    if os.path.isfile(hostfile):
      try:
        file = open(hostfile, "r")
        for line in file.readlines():
          if line.strip() not in self.hosts and not line.startswith("#"):
            self.hosts.append(line.strip())
        file.close()
      except IOError as e:
        print "Unable to open file", e
    else:
      print "file is not found, %s" % hostfile

  def do_ping(self, args):
    """ Ping the hosts in the host list """
    if len(self.hosts) == 0:
      print "No host is added"
    else:
      for ping_item in self.hosts:
        ping_command = ["ping", "-c", "1", ping_item]
        p = subprocess.Popen(
            ping_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        result = p.communicate()
        replyok = "0% packet loss"
        match = re.compile(replyok)
        if match.search(result[0]):
          print "host %s PING OK" % (ping_item)
        else:
          print "host %s PING FAILED" % (ping_item)
          self.do_rmhost(ping_item)

      print "Total pingable hosts: %s" % (len(self.hosts))

  def do_connect(self, args):
    """ Connect to all hosts in the host list """
    for host in self.hosts:
      try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=self.uid, password=self.password)
        self.connections.append(client)
        print "Connected host: %s" % host
      except socket.error as e:
        print "Failed on %s: socket connection failed" % host, e
        self.do_rmhost(host)
      except paramiko.SSHException as e:
        print "Failed on %s: password is invalid" % host, e
        self.do_rmhost(host)
      except paramiko.AuthenticationException as e:
        print "Authentication failed for some reason on %s:" % host, e
        self.do_rmhost(host)
    print "Total connected hosts: %s out of %s" % (len(self.connections), len(self.hosts))

  def do_run(self, command):
    """ run/execute command on all the host in the list """
    if command:
      self.logfile = open(self.logname, "a")
      self.logfile.write("Input: %s\n" % command)
      for host, conn in zip(self.hosts, self.connections):
        print "host: %s" % host
        self.logfile.write("host: %s\n" % host)

        stdin, stdout, stderr = conn.exec_command(command)
        stdin.close()

        for line in stdout.read().splitlines():
          print "\t%s" % (line)
          self.logfile.write("\t" + line + "\n")

        for line in stderr.read().splitlines():
          print "[Error]: %s" % (line)
          self.logfile.write("[Error]:\t" + line + "\n")
      self.logfile.close()
    else:
      print "usage: run"

  def do_close(self, args):
    for conn in self.connections:
      conn.close()
    self.connections = []

  def do_EOF(self, args):
    self.do_quit(self)

  def do_quit(self, args):
    self.do_close(self)
    self.hosts = []
    sys.exit(0)

  def do_put(self, args):
    """ Put a file onto the targeted host"""
    local_path = args.strip()
    if not os.access(local_path, os.R_OK):
      print "Read permission is denied on file, {}".format(local_path)
      return
    if not os.path.isfile(local_path):
      print "File is not found: {}".format(local_path)
      return

    remote_path = None
    if not remote_path:
      remote_path = os.path.split(local_path)[1]

    if self.connections:
      self.logfile = open(self.logname, "a")
      for host, conn in zip(self.hosts, self.connections):
        try:
          print "host: {}".format(host)
          self.logfile.write("host: {}\n".format(host))
          sftp = paramiko.SFTPClient.from_transport(conn)
          sftp.put(local_path, remote_path)
          print "File is copied to {}@{}:~/{}".format(self.uid, host, remote_path)
          self.logfile.write("File is copied to {}@{}:~/{}".format(self.uid, host, remote_path))
        except Exception as err:
          print "Error: {}".format(err)
          self.logfile.close()
        else:
          print "No connection is made"

  def do_get(self, args):
    """ Get a file from the targeted host"""
    remote_path = args.strip()
    remote_file_name = remote_path.split("/")[-1]
    local_path = "/tmp/"
    if self.connections:
      self.logfile = open(self.logname, "a")
      for host, conn in zip(self.hosts, self.connections):
        try:
          print "host: {}".format(host)
          sftp = paramiko.SFTPClient.from_transport(conn)
          local_file = local_path + remote_file_name + "." + host + ".out"
          sftp.get(remote_path, local_file)
          print "file: {} is copied to local FS: {}".format(remote_path, local_file)
          os.chmod(local_file, 644)
        except Exception as err:
          print "Error: {}".format(err)
          self.logfile.close()
        else:
          print "No connection is made"


if __name__ == '__main__':
  RunCommand().cmdloop()
