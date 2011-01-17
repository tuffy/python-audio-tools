#!/usr/bin/bin

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2011  Brian Langenberger

#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


import os
import sys
import cPickle
import select
import audiotools

def init_player(controller_obj, player_obj):
    (c2p_r_fd, c2p_w_fd) = os.pipe()
    (p2c_r_fd, p2c_w_fd) = os.pipe()
    pid = os.fork()
    if (pid > 0):  #controller
        os.close(c2p_r_fd)
        os.close(p2c_w_fd)
        return controller_obj(p2c_r_fd, c2p_w_fd, pid)
    else:          #player
        os.close(c2p_w_fd)
        os.close(p2c_r_fd)
        player_obj(c2p_r_fd, p2c_w_fd).run()

class Controller:
    def __init__(self, player_r_fd, player_w_fd, player_pid):
        self.player_r_fd = player_r_fd
        self.player_w_fd = player_w_fd
        self.player_pid = player_pid
        self.player_input = os.fdopen(player_r_fd, "rb")

    def to_player(self, cmd, *args):
        """Sends a (command, arg_list) tuple to the player."""

        os.write(self.player_w_fd,
                 cPickle.dumps((cmd, args), cPickle.HIGHEST_PROTOCOL))

    def from_player(self):
        """Returns a (command, arg_list) tuple from the player."""

        return cPickle.load(self.player_input)

    def run(self):
        """Executes a response command from the player.

        This pulls a pickled value off the r_fd and performs
        the given command."""

        (command, args) = self.from_player()
        getattr(self, command)(*args)

    def wait(self):
        return os.waitpid(self.player_pid, 0)

    def quit(self):
        self.to_player("quit")
        self.wait()

    def echo_reply(self, *args):
        print "Echo Reply %s" % (repr(args))

    def play(self, track_path):
        self.to_player("play", track_path)

    def play_error(self, exception):
        print "*** Playing Exception: %s" % (exception)

    def status(self):
        self.to_player("status")

    def status_response(self, path, channels, channel_mask, bits_per_sample,
                        sample_rate):
        #FIXME - add current/total PCM samples to status
        print "Status: %s %s %s %s %s" % (path, channels, channel_mask,
                                          bits_per_sample, sample_rate)

class Player:
    def __init__(self, controller_r_fd, controller_w_fd):
        self.controller_r_fd = controller_r_fd
        self.controller_w_fd = controller_w_fd
        self.controller_input = os.fdopen(controller_r_fd, "rb")
        self.track = None
        self.pcm = None

    def to_controller(self, cmd, *args):
        """Sends a (command, arg_list) tuple to the controller."""

        os.write(self.controller_w_fd,
                 cPickle.dumps((cmd, args), cPickle.HIGHEST_PROTOCOL))

    def from_controller(self):
        """Returns a (command, arg_list) tuple from the controller."""

        return cPickle.load(self.controller_input)

    def run(self):
        """Starts the player's event loop.

        This is called automatically by the init_player function."""

        #A proper player should be sending data from
        #a PCMReader to an output sink here
        #while polling the controller for input.
        #Once the reader is finished, it should then
        #send a signal to the controller
        #(which might send a command to play the next song).

        while (True):
            (rlist, wlist, xlist) = select.select([self.controller_r_fd],
                                                  [],
                                                  [])
            if (len(rlist) > 0):
                (command, args) = self.from_controller()
                getattr(self, command)(*args)

    def output(self, *args):
        print "Printing %s" % (repr(args))

    def echo(self, *args):
        self.to_controller("echo_reply", *args)

    def quit(self):
        sys.exit(0)

    def play(self, track_path):
        try:
            self.track = audiotools.open(track_path)
            self.pcm = None
        except Exception, err:
            self.to_controller("play_error", err)

    def status(self):
        if (self.track is not None):
            self.to_controller("status_response",
                               self.track.filename,
                               self.track.channels(),
                               self.track.channel_mask(),
                               self.track.bits_per_sample(),
                               self.track.sample_rate())
        else:
            self.to_controller("status_response",
                               None, 0, 0, 0, 0)
