#!/usr/bin/env python3
# Hiu, Yen-Onn
# yenonn@gmail.com
# WARNING!
#!!!!!!!!!!!BE CAREFUL WHEN YOU ARE USING THIS!!!!!!!!!!!!!!!!!
# ssh implementation to allow multiple ssh connections at one time. It allows you
# to prompt commands at one time recursively to all of the connected ssh clients.
# So, it means that you have to be *very* aware of the commands that you put in.
# otherwise, it will be a disasterous impact.
#!!!!!!!!!!!BE CAREFUL WHEN YOU ARE USING THIS!!!!!!!!!!!!!!!!!
# WARNING!
# Oct 29 2013
import paramiko
import cmd
import sys
import subprocess
import socket
import os
import getpass
import datetime
import time


class PrintLog():
  def __init__(self):
    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d-%H:%M:%S')
    self.logname = os.getcwd() + "/ssh-paramiko-" + timestamp + ".log"
    with open(self.logname, 'a') as file:
      file.write(f"Time: {timestamp}\n")

  def print(self, message):
    print(f"{message}")
    with open(self.logname, 'a') as file:
      file.write(f"{message}\n")

  def warn(self, message):
    print(f"WARN: {message}")
    with open(self.logname, 'a') as file:
      file.write(f"WARN: {message}\n")


class RunCommand(cmd.Cmd):
  """ Simple shell to run command on the host """
  prompt = "ssh > "
  intro = "-- Welcome to ssh paramiko, be careful of your commands --"

  def __init__(self):
    cmd.Cmd.__init__(self)
    self.hosts = []
    self.connections = []
    self.port = 22
    self.uid = ""
    while not self.uid:
      self.uid = input("login as: ").strip()
    else:
      self.password = ""
      while not self.password:
        self.password = getpass.getpass()
    self.log = PrintLog()

  def do_help(self, args):
    print("Usage - pyssh.py")
    print("======================================================================")
    print(" addhost      - add host with the comma delimitter")
    print(" addhostfile  - add host with a absolute path of a file")
    print(" rmhost       - remove host with the comma delimitter")
    print(" lshost       - list hosts")
    print("----------------------------------------------------------------------")
    print(" ping         - do a ping test to the added host list")
    print("----------------------------------------------------------------------")
    print(" connect      - establish ssh connection to the added host list")
    print(" run          - run a specific command on the connected host")
    print(" sudorun      - run a specific command on the connected host with privileges account")
    print(" put          - put a file onto the connected host")
    print(" get          - get a file from connected hosts")
    print("----------------------------------------------------------------------")
    print(" close        - close the ssh connect to the added host list")
    print(" exit         - exit the session")
    print("=====================================================================")

  def emptyline(self):
    pass

  def do_addhost(self, args):
    """ Add the host to the host list """
    add_item_hosts = args.split(",")
    for h in add_item_hosts:
      add_item = args.strip()
      if add_item and add_item not in self.hosts:
        self.hosts.append(add_item)
      else:
        self.log.warn(f"host is skipped: {add_time}")
    self.log.print(f"host is added: {self.hosts}")

  def do_rmhost(self, args):
    """ Remove the host to the host list """
    remove_host = args.strip()
    if remove_host and remove_host in self.hosts:
      self.hosts.remove(remove_host)
      self.log.warn(f"host is removed: {remove_host}")
    else:
      self.log.warn("host is not found.")

  def do_lshost(self, args):
    """ List out the host in the host list """
    if len(self.hosts) == 0:
      print("No hosts(s) is added")
    else:
      for item_host in self.hosts:
        print(f"host: {item_host}")
      print(f"* Total added hosts: {self.hosts}")

  def do_addhostfile(self, args):
    """ Add a file that connect the host list """
    hostfile = args.strip()
    if os.path.isfile(hostfile):
      try:
        file = open(hostfile, "r")
        for line in file.readlines():
          line = line.strip()
          if line not in self.hosts and len(line) and "#" not in line:
            self.hosts.append(line)
        file.close()
      except IOError as io_error:
        self.log.warn(f"Unable to open file {io_error}")
    else:
      self.log.warn(f"file is not found, {hostfile}")

  def do_ping(self, args):
    """ Ping the hosts in the host list """
    if len(self.hosts) == 0:
      print("No host(s) is added")
      return
    else:
      removehost = []
      for ping_item in self.hosts:
        ping_command = f"ping -c 2 {ping_item}"
        result = subprocess.getoutput(ping_command)
        if "2 packets received" in result:
          self.log.print(f"host: {ping_item} - PING OK")
        else:
          self.log.warn(f"host: {ping_item} - PING FAILED")
          removehost.append(ping_item)
      # calculate pingable hosts
      total_pingable_host = len(self.hosts) - len(removehost)
      # removing all the unpingable hosts
      for remove_item in removehost:
        self.do_rmhost(remove_item)
    print(f"* Total pingable hosts: {total_pingable_host}")

  def do_put(self, args):
    """ Put a file onto the targeted host"""
    local_path = args.strip()
    if not os.access(local_path, os.R_OK):
      self.log.warn(f"Read permission is denied on file, {local_path}")
      return
    if not os.path.isfile(local_path):
      self.log.warn(f"File is not found: {local_path}")
      return
    remote_path = None
    if not remote_path:
      remote_path = os.path.split(local_path)[1]
    if self.connections:
      for host, conn in zip(self.hosts, self.connections):
        try:
          self.log.print(f"host: {host}")
          sftp = paramiko.SFTPClient.from_transport(conn)
          sftp.put(local_path, remote_path)
          self.log.print(f"File is copied to {self.uid}@{host}:~/{remote_path}")
        except Exception as err:
          print(f"Error: {err}")
    else:
      self.log.warn("No connection is made")

  def do_get(self, args):
    """ Get a file from the targeted host"""
    remote_path = args.strip()
    remote_file_name = remote_path.split("/")[-1]
    local_path = "/tmp/"
    if self.connections:
      for host, conn in zip(self.hosts, self.connections):
        try:
          print(f"host: {host}")
          sftp = paramiko.SFTPClient.from_transport(conn)
          local_file = local_path + remote_file_name + "." + host + ".out"
          sftp.get(remote_path, local_file)
          self.log.print(f"file: {remote_path} is copied to local FS: {local_file}")
          os.chmod(local_file, 644)
        except Exception as err:
          print(f"Error: {err}")
    else:
      self.log.warn("No connection is made")

  def do_connect(self, args):
    """ New implementation for connection for hosts """
    if len(self.hosts) == 0:
      self.log.warn("No host(s) is not added.")
      return
    removehost = []
    self.log.print("Connecting to hosts.")
    for host in self.hosts:
      try:
        transport = paramiko.Transport((host, self.port))
        transport.connect(username=self.uid, password=self.password)
        self.connections.append(transport)
        self.log.print(f"Connected host: {host}")
      except socket.error as e:
        self.log.warn(f"Failed on {host}: socket connection failed - {e}")
        removehost.append(host)
      except paramiko.SSHException as e:
        self.log.warn(f"Failed on {host}: password is invalid - {e}")
        removehost.append(host)
      except paramiko.AuthenticationException as e:
        self.log.warn(f"Authentication failed for some reason on {host} - {e}")
        removehost.append(host)
        # calculating the connected hosts
      total_host = len(self.hosts)
      total_connected_host = len(self.hosts) - len(removehost)
      # remove the failed hosts
      for remove_item in removehost:
        self.do_rmhost(remove_item)
        self.log.warn(f"Fail connection: {remove_item}")
    self.log.print(f"* Total connected hosts: {total_connected_host} out of {total_host}")
    if total_connected_host >= 1:
      self.prompt = 'ssh mode: connected > '

  def do_run(self, args):
    """ run/execute command on all the host in the list """
    command = args.strip()
    if command and self.connections:
      self.log.print(f"Input: {command}")
      for host, conn in zip(self.hosts, self.connections):
        self.log.print(f"host: {host}")
        channel = conn.open_session()
        channel.exec_command(command)
        stdout = channel.makefile('rb', -1)
        stderr = channel.makefile_stderr('rb', -1)
        for byteline in stdout.read().splitlines():
          line = byteline.decode("utf-8")
          self.log.print(f"\t{line}")
        for byteline in stderr.read().splitlines():
          line = byteline.decode("utf-8")
          self.log.warn(f"[Error]: \t{line}")
    else:
      self.log.warn("No connection is made")

  def do_sudorun(self, args):
    command = args.strip()
    self.do_run(f"sudo {command}")

  def do_close(self, args):
    for conn in self.connections:
      conn.close()
    self.connections = []
    self.prompt = 'ssh > '

  def do_EOF(self, args):
    self.do_quit(self)

  def do_quit(self, args):
    self.do_close(self)
    self.hosts = []
    sys.exit(0)

  def do_exit(self, args):
    self.do_quit(self)


if __name__ == '__main__':
  try:
    RunCommand().cmdloop()
  except KeyboardInterrupt as e:
    print(f"Caught CRTL-C, script is terminated. {e}")
