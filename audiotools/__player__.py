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
import time

def init_player(controller_obj, player_class):
    (c2p_r_fd, c2p_w_fd) = os.pipe()
    (p2c_r_fd, p2c_w_fd) = os.pipe()
    pid = os.fork()
    if (pid > 0):  #controller
        os.close(c2p_r_fd)
        os.close(p2c_w_fd)
        controller_obj.player_r_fd = p2c_r_fd
        controller_obj.player_w_fd = c2p_w_fd
        controller_obj.player_pid = pid
        controller_obj.player_input = os.fdopen(p2c_r_fd, "rb")
    else:          #player
        os.close(c2p_w_fd)
        os.close(p2c_r_fd)
        player_class(c2p_r_fd, p2c_w_fd).run()

class Controller:
    def __init__(self):
        self.player_r_fd = -1
        self.player_w_fd = -1
        self.player_pid = -1
        self.player_input = None

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

    def cmd_echo_reply(self, *args):
        print "Echo Reply %s" % (repr(args))

    def cmd_open(self, track_path):
        self.to_player("open", track_path)

    def cmd_play(self):
        self.to_player("play")

    def cmd_pause(self):
        self.to_player("pause")

    def cmd_toggle_pause(self):
        self.to_player("toggle_pause")

    def cmd_stop(self):
        self.to_player("stop")

    def cmd_play_error(self, exception):
        print "*** Playing Exception: %s" % (exception)

    def cmd_track_finished(self):
        pass

    def cmd_status(self):
        self.to_player("status")

    def cmd_status_response(self, path, metadata ,channels, channel_mask,
                            bits_per_sample, sample_rate, total_frames,
                            frames_sent, player_state):
        pass

(PLAYER_STOPPED, PLAYER_PAUSED, PLAYER_PLAYING) = range(3)

class Player:
    def __init__(self, controller_r_fd, controller_w_fd):
        self.controller_r_fd = controller_r_fd
        self.controller_w_fd = controller_w_fd
        self.controller_input = os.fdopen(controller_r_fd, "rb")
        self.track = None
        self.status_cache = None
        self.pcm = None
        self.frames_sent = 0
        self.total_frames = 0
        self.state = PLAYER_STOPPED

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

    def echo(self, *args):
        self.to_controller("cmd_echo_reply", *args)

    def quit(self):
        sys.exit(0)

    def open(self, track_path):
        """opens the track at track_path and sets state to PLAYER_STOPPED"""

        self.state = PLAYER_STOPPED
        try:
            self.track = audiotools.open(track_path)
            self.status_cache = None
            self.pcm = None
            self.total_frames = self.track.total_frames()
            self.frames_sent = 0
        except Exception, err:
            self.to_controller("cmd_play_error", err)

    def play(self):
        """plays current open track and sets state to PLAYER_PLAYING

        if no track is set, state set to PLAYER_STOPPED"""

        if (self.track is not None):
            if (self.state == PLAYER_STOPPED):
                self.pcm = self.track.to_pcm()
                self.state = PLAYER_PLAYING
            elif (self.state == PLAYER_PAUSED):
                self.state = PLAYER_PLAYING
            elif (self.state == PLAYER_PLAYING):
                pass
        else:
            self.state = PLAYER_STOPPED

    def pause(self):
        """pauses playing and sets state to PLAYER_PAUSED"""

        self.state = PLAYER_PAUSED

    def toggle_pause(self):
        """if PLAYER_PLAYING, pause().
        if PLAYED_PAUSED or PLAYER_STOPPED, play()"""

        if (self.state == PLAYER_PLAYING):
            self.pause()
        elif ((self.state == PLAYER_PAUSED) or
              (self.state == PLAYER_STOPPED)):
            self.play()

    def stop(self):
        """stops playing and sets state to PLAYER_STOPPED"""

        if (self.pcm is not None):
            self.pcm.close()

        self.status_cache = None
        self.pcm = None
        self.total_frames = 0
        self.frames_sent = 0
        self.state = PLAYER_STOPPED

    def track_finished(self):
        """called by run() when a track is finished playing"""

        self.to_controller("cmd_track_finished")

    def status(self):
        if (self.status_cache is None):
            if (self.track is not None):
                self.status_cache = [self.track.filename,
                                     self.track.get_metadata(),
                                     self.track.channels(),
                                     self.track.channel_mask(),
                                     self.track.bits_per_sample(),
                                     self.track.sample_rate(),
                                     self.track.total_frames()]
                self.to_controller("cmd_status_response",
                                   *(self.status_cache + [self.frames_sent,
                                                          self.state]))
            else:
                self.status_cache = [None, None, 0, 0, 0, 0, 0]
                self.to_controller("cmd_status_response",
                                   *(self.status_cache + [self.frames_sent,
                                                          self.state]))
        else:
            self.to_controller("cmd_status_response",
                               *(self.status_cache + [self.frames_sent,
                                                      self.state]))

class NullPlayer(Player):
    def play(self):
        """plays current open track and sets state to PLAYER_PLAYING

        if no track is set, state set to PLAYER_STOPPED"""

        if (self.track is not None):
            if (self.state == PLAYER_STOPPED):
                self.pcm = audiotools.BufferedPCMReader(self.track.to_pcm())
                self.state = PLAYER_PLAYING
            elif (self.state == PLAYER_PAUSED):
                self.state = PLAYER_PLAYING
            elif (self.state == PLAYER_PLAYING):
                pass
        else:
            self.state = PLAYER_STOPPED

    def run(self):
        """Starts the player's event loop.

        This is called automatically by the init_player function."""

        while (True):
            if (self.state == PLAYER_PLAYING):
                (rlist, wlist, xlist) = select.select([self.controller_r_fd],
                                                      [], [], 0)
                if (len(rlist) > 0):
                    (command, args) = self.from_controller()
                    getattr(self, command)(*args)
                else:
                    if (self.frames_sent < self.total_frames):
                        frame = self.pcm.read(self.pcm.sample_rate / 2)
                        self.frames_sent += frame.frames
                        if (self.frames_sent < self.total_frames):
                            time.sleep(float(frame.frames) /
                                       self.pcm.sample_rate)
                        else:
                            self.stop()
                            self.track_finished()
                    else:
                        self.stop()
            else:
                (rlist, wlist, xlist) = select.select([self.controller_r_fd],
                                                      [], [])
                if (len(rlist) > 0):
                    (command, args) = self.from_controller()
                    getattr(self, command)(*args)
