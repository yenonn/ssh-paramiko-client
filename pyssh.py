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

class RunCommand(cmd.Cmd):
  """ Simple shell to run command on the host """
  prompt = "ssh > "
  intro = "-- Welcome to ssh paramiko, be careful of your commands --"
  def __init__(self):
    cmd.Cmd.__init__(self)
    self.hosts = []
    self.connections = []
    self.port = 22
    # Setting up the credential
    #self.uid = getpass.getuser()
	  #print "Connecting via [%s]" % self.uid
    self.uid = ""
    while not self.uid:
      self.uid = input("login as: ").strip()
    else:
      self.password = ""
      while not self.password:
        self.password = getpass.getpass()
    # Setting logging file
    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d-%H:%M:%S')
    self.logname = os.getcwd() + "/ssh-paramiko-" + timestamp + ".log"
    self.logfile = open(self.logname, 'a')
    self.logfile.write("Time: %s\n" % timestamp)
    self.logfile.close()
  
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
        print("host is skipped: {}".format(add_item))
    print("host is added: {}".format(" ".join(str(h) for h in self.hosts)))
   
  def do_rmhost(self, args):
    """ Remove the host to the host list """
    remove_host = args.strip()
    if remove_host and remove_host in self.hosts:
      self.hosts.remove(remove_host)
      print("host is removed: {} ".format(remove_host))
    else:
      print("host is not found.")
    
  def do_lshost(self, args):
    """ List out the host in the host list """
    if len(self.hosts) == 0:
      print("No hosts(s) is added")
    else:
      for item_host in self.hosts:
        print("host: {}".format(item_host))
      print("* Total added hosts: {}".format(self.hosts))

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
        print("Unable to open file {}".format(io_error))
    else:
      print("file is not found, {}".format(hostfile))

  def do_ping(self, args):
    """ Ping the hosts in the host list """
    if len(self.hosts) == 0:
      print("No host(s) is added")
      return
    else:
      removehost = []
      for ping_item in self.hosts:
        ping_command = "ping -c 2 {}".format(ping_item)
        result = subprocess.getoutput(ping_command)
        if "2 packets received" in result:
          print("host: {} - PING OK".format(ping_item))
        else:
          print("host: {} - PING FAILED".format(ping_item))
          removehost.append(ping_item)
      # calculate pingable hosts
      total_pingable_host = len(self.hosts) - len(removehost)
      # removing all the unpingable hosts
      for remove_item in removehost:
        self.do_rmhost(remove_item)
    print("* Total pingable hosts: {}".format(total_pingable_host))

    def do_put(self, args):
      """ Put a file onto the targeted host"""
      local_path = args.strip()
      if not os.access(local_path, os.R_OK):
        print("Read permission is denied on file, {}".format(local_path))
        return
      if not os.path.isfile(local_path):
        print("File is not found: {}".format(local_path))
        return

      remote_path = None
      if not remote_path:
        remote_path = os.path.split(local_path)[1]
        
      if self.connections:
        self.logfile = open(self.logname, "a")
        for host, conn in zip(self.hosts, self.connections):
          try:
            print("host: {}").format(host)
            self.logfile.write("host: {}\n".format(host))
            sftp = paramiko.SFTPClient.from_transport(conn)
            sftp.put(local_path, remote_path)
            print("File is copied to {}@{}:~/{}".format(self.uid, host, remote_path))
            self.logfile.write("File is copied to {}@{}:~/{}".format(self.uid, host, remote_path))
          except Exception as err:
            print("Error: {}".format(err))
            self.logfile.close()
          else:
            print("No connection is made")

    def do_get (self, args):
      """ Get a file from the targeted host"""
      remote_path = args.strip()
      remote_file_name = remote_path.split("/")[-1]
      local_path = "/tmp/"
      if self.connections:
        self.logfile = open(self.logname, "a")
        for host, conn in zip(self.hosts, self.connections):
          try:
            print("host: {}").format(host)
            sftp = paramiko.SFTPClient.from_transport(conn)
            local_file = local_path + remote_file_name + "." + host + ".out"
            sftp.get(remote_path, local_file)
            print("file: {} is copied to local FS: {}".format(remote_path, local_file))
            os.chmod(local_file, 644)
          except Exception as err:
            print("Error: {}".format(err))
            self.logfile.close()
          else:
            print("No connection is made")

    def do_connect(self, args):
      """ New implementation for connection for hosts """
      if len(self.hosts) == 0:
        print("No host(s) is not added.")
        return
      removehost = []
      self.logfile = open(self.logname, "a")
      self.logfile.write("Connecting to hosts.\n")
      for host in self.hosts:
        try:
          transport = paramiko.Transport((host, self.port))
          transport.connect(username = self.uid, password = self.password)
          self.connections.append(transport)
          print("Connected host: {}".format(host))
          self.logfile.write("Connected host: {}\n".format(host))
        except socket.error as e:
          print("Failed on {}: socket connection failed - {}".format(host, e))
          removehost.append(host)
        except paramiko.SSHException as e:
          print("Failed on {}: password is invalid".format(host, e))
          removehost.append(host)
        except paramiko.AuthenticationException as e:
          print("Authentication failed for some reason on {} :".format(host, e))
          removehost.append(host)
          #calculating the connected hosts
          total_host = len(self.hosts)
          total_connected_host = len(self.hosts) - len(removehost)
          #remove the failed hosts
      for remove_item in removehost:
        self.do_rmhost(remove_item)
        self.logfile.write("Fail connection: {}\n".format(remove_item))
      print("* Total connected hosts: {} out of {}".format(total_connected_host, total_host))
      self.logfile.write("Total connected hosts: {} out of {}\n".format(total_connected_host, total_host))
      self.logfile.close()
      if total_connected_host >= 1:
        self.prompt = 'ssh mode:connected > '
        
  # def do_connect(self, args):
  #   """ Connect to all hosts in the host list """
  #   for host in self.hosts:
  #     try:
  #       client = paramiko.SSHClient()
  #       client.set_missing_host_key_policy( paramiko.AutoAddPolicy())
  #       client.connect( host, username=self.uid , password=self.password)
  #       self.connections.append(client)
  #       print "Connected host: %s" % host
  #     except socket.error, e:
  #       print "Failed on %s: socket connection failed" % host, e
  #       self.do_rmhost(host)
  #     except paramiko.SSHException, e:
  #       print "Failed on %s: password is invalid" % host, e
  #       self.do_rmhost(host)
  #     except paramiko.AuthenticationException, e:
  #         print "Authentication failed for some reason on %s:" % host, e
  #         self.do_rmhost(host)
  #   print "Total connected hosts: %s out of %s" % ( len(self.connections), len(self.hosts) )

  def do_run(self, args):
    """ run/execute command on all the host in the list """
    command = args.strip()
    if command and self.connections:
      self.logfile = open(self.logname, "a")
      self.logfile.write("Input: {}\n".format(command))
      for host, conn in zip(self.hosts, self.connections):
        print("host: {}".format(host))
        self.logfile.write("host: {}\n".format(host))
        channel = conn.open_session()
        channel.exec_command(command)
        stdout = channel.makefile('rb', -1)
        stderr = channel.makefile_stderr('rb', -1)
        for line in stdout.read().splitlines():
          print("\t{}".format(line))
          self.logfile.write("\t" + line + "\n")
        for line in stderr.read().splitlines():
          print("[Error]: \t{}".format(line))
          self.logfile.write("[Error]:\t" + line + "\n")
        self.logfile.close()
    else:
      print("No connection is made")

  # def do_run(self, command):
  #   """ run/execute command on all the host in the list """
  #   if command:
  #     self.logfile = open(self.logname, "a")
  #     self.logfile.write("Input: %s\n" % command)
  #     for host, conn in zip(self.hosts, self.connections):
  #       print "host: %s" % host
  #       self.logfile.write("host: %s\n" % host)
  #       stdin, stdout, stderr = conn.exec_command(command)
  #       stdin.close()
  #     for line in stdout.read().splitlines():
  #       print "\t%s" % (line)
  #       self.logfile.write("\t" + line + "\n")
  #     for line in stderr.read().splitlines():
  #       print "[Error]: %s" % (line)
  #       self.logfile.write("[Error]:\t" + line + "\n")
  #     self.logfile.close()
  #   else:
  #     print "usage: run"

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
    print("Caught CRTL-C, script is terminated. {}".format(e))
