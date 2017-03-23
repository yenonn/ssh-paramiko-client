#!bin/python
#
#!!!!!!!!!!!BE CAREFUL WHEN YOU ARE USING THIS!!!!!!!!!!!!!!!!!
# ssh implementation to allow multiple ssh connections at one time. It allows you
# to prompt commands at one time recursively to all of the connected ssh clients. 
# So, it means that you have to be *very* aware of the commands that you put in.
# otherwise, it will be a disasterous impact.
#!!!!!!!!!!!BE CAREFUL WHEN YOU ARE USING THIS!!!!!!!!!!!!!!!!!
# WARNING!
#
# Last modification:
# Wed 22 Mar 2017 - add get pty to support sudo
# Thu 23 Mar 2017 - su doest not run properly.. adding quote
#
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
    intro = "-- Welcome to pyssh v2, be careful of your commands --"
#-----------------------------------------------------------------------------------#
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
            self.uid = raw_input("login as: ").strip()
            self.password = ""
            while not self.password:
                self.password = getpass.getpass()
            # Setting logging file
            timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d-%H:%M:%S')
            self.logname = os.getcwd() + "/pysshv2-" + timestamp + ".log"
            self.logfile = open(self.logname, 'a')
            self.logfile.write("Time: %s\n" % timestamp)
            self.logfile.close()
        #-----------------------------------------------------------------------------------#
    def do_help(self, args):
        print "Usage - pyssh.py"
        print "======================================================================"
        print " addhost      - add host with the comma delimitter"
        print " addhostfile  - add host with a absolute path of a file"
        print " rmhost       - remove host with the comma delimitter"
        print " lshost       - list hosts"
        print "----------------------------------------------------------------------"
        print " ping         - do a ping test to the added host list"
        print "----------------------------------------------------------------------"
        print " connect      - establish ssh connection to the added host list"
        print " run          - run a specific command on the connected host"
        print " runsudo      - run a specific command in sudo mode"
        print " put          - put a file onto the connected host"
        print "----------------------------------------------------------------------"
        print " close        - close the ssh connect to the added host list"
        print " quit         - quit the session"
        print " exit         - exit the session"
        print "======================================================================"
        #-----------------------------------------------------------------------------------#
    def emptyline(self):
        pass
        #-----------------------------------------------------------------------------------#
    def do_addhost(self, args):
        """ Add the host to the host list """
        add_item_hosts = args.split(",")
        for h in add_item_hosts:
            add_item = h.strip()
            if add_item and add_item not in self.hosts:
                self.hosts.append(add_item)
            else:
                print "host is skipped: %s" % add_item
        print "host added: %s" % self.hosts
        #-----------------------------------------------------------------------------------#
    def do_rmhost(self, args):
        """ Remove the host to the host list """
        remove_host = args.strip()
        if remove_host and remove_host in self.hosts:
            self.hosts.remove(remove_host)
            print "host is removed: %s " % remove_host
        else:
            print "host is not found."
        #-----------------------------------------------------------------------------------#
    def do_lshost(self, args):
        """ List out the host in the host list """
        if len(self.hosts) == 0:
            print "No hosts(s) is added"
        else:
            for item_host in self.hosts:
                print "host: %s" % item_host
            print "Total added hosts: %s" % len(self.hosts)
        #-----------------------------------------------------------------------------------#
    def do_addhostfile(self, args):
        """ Add a file that connect the host list """
        hostfile = args.strip()
        if os.path.isfile(hostfile):
            try:
                file = open(hostfile, "r")
                for line in file.readlines():
                    if line.strip() not in self.hosts and len(line.strip()) > 0:
                        self.hosts.append(line.strip())
                file.close()
            except IOError, e:
                print "Unable to open file", e
        else:
            print "file is not found, %s" % hostfile
        #-----------------------------------------------------------------------------------#
    def do_ping(self, args):
        """ Ping the hosts in the host list """
        if len(self.hosts) == 0:
            print "No host(s) is added"
        else:
            removehost = []
            for ping_item in self.hosts:
                ping_command = ["ping", "-c", "2", ping_item]
                p = subprocess.Popen(ping_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                result = p.communicate()

            replyok = "0% packet loss"
            match = re.compile(replyok)

        if match.search(result[0]):
            print "host: %s - PING OK" % (ping_item)
        else:
            print "host: %s - PING FAILED" % (ping_item)
            removehost.append(ping_item)

	    # calculate pingable hosts
        total_pingable_host = len(self.hosts) - len(removehost)

	    # removing all the unpingable hosts
        for remove_item in removehost:
            self.do_rmhost(remove_item)
            print "Total pingable hosts: %s" % (total_pingable_host)
        #-----------------------------------------------------------------------------------#

    def do_put(self, args):
        """ Put a file onto the targeted host"""
        local_path = args.strip()
        if not os.access(local_path, os.R_OK):
            print "Read permission is denied on file, %s" % local_path
            return

        if not os.path.isfile(local_path):
            print "File is not found: %s" % (local_path)
            return

        remote_path = None
        if not remote_path:
            remote_path = os.path.split(local_path)[1]

        if self.connections:
            self.logfile = open(self.logname, "a")
            for host, conn in zip(self.hosts, self.connections):
                try:
                    print "host: %s" % host
                    self.logfile.write("host: %s\n" % host)
                    sftp = paramiko.SFTPClient.from_transport(conn)
                    sftp.put(local_path, remote_path)
                    print "File is copied to %s@%s:~/%s" % (self.uid, host, remote_path)
                    self.logfile.write("File is copied to %s@%s:~/%s" % (self.uid, host, remote_path))
                except Exception, err:
                    print "Error: %s" % (err)
                    self.logfile.close()
        else:
            print "No connection is made"
        #-----------------------------------------------------------------------------------#
    def do_connect(self, args):
        """ New implementation for connection for hosts """
        if len(self.hosts) == 0:
            print "No host(s) is not added."
            return
        removehost = []
        self.logfile = open(self.logname, "a")
        self.logfile.write("Connecting to hosts.\n")
	for host in self.hosts:
            try:
                transport = paramiko.Transport((host, self.port))
                transport.connect(username=self.uid, password=self.password)
                self.connections.append(transport)
                print "Connected host: %s" % host
                self.logfile.write("Connected host: %s\n" % host)
            except socket.error, e:
                print "Failed on %s: socket connection failed" % host, e
                removehost.append(host)
            except paramiko.SSHException, e:
                print "Failed on %s: password is invalid" % host, e
                removehost.append(host)
            except paramiko.AuthenticationException, e:
                print "Authentication failed for some reason on %s :" % host, e
                removehost.append(host)

        #calculating the connected hosts
        total_host = len(self.hosts)
        total_connected_host = len(self.hosts) - len(removehost)

        #remove the failed hosts
        for remove_item in removehost:
            self.do_rmhost(remove_item)
            self.logfile.write("Fail connection: %s\n" % remove_item)

            print "Total connected hosts: %s out of %s" % (total_connected_host, total_host)
        self.logfile.write("Total connected hosts: %s out of %s\n" % (total_connected_host, total_host))
        self.logfile.close()
        if total_connected_host >= 1:
            self.prompt = 'ssh mode:connected > '
        #-----------------------------------------------------------------------------------#
    def do_runsudo(self, args):
	""" enable/disable sudo """
	sudo_cmd = args.strip()
	self.do_run(sudo_cmd,True)
        #-----------------------------------------------------------------------------------#
	# There are 2 ways of doing the sudo you can modify to suit your best 		    #
	# Read sudo for infomation about using -S -p 					    #
        #-----------------------------------------------------------------------------------#
    def do_run(self, args,sudoenabled=False):
        """ run/execute command on all the host in the list """
        command = args.strip()
	if sudoenabled:
           #fullcmd = "echo " + self.password + " | sudo -k -S -p '' su -c \'" + command + "\'"
           fullcmd = "sudo -k su -c " + "\'" + command + "\'"
	else:
           fullcmd = command
        if fullcmd and self.connections:
            self.logfile = open(self.logname, "a")
            self.logfile.write("Input: %s\n" % command)
            for host, conn in zip(self.hosts, self.connections):
                print "host: %s" % host
                self.logfile.write("host: %s\n" % host)
		channel = conn.open_session()
		if sudoenabled:
		   channel.get_pty()

		channel.exec_command(fullcmd)
		if sudoenabled:
		   stdin = channel.makefile('wb', -1)

                stdout = channel.makefile('rb', -1)
                stderr = channel.makefile_stderr('rb', -1)
		if sudoenabled:
		   stdin.write(self.password +'\n')
		   stdin.flush()
                   for line in stdout.read().splitlines()[1:]:
                       print "\t%s" % (line)
                       self.logfile.write("\t" + line + "\n")
		else:
		    for line in stdout.read().splitlines():
                        print "\t%s" % (line)
                        self.logfile.write("\t" + line + "\n")

		#for line in stdout.read().splitlines():
                    #print "\t%s" % (line)
                    #self.logfile.write("\t" + line + "\n")

                for line in stderr.read().splitlines():
                    print "[Error]: \t%s" % (line)
                    self.logfile.write("[Error]:\t" + line + "\n")
            self.logfile.close()
        else:
            print "No connection is made"
        #-----------------------------------------------------------------------------------#
    def do_close(self, args):
        for conn in self.connections:
            conn.close()
            self.connections = []
            self.prompt = 'ssh > '
	#-----------------------------------------------------------------------------------#
    def do_EOF(self, args):
        self.do_quit(self)
        #-----------------------------------------------------------------------------------#
    def do_quit(self, args):
        self.do_close(self)
        self.hosts = []
        sys.exit(0)
        #-----------------------------------------------------------------------------------#
    def do_exit(self, args):
        self.do_quit(self)
        #-----------------------------------------------------------------------------------#
if __name__ == '__main__':
    try:
        RunCommand().cmdloop()
    except KeyboardInterrupt, e:
        print "Caught CRTL-C, script is terminated.", e
