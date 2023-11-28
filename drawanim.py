
# Draw Animated with Incremental Blitting
# Copyright (c) 2023 stuart.lynne@gmail.com
# Made available under the MIT license.
# See LICENSE file for details.

import sys
import matplotlib.pyplot as plt
import numpy as np
from time import time, sleep, perf_counter
from matplotlib.axis import XAxis, YAxis
from matplotlib.legend import Legend
from matplotlib.spines import Spine

# Draw Animated with Incremental Blitting
# This class is used to draw animated artists on a matplotlib axes using blitting
# using two incremental approaches to reduce drawing time and latency.
#

# context manager to track draw times for artists
class DrawTimer:
    def __init__(self, id ):
        self.t0 = None
        self.avg = 0
        self.total = 0
        self.count = 0
        self.id = id

    def get_avg(self):
        return self.avg, self.count, self.id

    def __enter__(self):
        self.t0 = perf_counter()
        return self

    def __exit__(self, type, value, traceback):
        draw_time = perf_counter() - self.t0
        self.total += draw_time
        self.count += 1
        self.avg = self.total / self.count


# Draw Animated with Blitting
# This class is used to draw animated artists on a matplotlib axes using blitting.
# It is designed to be used in a loop, where each iteration of the loop will draw
# one or more artists.  The loop should continue until draw_animated() returns False.
#
# The intent is to allow the GUI event loop to run between each call to draw_animated()
# to reduce latency and improve responsiveness of the GUI.
#
def draw_animated(fig, flush_events=False, close=False, open=False, dprint=None):

    # catch resize event, clear saved backgrounds, it is expected that matplotlib
    # will draw the entire figure after a resize event and we need to save the 
    # initial base background later
    def _on_resize(event):
        fig._bg_base = fig._bg_static = None

    def draw_artist(draw_list, msg):
        while len(draw_list) > 0:
            a = draw_list.pop(0)
            if a not in current_animated_artists:
                continue
            # create a DrawTimer if needed
            if a not in fig._draw_times:
                fig._draw_times[a] = DrawTimer(id(a))
            
            # draw the artist and update the DrawTimer with elapsed time
            with fig._draw_times[a]:
                fig.draw_artist(a)
            return f"{a.get_label()} draw_artist", fig._draw_times[a].get_avg()
        return None, None

    if open:
        try:
            if fig._mpl_connect is not None:
                fig.figure.canvas.mpl_disconnect(fig._mpl_connect)
                fig._mpl_connect = None
        except:
            pass
        fig._bg_base = fig._bg_static = None
        fig._draw_times = {}
        fig._mpl_connect = fig.canvas.mpl_connect('resize_event', _on_resize)
        fig._draw_list = None
        fig._blitted = False
        fig._draw_reset = False
        return None, None

    if fig._draw_reset:
        fig._bg_static = None
        fig._draw_reset = False

    # get the list of animated artists that are currently visible, this needs to be done
    # each time because the list of artists can change dynamically
    static_dict = {}
    dynamic_dict = {}
    for axes in fig.get_children():
        if type(axes) is plt.Axes:
            for a in axes.get_children():
                if a.get_animated() and a.get_visible():
                    if type(a) is XAxis or type(a) is YAxis or type(a) is Legend or type(a) is Spine:
                        static_dict[id(a)] = a
                    elif a in [axes.title, axes._left_title, axes._right_title,]:
                        static_dict[id(a)] = a
                    else:
                        dynamic_dict[id(a)] = a

    static_animated_artists = [a for a in static_dict.values()] if fig._bg_static is None else []
    dynamic_animated_artists = [a for a in dynamic_dict.values()]

    current_animated_artists = static_animated_artists + dynamic_animated_artists

    if close:
        if fig._mpl_connect is not None:
            fig.figure.canvas.mpl_disconnect(fig._mpl_connect)
            fig._mpl_connect = None
        return None, None

    # save the base background if we don't have it, return True
    try:
        if fig._bg_base:
            pass
    except AttributeError:
        fig._bg_base = fig._bg_static = None
        fig._mpl_connect = fig.canvas.mpl_connect('resize_event', _on_resize)
        fig._draw_list = None
        fig._blitted = False
        #print(f"current_animated_artists: {current_animated_artists}", file=sys.stderr)
        #sleep(2)
        return None, None

    if fig._bg_base is None:
        fig._bg_base = fig.figure.canvas.copy_from_bbox(fig.figure.bbox)
        fig._draw_list = None
        fig._blitted = True
        #sleep(6)
        return 'copy_from_bbox', None


    # if draw_list is None, restore the background, create artist draw list, return True
    if fig._draw_list is None:
        fig.canvas.restore_region(fig._bg_base if fig._bg_static is None else fig._bg_static)
        if False:
            fig._draw_list = static_animated_artists + dynamic_animated_artists   
            fig._static = False
        else:
            fig._draw_list = static_animated_artists
            fig._static = True
        fig._blitted = False
        # XXX
        #fig.canvas.flush_events()
        #sleep(2)
        return 'restore_base' if fig._bg_static is None else 'restore_static', None

    # if work list is not empty, draw next artist, return True
    # N.b. Verify that the artist is still in the axes, it may have been removed, 
    # and/or may not be visible

    if fig._static:
        while len(fig._draw_list) > 0:
            label, time = draw_artist(fig._draw_list, 'static',)
            if label is None:
                break
            return label, time
        # 
        fig._draw_list = dynamic_animated_artists
        fig._static = False
        fig._bg_static = fig.figure.canvas.copy_from_bbox(fig.figure.bbox)


    while len(fig._draw_list) > 0:
        label, time = draw_artist(fig._draw_list, 'dynamic',)
        if label is None:
            break
        return label, time

    # Finally, when work list is empty, blit and return False
    if not fig._blitted:
        fig._blitted = True
        fig.figure.canvas.blit(fig.figure.bbox)
        return 'blit', None

    fig._draw_list = None

    # optionally let the GUI event loop process anything it has to do
    if flush_events:
        fig.canvas.flush_events()
        #sleep(4)
    return None, None


# ########################################################################################################

if __name__ == "__main__":

    # create a mosaic 2 x 2 grid of subplots, 
    fig, axes_dict = plt.subplot_mosaic([['a', 'b'], ['c', 'd']], constrained_layout=True, figsize=(8, 8))

    # setup 4 lines and 2 annotations on each subplot axes, ensure everything is animated
    lines = {n: {} for n in axes_dict.keys()}
    annotations = { a: {'frame_number': None, 'fps': None} for a in axes_dict.keys()}
    legends = {n: None for n in axes_dict.keys()}
    colors = ['red', 'blue', 'green', 'brown']
    for name, ax in axes_dict.items():

        # animate the axes
        title = f"Draw Animated Incremental {name}"
        ax.set_title(title, animated=True, )

        # animated the x and y axis
        xaxis, yaxis = ax._axis_map.values()
        xaxis.set_animated(True)
        yaxis.set_animated(True)

        # animate the spines
        for n, s in ax.spines.items():
            s.set_animated(True)
        # create the 4 line plots
        x = np.linspace(0, 2 * np.pi, 100)
        for c in colors:
            line, = ax.plot(x, np.sin(x), animated=True, label=c, color=c, )
            lines[name][c] = line

        # create the 2 annotations
        for annotation, xytext in [('frame_number', (10, -10)), ('fps', (200, -10))]:
            annotations[name][annotation] = ax.annotate( 
                annotation, (0, 1), xycoords="axes fraction", xytext=xytext, 
                textcoords="offset points", ha="left", va="top", label=annotation, 
                animated=True, )

        # create the legend, note that the ax.legend call does not take the animated parameter, 
        # need to set it explicitly
        leg = ax.legend(handles=lines[name].values(), loc='lower right', )
        leg.set_animated(True)
        leg.set_label('legend')
        legends[name] = leg

    draw_animated(fig, open=True)

    # make sure our window is on the screen and drawn
    plt.show(block=False)
    plt.pause(.001)

    start_time = time()
    frame_count = 0
    divisor = 100
    multiplier = 1
    resets = 0 
    reset = False
    for j in range(400):

        if j % 80 == 0:
            multiplier *= 1.2
        
        for i, (name, ax) in enumerate(axes_dict.items()):
            ymin = []
            ymax = []
            for k, (color, line) in enumerate(lines[name].items()):
                offset = k * 10
                ydata = np.sin(x + offset + (j / divisor) * np.pi / (k+1)) * multiplier 
                ymin.append(min(ydata))
                ymax.append(max(ydata))
                line.set_ydata(ydata)
            annotations[name]['frame_number'].set_text("frame: %d" % (frame_count,))
            annotations[name]['fps'].set_text("fps: %3.1f" % (frame_count / (time() - start_time)))

            if j % 80 == 0:

                min_y = min(ymin)
                max_y = max(ymax)
                ylims = ax.get_ylim()

                if min_y < ylims[0] or max_y > ylims[1]:
                    ax.set_ylim(min_y, max_y)
                    ax.set_ylim(min_y, max_y)
                    ax.set_xlim(0, 2 * np.pi)
                    reset = True

        if reset:
            resets += 1
            reset = False
            for name, ax in axes_dict.items():
                ax.set_title(f"Draw Animated Incremental {name} {resets}")
            fig._draw_reset = True

        # update, this is a loop so GUI can process events
        elapsed = 0
        while True:
            msg, draw_time = draw_animated(fig, flush_events=True)
            if msg is None:
                break
            if draw_time is None:
                continue
            elapsed += draw_time[0]
            if elapsed < 0.01:
                continue
            elapsed = 0
            sleep(.00001)

        frame_count += 1
        fig.canvas.flush_events()
        sleep(.0001)

    draw_animated(fig, close=True)

    # show draw times
    draw_time = [v.total for k, v in fig._draw_times.items()]
    draw_times = [[v.avg, v.total, v.count, v.id, str(k)] for k, v in fig._draw_times.items()]
    total_time = sum(draw_time)
    total_pc = 0    
    for avg, total, count, id, name in sorted(draw_times, reverse=True):
        pc = 100.0*total/total_time
        total_pc += pc
        if count > 1:
            print('draw_animated  %5d | %7.2f %4.1f%% %4.0f%% | %7.2f | %s %s' % (
                count, total*1000, pc, total_pc, avg*1000, id, name), file=sys.stderr) 


