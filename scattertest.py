
'''
The following is a test of the scatter plot animation performance from a StackOverflow question.

The above answer runs at about 8FPS on my Linux desktop.

Modifying to create the scatter plot once and using set_offsets() to update the X/Y data gets it to about 15FPS.

Changing to blitting gets us to about 24FPS. 

Changing to blitting with the axes only being redrawn periodically when the limits change is marginally faster, about 179FPS.

In other testing I see that drawing the axes with the ticks and labels can consume up to 80 percent of draw time.

If the limits are not changing, then the axes do not need to be redrawn, only the actual data, which is by 
comparison very short.

'''
import sys
import matplotlib.pyplot as plt
import numpy as np
import time
import random

# See: git@github.com:stuartlynne/drawanimated.git
from drawanim import DrawAnimated, DrawTimes

if __name__ == '__main__':

    plt.ioff()
    fig, ax = plt.subplots()
    sample_x = range(1000,12000,100)
    sample_y = random.sample(range(110),110)

    # setup draw_animated, and set all of the artists to animated, including the axes, spines, and title.
    drawanimated = DrawAnimated(fig, )
    drawanimated.open(xaxis_dynamic=False, yaxis_dynamic=False, extra_static_artists=[], debug=False, )
    drawanimated.animate_chrome(ax, name='scatter', title='Scatter Plot', )

    # create scatter plot, set animated=True 
    sc = ax.scatter([],[], color='black', animated=True)

    for force in [False, True]:
        # draw the initial plot, effectively just a blank plot
        if force:
            ax.set_title('Scatter Plot')
        else:
            ax.set_title('Scatter Plot - force static redraws')
        fig.show()
        #plt.pause(0.001)

        # iterate across the data incrementally updating the plot
        last_xlims = last_ylims = None
        fps = []
        lims_changed = 0
        for idx in range(1, len(sample_x)):
            t1 = time.perf_counter()

            # get x and y we want to plot, update scatter plot using set_offsets
            x = sample_x[:idx]
            y = sample_y[:idx]
            sc.set_offsets(np.c_[x,y])

            # get the new limits of the plot and update if necessary,
            # if changed set fig._draw_reset = True to force the axes to be redrawn
            # To see the effect of not redrawing the axes, set the following to False
            if True:
                xlims = (min(x),max(x))
                ylims = (min(y),max(y))
            else:
                xlims = (min(sample_x), max(sample_x))
                ylims = (min(sample_y), max(sample_y))
            if ylims[0] == ylims[1]:
                ylims = (ylims[0]-1, ylims[1]+1)

            # if the limits have changed, update the plot
            if last_xlims is None or last_xlims[1] <= xlims[1]:

                # the way this test is written the xlims are always increasing, which is not realistic
                # and the axes are always redrawn, limiting us to about 24FPS on Linux test system.
                # bumping the number so that we only redraw periodically gets us to about 170FPS on the same system.
                #
                xlims = (xlims[0], xlims[1]+1000)
                ax.set_xlim(xlims)
                fig._draw_reset = True
                drawanimated.reset('xlims')
                last_xlims = xlims
                lims_changed += 1

            if last_ylims is None or last_ylims != ylims:
                ax.set_ylim(ylims)
                drawanimated.reset('ylims')
                last_ylims = ylims
                lims_changed += 1

            if force:
                drawanimated.reset('force')
            # incrementally draw the plot
            drawanimated.draw_loop(pause_time=0.01, sleep_time=0.001)

            fps.append(1/(time.perf_counter()-t1))
            #print('Mean Frame Rate: %.3gFPS' % (1/(time.perf_counter()-t1)), file=sys.stderr)

        print('Mean FPS: %.3gFPS' % np.mean(fps), file=sys.stderr)
        print('lims_changed: %d' % lims_changed, file=sys.stderr)
        drawanimated.close()
        drawanimated.print_summary()

